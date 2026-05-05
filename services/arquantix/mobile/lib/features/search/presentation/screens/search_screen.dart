import 'dart:async';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:permission_handler/permission_handler.dart' show openAppSettings;

import '../../../../design_system/design_system.dart';
import '../../../news/presentation/markdown/article_paragraph_markdown.dart';
import '../../data/assistance_conversation_storage.dart';
import '../../application/assistance_deep_link_resolver.dart';
import '../../data/chat_api.dart';
import '../../data/voice_transcriber.dart';
import '../widgets/auto_qcm_footer.dart';
import '../widgets/bundle_detail_card_embed.dart';
import '../widgets/crypto_bundles_card_embed.dart';
import '../widgets/featured_articles_list_embed.dart';
import '../widgets/instrument_detail_card_embed.dart';
import '../widgets/portfolio_allocation_donut_embed.dart';
import '../widgets/top_movers_crypto_embed.dart';
import '../widgets/transaction_detail_embed.dart';
import '../widgets/voice_input_widgets.dart';
import 'assistance_conversations_screen.dart';

/// État du sous-système voice input (D.1.4.8). Mutuellement exclusif
/// avec `_loading` : on ne peut pas enregistrer pendant qu'une réponse
/// IA est en cours de génération, et inversement.
///
/// Transitions valides :
/// - `idle` ─tap micro→ `recording`
/// - `recording` ─tap stop⊠→ `transcribing(action=inject)`
/// - `recording` ─tap ✓→ `transcribing(action=send)`
/// - `transcribing` ─tap stop⊠→ `idle` (transcription annulée)
/// - `transcribing` ─done→ `idle` (texte injecté ou envoyé selon action)
enum _VoiceInputState { idle, recording, transcribing }

/// Action choisie par l'utilisateur en stoppant l'enregistrement,
/// déterminant ce qu'on fera du texte transcrit.
enum _VoiceTranscribeAction {
  /// Stop ⊠ pendant recording → la transcription terminée injecte le
  /// texte dans le TextField (l'utilisateur peut éditer puis envoyer
  /// manuellement). Reproduit le comportement « dictée » ChatGPT.
  inject,

  /// ✓ pendant recording → la transcription terminée envoie
  /// directement le message à l'agent assistance (pas d'édition
  /// intermédiaire). Reproduit le comportement « speech-to-send »
  /// ChatGPT.
  send,
}

/// Message affiché dans la conversation.
class _ChatMessage {
  const _ChatMessage({
    required this.role,
    required this.content,
    required this.createdAt,
    this.agentUsed,
    this.messageType = 'text',
    this.choicesPayload,
    this.selectedChoiceId,
    this.embeds = const [],
    this.autoQcmPayload,
    this.selectedAutoQcmOptionId,
  });
  final String role; // 'user' | 'assistant'
  final String content;

  /// Horodatage local du message. Utilisé pour :
  ///   • afficher l'heure sous la bulle (« 08:15 », « Hier, 08:15 », …),
  ///   • insérer les séparateurs de date (« Aujourd'hui » / « Hier » / DATE)
  ///     entre deux messages tombant sur des jours différents.
  ///
  /// Source :
  ///   • messages historiques (`fetchAssistanceHistory`) → `created_at` serveur.
  ///   • messages créés en local (envoi user, 1er delta assistant SSE) →
  ///     `DateTime.now()` au moment de la création (puis conservé pendant
  ///     toute la durée du streaming pour ne pas se réinitialiser à chaque
  ///     token).
  final DateTime createdAt;

  /// Multi-agents Phase 1 (cf. docs/arquantix/MULTI_AGENTS.md).
  /// Identifiant de l'agent qui a produit le message assistant
  /// (`compliance`, `advisor`, `product`, `market`, `default`, `router`).
  /// `null` pour les messages user. Sert au badge UI au-dessus de la bulle.
  final String? agentUsed;

  /// `'text'` (bulle Markdown classique) ou `'choices'` (QCM cliquable).
  final String messageType;

  /// Payload structuré quand `messageType == 'choices'`. `null` sinon.
  final AssistanceChoicesPayload? choicesPayload;

  /// D.1.4.7 — ID de l'option sélectionnée par l'utilisateur sur un
  /// QCM. `null` tant qu'aucune option n'a été cliquée. Une fois
  /// défini, le QCM passe en mode « consommé » :
  ///   - l'option choisie est mise en avant (contour noir, texte noir
  ///     `AppColors.textPrimary`) ;
  ///   - les autres options passent en gris atténué
  ///     (`AppColors.textMuted`) et ne sont plus cliquables ;
  ///   - aucune option ne déclenche `_handleChoiceTapped`.
  ///
  /// Garde forte contre les double-clic et clarification visuelle de
  /// l'historique de la conversation (cf. capture utilisateur du
  /// 03/05/2026 — confusion possible si un QCM ancien reste cliquable
  /// au scroll). Purement local, jamais persisté côté serveur.
  final String? selectedChoiceId;

  /// Phase 2c.2 — Embeds UI structurés (cartes `transaction_detail`,
  /// etc.) attachés à ce message assistant. Vide pour les messages
  /// user et les messages legacy. Rendus *après* la bulle markdown
  /// dans le même `Column` aligné à gauche.
  final List<AssistanceEmbed> embeds;

  /// Cognitive Bot v4 — Lot 7 V1.1 (2026-05-05). Footer auto-QCM
  /// **annexé** à un message texte. Distinct de [choicesPayload] qui
  /// remplace la bulle. Source : `done.auto_qcm` SSE ou
  /// `message_payload.auto_qcm` au reload `/messages`.
  final AssistanceAutoQcmPayload? autoQcmPayload;

  /// Lot 7 V1.1 — ID de l'option auto-QCM choisie par l'utilisateur.
  /// `null` tant qu'aucune option n'a été cliquée. Une fois défini, le
  /// footer passe en mode **consommé** (anti double-tap, marque
  /// l'option choisie). Purement local (jamais persisté serveur).
  final String? selectedAutoQcmOptionId;

  bool get isChoicesMessage => messageType == 'choices' && choicesPayload != null;

  /// Lot 7 V1.1 — `true` si un footer auto-QCM est attaché. Distinct de
  /// [isChoicesMessage] : ici la bulle texte reste affichée et le
  /// footer est rendu en dessous.
  bool get hasAutoQcm =>
      autoQcmPayload != null && autoQcmPayload!.options.isNotEmpty;

  /// Copie immutable avec sélection d'une option mise à jour. Utilisé
  /// par [_SearchScreenState._handleChoiceTapped] pour figer le QCM
  /// dans l'état « consommé » sans muter l'instance d'origine.
  _ChatMessage copyWithSelectedChoiceId(String selectedId) {
    return _ChatMessage(
      role: role,
      content: content,
      createdAt: createdAt,
      agentUsed: agentUsed,
      messageType: messageType,
      choicesPayload: choicesPayload,
      selectedChoiceId: selectedId,
      embeds: embeds,
      autoQcmPayload: autoQcmPayload,
      selectedAutoQcmOptionId: selectedAutoQcmOptionId,
    );
  }

  /// Copie immutable avec embeds remplacés. Utilisé pour attacher les
  /// `AssistanceTurnEvent.doneEmbeds` au message assistant qui vient
  /// de finir de streamer (sans repasser par un `_load()` complet).
  _ChatMessage copyWithEmbeds(List<AssistanceEmbed> next) {
    return _ChatMessage(
      role: role,
      content: content,
      createdAt: createdAt,
      agentUsed: agentUsed,
      messageType: messageType,
      choicesPayload: choicesPayload,
      selectedChoiceId: selectedChoiceId,
      embeds: next,
      autoQcmPayload: autoQcmPayload,
      selectedAutoQcmOptionId: selectedAutoQcmOptionId,
    );
  }

  /// Lot 7 V1.1 — Copie immutable avec un payload auto-QCM attaché.
  /// Utilisé au moment du `done` SSE pour le rendre live, ou au reload
  /// `/messages` pour reconstituer l'historique.
  _ChatMessage copyWithAutoQcm(AssistanceAutoQcmPayload? payload) {
    return _ChatMessage(
      role: role,
      content: content,
      createdAt: createdAt,
      agentUsed: agentUsed,
      messageType: messageType,
      choicesPayload: choicesPayload,
      selectedChoiceId: selectedChoiceId,
      embeds: embeds,
      autoQcmPayload: payload,
      selectedAutoQcmOptionId: selectedAutoQcmOptionId,
    );
  }

  /// Lot 7 V1.1 — Copie immutable avec une option auto-QCM marquée
  /// comme sélectionnée. Symétrique de [copyWithSelectedChoiceId] pour
  /// les QCM router.
  _ChatMessage copyWithSelectedAutoQcmOptionId(String selectedId) {
    return _ChatMessage(
      role: role,
      content: content,
      createdAt: createdAt,
      agentUsed: agentUsed,
      messageType: messageType,
      choicesPayload: choicesPayload,
      selectedChoiceId: selectedChoiceId,
      embeds: embeds,
      autoQcmPayload: autoQcmPayload,
      selectedAutoQcmOptionId: selectedId,
    );
  }
}

/// Page recherche : interface type ChatGPT avec agent conversationnel (OpenAI, réponses Markdown).
/// [onBack] : si fourni, le bouton back appelle ce callback (ex. retour à l'accueil depuis le shell).
class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key, this.onBack});

  final VoidCallback? onBack;

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final List<_ChatMessage> _messages = [];
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  /// Focus node de l'input texte. Utilisé pour redonner le focus
  /// après tap sur l'option `freeform` d'un QCM (cf.
  /// [_handleChoiceTapped]).
  final FocusNode _inputFocusNode = FocusNode();
  bool _loading = false;
  String? _error;

  /// Key attachée au **dernier message user** (= celui qui vient
  /// d'être envoyé). Permet d'utiliser `Scrollable.ensureVisible` pour
  /// le caler en haut du viewport sous la navbar à chaque envoi. Une
  /// nouvelle key est instanciée à chaque `_sendMessage` pour cibler
  /// la nouvelle bulle (les anciennes bulles user gardent leurs
  /// éventuelles keys orphelines, sans incidence — elles ne sont plus
  /// référencées).
  GlobalKey? _lastUserMessageKey;

  /// ID de la conversation courante côté serveur (MVP D.1.3).
  /// - `null` au premier message → le serveur crée la conversation et nous
  ///   le renvoie ; on le persiste pour la reprise au prochain lancement.
  /// - Réinitialisé à `null` quand l'utilisateur déclenche
  ///   « Nouvelle conversation » (bouton edit dans la nav bar).
  String? _conversationId;

  /// MVP D.1.4.7 — Handle du tour assistant en cours de streaming.
  ///
  /// Conservé côté state pour permettre au bouton stop (carré blanc
  /// quand `_loading == true`) d'appeler [AssistanceTurnHandle.cancel] :
  ///   1. ferme la connexion SSE côté mobile (libère l'UI tout de
  ///      suite) ;
  ///   2. envoie POST `/chat/turn/{conv_id}/cancel` côté serveur pour
  ///      tuer la task background → aucun message commité en BDD pour
  ///      ce tour.
  ///
  /// `null` quand aucun tour n'est en cours. Réinitialisé à la fin du
  /// stream (succès, erreur, annulation) dans [_sendMessage].
  AssistanceTurnHandle? _activeTurnHandle;

  /// MVP D.1.4.7 — Texte du message user qui vient d'être annulé,
  /// conservé pour permettre à l'utilisateur de **relancer** sa demande
  /// via le QCM « Tu as arrêté la recherche, veux-tu la relancer ? »
  /// affiché juste après le stop (cf. [_cancelGeneration] et
  /// [_handleChoiceTapped]).
  ///
  /// `null` quand aucun retry n'est proposé. Réinitialisé :
  ///   - au tap sur l'option « Relancer » du QCM (consommation) ;
  ///   - au tap sur l'option « Rien de tout ça » (freeform, abandon) ;
  ///   - à l'envoi d'un nouveau message manuel ;
  ///   - au reset complet (`_startNewConversation`,
  ///     `_openConversationsHistory`).
  String? _pendingRetryText;

  /// Identifiant d'option spéciale pour « Relancer ma demande » dans
  /// le QCM affiché après un stop volontaire. Distinct de tout
  /// `agent_id` connu pour être routé spécifiquement par
  /// [_handleChoiceTapped] (pas envoyé au router).
  static const String _kRetryAfterCancelOptionId = 'retry_after_cancel';

  // ── Voice input (D.1.4.8) ─────────────────────────────────────────
  //
  // Le moteur (native vs whisper) est sélectionné au lancement de
  // l'app par la variable Dart `ASSISTANCE_VOICE_ENGINE`. La factory
  // [VoiceTranscriberFactory] retourne la bonne implémentation
  // (NativeVoiceTranscriber par défaut, WhisperVoiceTranscriber sinon).
  //
  // Le transcriber est lazy-init : on ne touche pas au moteur natif
  // tant que l'utilisateur n'a pas tap le bouton micro pour la
  // première fois (évite la modale système permission au lancement).
  VoiceTranscriber? _voiceTranscriber;

  /// État du sous-système voice. `idle` la majorité du temps.
  _VoiceInputState _voiceState = _VoiceInputState.idle;

  /// Chargement initial de l'historique (D.1.6) : `true` tant qu'on rejoue
  /// les anciens messages depuis le serveur après une reprise. Bloque
  /// l'affichage du « Bonjour Gael… » empty-state pour ne pas faire clignoter
  /// l'écran si on a effectivement une conversation à charger.
  bool _restoringHistory = false;

  // ── Phase 1 D.1.4.5 — POLLING « catch-up » ──────────────────────────
  // Si l'utilisateur ouvre une conversation depuis l'historique alors que
  // l'assistant est en train d'écrire (commit user déjà fait, message
  // assistant pas encore arrivé côté serveur), on poll `/messages` jusqu'à
  // voir un message assistant. Affiche pendant ce temps le typing indicator
  // standard. Sert aussi de fallback automatique si la phase 2 (SSE) échoue.
  Timer? _pollingTimer;
  int _pollingAttempts = 0;
  static const Duration _pollInterval = Duration(seconds: 5);
  static const int _pollMaxAttempts = 24; // 2 min max — sécurité (24 × 5s).

  /// Opacité du titre nav bar + force du blur arrière-plan en fonction du scroll
  /// (mêmes valeurs que [LayoutPageLevel2] : translation douce, fade-in net).
  double _navTitleOpacity = 0;

  /// Démarrage du fade-in (offset px). Petit buffer pour éviter le clignotement
  /// au moindre micro-scroll.
  static const double _navFadeStart = 16;

  /// Distance sur laquelle l'opacité du titre passe de 0 → 1.
  static const double _navFadeRange = 48;

  @override
  void initState() {
    super.initState();
    _controller.addListener(_onInputChanged);
    _scrollController.addListener(_onScroll);
    _restoreConversationIdFromStorage();
  }

  /// Reprend une conversation existante (D.1.3 + D.1.6) :
  /// 1. Lit l'ID persisté dans `flutter_secure_storage`.
  /// 2. Si présent, fetch l'historique côté serveur et peuple la liste
  ///    `_messages` pour rejouer les anciens tours dans l'UI.
  /// 3. Si le serveur renvoie 404 (conversation supprimée / ID obsolète),
  ///    on nettoie le storage et on repart proprement sur l'empty state.
  Future<void> _restoreConversationIdFromStorage() async {
    final id = await AssistanceConversationStorage.instance.read();
    if (!mounted || id == null || _conversationId != null) return;

    setState(() {
      _conversationId = id;
      _restoringHistory = true;
    });

    try {
      final history = await fetchAssistanceHistory(id);
      if (!mounted) return;
      if (history == null) {
        await AssistanceConversationStorage.instance.clear();
        setState(() {
          _conversationId = null;
          _restoringHistory = false;
        });
        return;
      }
      setState(() {
        _messages
          ..clear()
          ..addAll(_historyMessagesToChat(history.messages));
        _restoringHistory = false;
      });
      // À l'ouverture d'une conversation depuis l'historique on saute
      // directement en bas (cf. `_scrollToBottom` : saut immédiat).
      _scrollToBottom();
      // D.1.4.2 — défense en profondeur : la conversation est aussi
      // marquée lue côté `AssistanceConversationsScreen` au tap (règle
      // métier : « ouverte = lue »). On répète ici fire-and-forget pour
      // couvrir les chemins d'entrée alternatifs (deeplink, restauration
      // au lancement de l'app…). Idempotent côté serveur.
      unawaited(markAssistanceConversationRead(id));
      // D.1.4.5 — si la conv est dans un état « assistant en cours
      // d'écriture » (dernier msg = user mais pas encore d'assistant
      // commit), on poll jusqu'à voir la réponse arriver.
      _startPollingIfPending();
    } catch (_) {
      // L'historique n'est pas critique : si le serveur est indisponible,
      // on garde le _conversationId pour que le prochain envoi continue
      // bien le thread, mais on permet à l'utilisateur d'écrire dès
      // maintenant sans bloquer l'UI.
      if (!mounted) return;
      setState(() => _restoringHistory = false);
    }
  }

  void _onInputChanged() => setState(() {});

  void _onScroll() {
    final offset =
        _scrollController.hasClients ? _scrollController.offset : 0.0;
    final next =
        ((offset - _navFadeStart) / _navFadeRange).clamp(0.0, 1.0);
    if ((next - _navTitleOpacity).abs() > 0.02) {
      setState(() => _navTitleOpacity = next);
    }
  }

  @override
  void dispose() {
    _stopPolling();
    _controller.removeListener(_onInputChanged);
    _scrollController.removeListener(_onScroll);
    _controller.dispose();
    _scrollController.dispose();
    _inputFocusNode.dispose();
    // D.1.4.8 — libère les ressources natives micro/Whisper si elles
    // ont été allouées (lazy init).
    final transcriber = _voiceTranscriber;
    _voiceTranscriber = null;
    if (transcriber != null) {
      // Fire-and-forget : le dispose du transcriber peut être async
      // (cleanup de fichiers temp pour Whisper) mais on ne bloque pas
      // le dispose du widget.
      unawaited(transcriber.dispose());
    }
    super.dispose();
  }

  // ── Polling « catch-up » ───────────────────────────────────────────
  //
  // Démarré après `_restoreConversationIdFromStorage` quand le dernier
  // message rejoué est un `user` (= l'assistant est en cours d'écriture
  // côté serveur, on attend qu'il commit son tour). Le typing indicator
  // est affiché pendant ce temps (réutilise `_loading`).

  void _startPollingIfPending() {
    if (_pollingTimer != null) return;
    if (_messages.isEmpty) return;
    final id = _conversationId;
    if (id == null) return;
    // On poll uniquement si le dernier message local est `user`
    // (assistant en train d'écrire côté serveur). Avec le streaming
    // silencieux (D.1.4.5 v2 — réponse d'un coup), on n'a plus de cas
    // « assistant partiel » côté UI puisqu'on ne commite la bulle
    // assistant qu'au `done`.
    if (_messages.last.role != 'user') return;

    _pollingAttempts = 0;
    if (!_loading) setState(() => _loading = true);

    _pollingTimer = Timer.periodic(_pollInterval, (timer) async {
      if (!mounted) {
        timer.cancel();
        return;
      }
      _pollingAttempts++;
      if (_pollingAttempts >= _pollMaxAttempts) {
        // C.3 — filet de sécurité : après 24×5s = 2 min sans réponse
        // assistant côté serveur, on sort le user du state loading
        // avec un message d'erreur clair plutôt que de laisser le
        // spinner indéfiniment. Avec C.1+C.2 côté backend, ce cas
        // ne devrait quasi plus jamais arriver (retry LLM + fallback
        // persistant), mais on garde la garantie UX côté mobile.
        _stopPolling(
          errorMessage:
              'Pas de réponse pour le moment. Réessaie dans un instant.',
        );
        return;
      }
      final currentId = _conversationId;
      if (currentId == null) {
        _stopPolling();
        return;
      }
      try {
        final history = await fetchAssistanceHistory(currentId);
        if (!mounted) return;
        if (history == null) {
          // Conv supprimée / 404 : on lâche prise, le storage sera nettoyé
          // au prochain `_restoreConversationIdFromStorage`.
          _stopPolling(
            errorMessage: 'Conversation introuvable. Réessaie.',
          );
          return;
        }
        if (history.messages.isEmpty) return;
        final lastSrv = history.messages.last;
        if (lastSrv.role == 'assistant') {
          // Resync depuis le serveur (au cas où plusieurs messages auraient
          // été ajoutés entre-temps). Pas de re-scroll : on conserve
          // la position courante (généralement le user message en
          // haut, calé à l'envoi).
          setState(() {
            _messages
              ..clear()
              ..addAll(_historyMessagesToChat(history.messages));
            _loading = false;
          });
          unawaited(markAssistanceConversationRead(currentId));
          _stopPolling();
        }
      } catch (_) {
        // Erreur réseau transient → on retentera au tick suivant.
      }
    });
  }

  /// Arrête le polling « catch-up ».
  ///
  /// - Sans argument : cancel simple (utilisé sur path nominal,
  ///   dispose, navigation, etc.). Ne touche pas à `_loading` ni
  ///   à `_error` (le caller gère).
  /// - Avec [errorMessage] : usage « fail-stop » côté C.3. Force
  ///   `_loading = false` et expose un message d'erreur visible à
  ///   l'utilisateur si on était bien en attente d'une réponse
  ///   assistant. Idempotent : ne ré-écrit pas un état déjà nettoyé.
  void _stopPolling({String? errorMessage}) {
    _pollingTimer?.cancel();
    _pollingTimer = null;
    _pollingAttempts = 0;
    if (errorMessage != null && mounted && _loading) {
      setState(() {
        _loading = false;
        _error = errorMessage;
      });
    }
  }

  Future<void> _sendMessage({String? agentHint}) async {
    final text = _controller.text.trim();
    if (text.isEmpty || _loading) return;

    // 1) Fermer le clavier dès le tap sur send : sans ça, l'animation
    //    de scroll qui suit travaillerait sur un viewport en cours de
    //    redimensionnement (clavier qui descend), ce qui rendrait le
    //    mouvement chaotique.
    FocusManager.instance.primaryFocus?.unfocus();
    SystemChannels.textInput.invokeMethod<void>('TextInput.hide');

    // 2) Si un polling de catch-up tournait sur la conv, on l'arrête :
    //    on reprend la main avec un envoi explicite.
    _stopPolling();

    _controller.clear();
    // 3) Nouvelle key pour la bulle user qui va être ajoutée — utilisée
    //    juste après pour la caler en haut du viewport.
    _lastUserMessageKey = GlobalKey();

    // 3.bis) Capturer `maxScrollExtent` AVANT le rebuild qui ajoute le
    //   user message. Cette valeur permet de calculer la cible de
    //   scroll « théorique » du user message (= où il sera positionné
    //   après le rebuild) sans avoir besoin du `RenderBox` du widget
    //   (qui peut ne pas être construit si l'utilisateur lit des
    //   anciens messages plus haut). Cette cible est **stable** : elle
    //   ne dépend pas du contenu IA ajouté APRÈS pendant l'animation,
    //   donc le scroll ne dérive pas vers la réponse en cours.
    //   Cf. `_scrollLastUserToTop` pour la formule.
    final oldMaxScrollExtent = _scrollController.hasClients
        ? _scrollController.position.maxScrollExtent
        : null;

    setState(() {
      _error = null;
      // D.1.4.7 — l'utilisateur envoie un nouveau message : un éventuel
      // QCM « retry après cancel » devient caduc, on libère la mémoire
      // associée pour que le bouton « Relancer » d'un ancien QCM (resté
      // visible dans la liste) ne déclenche plus rien si re-cliqué.
      _pendingRetryText = null;
      // D.1.4.7 (UX QCM) — Si le dernier message assistant est un QCM
      // encore en attente (aucune option cliquée, `selectedChoiceId`
      // null) et que l'utilisateur envoie un message libre par-dessus,
      // on **court-circuite** ce QCM : marquage avec la sentinelle
      // « consommé sans sélection » → toutes les options grisées et
      // non-cliquables, exactement comme après un clic d'option mais
      // sans aucune en avant. Symétrique de [_handleChoiceTap] qui
      // pose `selectedChoiceId = option.id` AVANT l'envoi. Idempotent
      // : si l'envoi vient d'un clic d'option (`selectedChoiceId`
      // déjà set), le helper ne touche à rien.
      _markPendingChoicesAsConsumedWithoutSelection();
      _messages.add(_ChatMessage(
        role: 'user',
        content: text,
        createdAt: DateTime.now(),
      ));
      _loading = true;
    });
    // 4) Scroll fluide pour amener la nouvelle bulle user juste sous
    //    la navbar (avec la marge top du ListView comme zone de
    //    sécurité). Le typing indicator et la future réponse arrivent
    //    en dessous, dans l'espace blanc — pas de re-scroll ensuite.
    _scrollLastUserToTop(oldMaxScrollExtent: oldMaxScrollExtent);

    // ── Phase 2 D.1.4.5 — STREAMING SSE ───────────────────────────────
    // Stream consommé silencieusement : on accumule tous les deltas en
    // mémoire (`buffer`) sans toucher à l'UI, puis on affiche la
    // réponse **d'un coup** au `done` (style WhatsApp). Tant que `done`
    // n'est pas reçu, l'UI montre la bulle typing animée.
    //
    // Si le stream échoue (réseau, proxy, edge buffering…), on bascule
    // automatiquement sur le polling : la requête a déjà créé la conv
    // côté serveur (commit early — D.1.4.4), et le pipeline OpenAI
    // continue côté serveur même si le client a déconnecté.
    //
    // D.1.4.7 — On utilise `startAssistanceTurnStream` qui retourne un
    // [AssistanceTurnHandle] annulable. On le stocke dans
    // `_activeTurnHandle` pour permettre au bouton stop de l'arrêter.
    final buffer = StringBuffer();
    final handle = startAssistanceTurnStream(
      conversationId: _conversationId,
      content: text,
      agentHint: agentHint,
    );
    _activeTurnHandle = handle;

    try {
      await for (final ev in handle.events) {
        if (!mounted) return;
        switch (ev.type) {
          case 'started':
            // 1ʳᵉ frame : on connaît l'ID de conversation avant même le
            // 1ᵉʳ token. On le persiste tout de suite pour garantir la
            // reprise au prochain lancement, même si la connexion lâche.
            final convId = ev.conversationId;
            if (convId != null && convId.isNotEmpty) {
              _conversationId = convId;
              unawaited(
                AssistanceConversationStorage.instance.write(convId),
              );
            }
            break;

          case 'delta':
            final delta = ev.deltaContent ?? '';
            if (delta.isEmpty) break;
            // Accumulation silencieuse en mémoire (pas de `setState`)
            // pour préserver l'effet « réponse d'un coup » quand le
            // serveur émet `done` : tant que la réponse n'est pas
            // complète, l'UI reste sur la bulle typing (typing
            // indicator façon WhatsApp).
            buffer.write(delta);
            break;

          case 'choices':
            // Multi-agents Phase 1 — le router est indécis, il pousse
            // un QCM. On ajoute un message assistant `messageType=
            // 'choices'` qui sera rendu en boutons cliquables par
            // [_buildChoicesBubble]. Pas de bulle Markdown, pas de
            // typing-to-bubble fade : c'est un message d'un autre
            // type, pas une réponse.
            if (!mounted) return;
            final prompt = ev.choicesPrompt ?? '';
            final options = ev.choicesOptions;
            if (options.isEmpty) break;
            final fallbackText = StringBuffer(prompt);
            for (var i = 0; i < options.length; i++) {
              fallbackText.write('\n${i + 1}. ${options[i].label}');
            }
            setState(() {
              _messages.add(_ChatMessage(
                role: 'assistant',
                content: fallbackText.toString(),
                createdAt: DateTime.now(),
                agentUsed: ev.agentUsed ?? 'router',
                messageType: 'choices',
                choicesPayload: AssistanceChoicesPayload(
                  options: options,
                  allowFreeform: ev.choicesAllowFreeform,
                ),
              ));
              _loading = false;
            });
            // Marque comme lue (le QCM est un message assistant
            // affiché → règle métier « ouverte = lue »).
            final convId = _conversationId;
            if (convId != null && convId.isNotEmpty) {
              unawaited(markAssistanceConversationRead(convId));
            }
            break;

          case 'done':
            if (!mounted) return;
            // Si on a déjà ajouté un message `choices` côté UI (cas
            // QCM), le `done` qui suit est juste une confirmation de
            // commit serveur — rien à faire de plus côté affichage.
            final lastMsg =
                _messages.isNotEmpty ? _messages.last : null;
            final lastIsChoices =
                lastMsg != null && lastMsg.isChoicesMessage;
            if (lastIsChoices) {
              break;
            }
            // Le serveur a commité le message complet en BDD. On
            // bascule l'UI : la bulle typing fade vers la bulle
            // assistant complète (`AnimatedSwitcher` du dernier slot
            // dans `_buildMessageList`). Pas de re-scroll : le user
            // message reste en haut du viewport (où on l'a calé à
            // l'envoi), la réponse apparaît dans l'espace blanc en
            // dessous — UX façon WhatsApp / iMessage.
            final finalContent = buffer.toString();
            if (finalContent.isNotEmpty) {
              setState(() {
                _messages.add(_ChatMessage(
                  role: 'assistant',
                  content: finalContent,
                  createdAt: DateTime.now(),
                  agentUsed: ev.agentUsed,
                  messageType: ev.messageType ?? 'text',
                  // Phase 2c.2 — embeds UI structurés (cartes
                  // `transaction_detail`, etc.) émis par le serveur sur
                  // ce `done`. Si vide, fallback gracieux (= bulle
                  // markdown classique sans cartes).
                  embeds: ev.doneEmbeds,
                  // Cognitive Bot v4 — Lot 7 V1.1 (2026-05-05) — footer
                  // auto-QCM annexé au message texte (boutons cliquables
                  // sous la bulle markdown). `null` quand le serveur n'a
                  // pas auto-promu (cas usuel) → pas de footer.
                  autoQcmPayload: ev.doneAutoQcm,
                ));
                _loading = false;
              });
              // D.1.4.2 — règle métier « ouverte = lue » : l'utilisateur
              // est sur l'écran au moment où la réponse arrive, on
              // signale donc immédiatement la lecture côté serveur
              // pour faire disparaître la pastille indigo dans
              // l'historique. Fire-and-forget, idempotent (204).
              final convId = _conversationId;
              if (convId != null && convId.isNotEmpty) {
                unawaited(markAssistanceConversationRead(convId));
              }
            }
            // Si `finalContent` est vide (cas pathologique : `done`
            // sans aucun `delta` reçu), on laisse `_loading = true`
            // pour que le bloc post-try lance un polling de récup.
            break;

          case 'error':
            throw ChatApiException(
              0,
              ev.errorMessage ?? 'stream_error',
            );
        }
      }

      if (!mounted) return;
      // Stream terminé. Si `_loading` est encore `true`, c'est qu'on
      // n'a jamais commité de bulle assistant côté UI (aucun `done`
      // valide reçu, ou `done` sans contenu, ou aucun delta + aucun
      // done) : on lance un polling pour récupérer le message commité
      // côté serveur (le pipeline OpenAI continue indépendamment du
      // client).
      if (_loading) {
        if (_conversationId != null) {
          _startPollingIfPending();
          return;
        }
        setState(() => _loading = false);
      }
    } catch (e) {
      if (!mounted) return;

      // D.1.4.7 — Annulation **volontaire** par l'utilisateur (bouton
      // stop) : pas de polling de catch-up. La task serveur a déjà été
      // tuée par `POST /chat/turn/{id}/cancel` → aucun message à
      // récupérer, et déclencher un polling créerait un état "loading"
      // fantôme jusqu'au timeout.
      if (handle.isCancelled) {
        setState(() {
          _loading = false;
          _error = null;
        });
        return;
      }

      // Fallback robuste : si on a au moins l'ID de conversation, on
      // peut toujours tenter un catch-up via polling — le pipeline
      // serveur continue indépendamment du client.
      if (_conversationId != null) {
        _startPollingIfPending();
        return;
      }

      setState(() {
        _loading = false;
        _error = e is ChatApiException ? e.message : e.toString();
      });
    } finally {
      // Clear la référence au handle quoi qu'il arrive — le tour est
      // terminé (succès, erreur, annulation). Évite que le bouton stop
      // d'un futur tour pointe vers un handle obsolète.
      if (identical(_activeTurnHandle, handle)) {
        _activeTurnHandle = null;
      }
    }
  }

  /// MVP D.1.4.7 — Handler du bouton stop (carré blanc affiché à la
  /// place de la flèche d'envoi quand `_loading == true`).
  ///
  /// Effets en chaîne :
  ///
  /// 1. **Cancel serveur + client** : appelle
  ///    [AssistanceTurnHandle.cancel] sur le tour en cours →
  ///    a. ferme la connexion SSE côté mobile (libère l'UI tout de
  ///       suite — le `await for` lève une exception attrapée par le
  ///       bloc catch de [_sendMessage]) ;
  ///    b. POST `/chat/turn/{conv_id}/cancel` côté serveur → la task
  ///       background est `cancel()`-ée, aucun message commité en BDD.
  ///
  /// 2. **Nettoyage UI du message user orphelin** : on **retire la
  ///    bulle user** qu'on venait d'envoyer. Sans ça, l'`AnimatedSwitcher`
  ///    du dernier slot bascule du typing vers
  ///    `_buildAssistantBubble(_messages.last)` qui rend le message
  ///    user comme une bulle assistant (bug visuel : bulle blanche à
  ///    gauche au lieu d'indigo à droite).
  ///
  /// 3. **QCM de récupération** : on insère un message `choices` local
  ///    (jamais persisté côté serveur, disparaît à la prochaine
  ///    ouverture de la conv) qui propose 2 options :
  ///    - `_kRetryAfterCancelOptionId` → relance la demande initiale ;
  ///    - `freeform` → ferme le QCM, focus sur l'input.
  ///    Le texte original est mémorisé dans `_pendingRetryText` pour
  ///    être réutilisé si l'utilisateur clique « Relancer ».
  ///
  /// Le bloc catch de [_sendMessage] détecte `handle.isCancelled` et
  /// skip le polling de catch-up — sinon on déclencherait un état
  /// loading fantôme jusqu'au timeout du polling.
  void _cancelGeneration() {
    final handle = _activeTurnHandle;
    if (handle == null) return;
    if (!_loading) return;

    // Capturer le texte original AVANT toute mutation de la liste —
    // sera utilisé pour le label du QCM et pour le retry effectif.
    String? originalUserText;
    if (_messages.isNotEmpty && _messages.last.role == 'user') {
      originalUserText = _messages.last.content;
    }

    handle.cancel(conversationId: _conversationId);
    _stopPolling();

    setState(() {
      _loading = false;
      _error = null;

      // Retirer le user message orphelin (cf. point 2 ci-dessus).
      if (_messages.isNotEmpty && _messages.last.role == 'user') {
        _messages.removeLast();
      }

      // Insérer le QCM de récupération si on a bien un texte à
      // proposer en retry. Sans texte (cas pathologique : cancel
      // déclenché avant que le user message ne soit dans la liste),
      // on s'abstient pour ne pas afficher un QCM incomplet.
      if (originalUserText != null && originalUserText.trim().isNotEmpty) {
        _pendingRetryText = originalUserText;
        _messages.add(_buildCancelRetryChoicesMessage(originalUserText));
      } else {
        _pendingRetryText = null;
      }
    });
  }

  /// Construit le message `choices` local affiché juste après un stop
  /// volontaire (cf. [_cancelGeneration]). Le format est strictement
  /// identique aux QCM serveur (rendu via `_buildChoicesBubble`),
  /// hormis :
  ///   - `agentUsed = 'router'` → pas de badge agent (cf.
  ///     `_buildAgentBadge` qui skip explicitement `'router'`) ;
  ///   - les options sont des IDs **locaux** (`retry_after_cancel`,
  ///     `freeform`), pas des `agent_id` valides — c'est
  ///     [_handleChoiceTapped] qui les intercepte.
  _ChatMessage _buildCancelRetryChoicesMessage(String originalUserText) {
    const promptText =
        "Tu as arrêté la recherche. Tu veux la relancer ?";
    final retryLabel = _formatRetryLabel(originalUserText);

    final options = <AssistanceChoiceOption>[
      AssistanceChoiceOption(
        id: _kRetryAfterCancelOptionId,
        label: retryLabel,
      ),
      const AssistanceChoiceOption(
        id: 'freeform',
        label: 'Non, je préfère reformuler',
      ),
    ];

    // Le `content` sert de fallback texte (extrait par
    // `_extractChoicesPrompt` pour le rendu du prompt en haut du
    // module) — on respecte le format « prompt\n1. opt1\n2. opt2 ».
    final fallbackText = StringBuffer(promptText);
    for (var i = 0; i < options.length; i++) {
      fallbackText.write('\n${i + 1}. ${options[i].label}');
    }

    return _ChatMessage(
      role: 'assistant',
      content: fallbackText.toString(),
      createdAt: DateTime.now(),
      agentUsed: 'router',
      messageType: 'choices',
      choicesPayload: AssistanceChoicesPayload(
        options: options,
        // `allowFreeform: false` car on a déjà ajouté manuellement
        // l'option freeform dans `options` avec un label personnalisé
        // (« Non, je préfère reformuler ») plus parlant dans ce
        // contexte que le « Rien de tout ça » générique.
        allowFreeform: false,
      ),
    );
  }

  /// Formate le label du bouton « Relancer » en troncant le texte
  /// original à ~40 caractères pour éviter qu'un message long ne
  /// déborde du bouton ou ne le rende illisible. Garde les guillemets
  /// pour rappeler que c'est une citation textuelle.
  String _formatRetryLabel(String originalText) {
    final trimmed = originalText.trim().replaceAll('\n', ' ');
    if (trimmed.length <= 40) {
      return 'Relancer : « $trimmed »';
    }
    return 'Relancer : « ${trimmed.substring(0, 37)}… »';
  }

  // ── Voice input handlers (D.1.4.8) ────────────────────────────────

  /// Tap sur le bouton micro à droite de l'input pill. Démarre le
  /// flow voice :
  ///   1. Lazy-init du transcriber selon la factory (native/whisper).
  ///   2. Demande la permission micro (modale système iOS/Android au
  ///      premier appel) — si refusée, snackbar et retour à idle.
  ///   3. Démarre l'enregistrement et passe en `recording`.
  ///
  /// Aucune action si déjà en train d'enregistrer / transcrire ou si
  /// une génération IA est en cours (cas couverts par le rendu
  /// conditionnel du bouton micro, défense en profondeur ici).
  Future<void> _startVoiceRecording() async {
    if (_voiceState != _VoiceInputState.idle || _loading) return;

    final transcriber = _voiceTranscriber ?? VoiceTranscriberFactory.create();
    _voiceTranscriber = transcriber;

    try {
      await transcriber.initialize();
    } on VoiceTranscriberException catch (e) {
      if (!mounted) return;
      _showVoiceErrorSnackbar(_messageForVoiceError(e.error));
      return;
    } catch (_) {
      if (!mounted) return;
      _showVoiceErrorSnackbar(
        'Le moteur vocal n’est pas disponible sur cet appareil.',
      );
      return;
    }

    // Permission micro : on appelle à chaque tap. Le check est rapide
    // (l'OS répond immédiatement si déjà accordé, et l'impl
    // `_checkOrRequestMicrophonePermission` n'affiche la modale système
    // que si vraiment nécessaire). Ça permet aussi de re-détecter si
    // l'utilisateur a révoqué la permission entre 2 sessions.
    final granted = await transcriber.requestPermissions();
    if (!mounted) return;
    if (!granted) {
      _showVoicePermissionDeniedSnackbar();
      return;
    }

    try {
      await transcriber.startListening();
    } on VoiceTranscriberException catch (e) {
      if (!mounted) return;
      _showVoiceErrorSnackbar(_messageForVoiceError(e.error));
      return;
    } catch (_) {
      if (!mounted) return;
      _showVoiceErrorSnackbar(
        'Impossible de démarrer l’enregistrement audio.',
      );
      return;
    }

    if (!mounted) return;
    setState(() {
      _voiceState = _VoiceInputState.recording;
      // L'utilisateur a explicitement choisi le voice : on ferme le
      // clavier s'il était ouvert pour ne pas avoir 2 surfaces de saisie.
      _inputFocusNode.unfocus();
    });
  }

  /// Stop ⊠ pendant `recording` → on passe en `transcribing` avec
  /// l'action `inject`. Une fois la transcription terminée, le texte
  /// sera placé dans le `_controller` et l'utilisateur pourra l'éditer
  /// avant d'envoyer manuellement.
  Future<void> _stopVoiceAndInject() async {
    await _stopVoiceWithAction(_VoiceTranscribeAction.inject);
  }

  /// ✓ pendant `recording` → on passe en `transcribing` avec l'action
  /// `send`. Une fois la transcription terminée, on appelle directement
  /// `_sendMessageWithText` sans laisser l'utilisateur éditer.
  Future<void> _stopVoiceAndSend() async {
    await _stopVoiceWithAction(_VoiceTranscribeAction.send);
  }

  /// Implémentation commune au stop avec injection ou envoi : passe
  /// en transcribing, attend le résultat, dispatche selon `action`.
  /// Si `cancel` est appelé entre temps, on ne fait rien (le state
  /// est déjà repassé à idle par `_cancelVoiceFlow`).
  Future<void> _stopVoiceWithAction(_VoiceTranscribeAction action) async {
    final transcriber = _voiceTranscriber;
    if (transcriber == null) return;
    if (_voiceState != _VoiceInputState.recording) return;

    setState(() {
      _voiceState = _VoiceInputState.transcribing;
    });

    String? transcript;
    try {
      transcript = await transcriber.stopAndTranscribe();
    } on VoiceTranscriberException catch (e) {
      if (!mounted) return;
      // Si l'utilisateur a cancel pendant la transcription, le state
      // est déjà idle — on ne montre pas le snackbar.
      if (_voiceState != _VoiceInputState.transcribing) return;
      setState(() {
        _voiceState = _VoiceInputState.idle;
      });
      // `emptyTranscript` après un stop volontaire = l'utilisateur n'a
      // rien dit ou a parlé trop bas. On reste silencieux pour ne pas
      // bombarder de snackbars (ChatGPT fait pareil : retour à l'input
      // vide sans message).
      if (e.error != VoiceTranscriberError.emptyTranscript) {
        _showVoiceErrorSnackbar(_messageForVoiceError(e.error));
      }
      return;
    } catch (_) {
      if (!mounted) return;
      if (_voiceState != _VoiceInputState.transcribing) return;
      setState(() {
        _voiceState = _VoiceInputState.idle;
      });
      _showVoiceErrorSnackbar('Erreur inattendue lors de la transcription.');
      return;
    }

    if (!mounted) return;
    // Si l'utilisateur a cancel pendant qu'on attendait, on ignore le
    // résultat (state déjà repassé à idle).
    if (_voiceState != _VoiceInputState.transcribing) return;

    setState(() {
      _voiceState = _VoiceInputState.idle;
    });

    final text = transcript.trim();
    if (text.isEmpty) return;

    switch (action) {
      case _VoiceTranscribeAction.inject:
        // On remplace le contenu du TextField (pas append) pour ne pas
        // mélanger un éventuel texte tapé manuellement avec la dictée
        // — comportement attendu par l'utilisateur.
        _controller.text = text;
        _controller.selection = TextSelection.fromPosition(
          TextPosition(offset: _controller.text.length),
        );
        _inputFocusNode.requestFocus();
        break;
      case _VoiceTranscribeAction.send:
        _sendMessageWithText(text);
        break;
    }
  }

  /// Stop ⊠ à gauche de l'input pendant `recording` OU `transcribing`.
  /// Annule complètement le flow voice : enregistrement coupé, audio
  /// jeté (Whisper), transcription en cours abandonnée. L'UI revient
  /// à l'état idle, sans snackbar (annulation volontaire).
  Future<void> _cancelVoiceFlow() async {
    final transcriber = _voiceTranscriber;
    if (_voiceState == _VoiceInputState.idle) return;

    setState(() {
      _voiceState = _VoiceInputState.idle;
    });

    if (transcriber != null) {
      // `cancel()` est idempotent côté transcriber.
      await transcriber.cancel();
    }
  }

  /// Mappage erreur transcriber → message utilisateur (FR, ton aligné
  /// avec le reste de l'app : direct, sans condescendance).
  String _messageForVoiceError(VoiceTranscriberError err) {
    switch (err) {
      case VoiceTranscriberError.permissionDenied:
        return 'L’accès au micro a été refusé.';
      case VoiceTranscriberError.engineUnavailable:
        return 'La reconnaissance vocale n’est pas disponible sur cet appareil.';
      case VoiceTranscriberError.networkFailure:
        return 'Connexion impossible pour la transcription.';
      case VoiceTranscriberError.emptyTranscript:
        return 'Aucune parole détectée.';
      case VoiceTranscriberError.internal:
        return 'Erreur du moteur vocal.';
    }
  }

  void _showVoiceErrorSnackbar(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        duration: const Duration(seconds: 3),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  /// Snackbar dédié au refus de permission, avec action « Réglages »
  /// pour diriger l'utilisateur vers le panneau OS où il peut
  /// réautoriser.
  void _showVoicePermissionDeniedSnackbar() {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Text(
          'Pour dicter vos questions, autorisez l’accès au micro dans les réglages.',
        ),
        duration: const Duration(seconds: 5),
        behavior: SnackBarBehavior.floating,
        action: SnackBarAction(
          label: 'Réglages',
          onPressed: () {
            // openAppSettings vient de permission_handler.
            openAppSettings();
          },
        ),
      ),
    );
  }

  /// Ouvre la page « Mes conversations » (D.1.4). Au retour, si l'utilisateur
  /// a sélectionné une conversation, elle a déjà été inscrite dans le secure
  /// storage par la page (cf. [AssistanceConversationStorage]). On vide alors
  /// le state local et on redéclenche la restauration (D.1.6) pour rejouer
  /// l'historique de la conversation choisie.
  Future<void> _openConversationsHistory() async {
    final selectedId = await Navigator.of(context).push<String?>(
      MaterialPageRoute(
        builder: (_) => const AssistanceConversationsScreen(),
      ),
    );
    if (!mounted) return;
    if (selectedId == null || selectedId.isEmpty) return;
    if (selectedId == _conversationId && _messages.isNotEmpty) {
      // Même conversation, déjà chargée — rien à faire.
      return;
    }
    _stopPolling();
    // D.1.4.8 — si un voice flow est actif, on l'annule avant de
    // changer de conversation pour éviter qu'un transcript en cours
    // ne pollue la nouvelle conv.
    unawaited(_cancelVoiceFlow());
    setState(() {
      _messages.clear();
      _conversationId = null;
      _error = null;
      _loading = false;
      _controller.clear();
      // D.1.4.7 — un éventuel QCM « retry après cancel » de la conv
      // précédente n'a plus de sens dans ce nouveau contexte.
      _pendingRetryText = null;
    });
    await _restoreConversationIdFromStorage();
  }

  /// Démarre une nouvelle conversation : vide l'écran, oublie l'ID courant
  /// (le prochain `_sendMessage` créera une conversation côté serveur) et
  /// remet le focus sur l'input.
  Future<void> _startNewConversation() async {
    _stopPolling();
    // D.1.4.8 — symétrique de `_openConversationsHistory` : on annule
    // tout voice flow en cours avant le reset.
    unawaited(_cancelVoiceFlow());
    setState(() {
      _messages.clear();
      _conversationId = null;
      _error = null;
      _restoringHistory = false;
      _loading = false;
      _controller.clear();
      // D.1.4.7 — reset du retry pendant comme pour les autres reset.
      _pendingRetryText = null;
    });
    await AssistanceConversationStorage.instance.clear();
  }

  /// Cale la liste sur le dernier message — toujours en saut immédiat
  /// (façon WhatsApp / iMessage : pas d'animation de scroll explicite,
  /// la nouvelle bulle apparaît directement en bas sans yoyo ni bounce).
  ///
  /// Utilisé uniquement à la **restauration d'historique** (D.1.6) :
  /// on veut afficher d'emblée le bas de la conversation. Pour l'envoi
  /// d'un nouveau message user, voir [_scrollLastUserToTop].
  ///
  /// Double `jumpTo` post-frame : `ListView.builder` rend les items en
  /// lazy, donc `maxScrollExtent` peut augmenter au fur et à mesure que
  /// les bulles Markdown se construisent. On fait donc une 2ᵉ passe
  /// au frame suivant pour rattraper cette stabilisation tardive.
  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.jumpTo(_scrollController.position.maxScrollExtent);
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!_scrollController.hasClients) return;
        _scrollController.jumpTo(_scrollController.position.maxScrollExtent);
      });
    });
  }

  /// Cale la dernière bulle user **16 px sous la navbar** avec une
  /// animation fluide (300 ms, `Curves.easeOutCubic`) — façon
  /// ChatGPT/iMessage. Fonctionne quelle que soit la position scroll
  /// courante (haut, milieu, bas) **et** que l'IA commence à streamer
  /// pendant l'animation ou pas.
  ///
  /// Subtilité 1 — `ListView.builder` lazy : si l'utilisateur lit des
  /// anciens messages, le dernier user message (juste ajouté à la
  /// fin) n'est pas dans le tree, donc pas de `RenderBox` accessible
  /// → on doit calculer la cible **sans le RenderBox**.
  ///
  /// Subtilité 2 — Pendant l'animation (300 ms), l'IA peut commencer
  /// à répondre, ce qui ajoute du contenu **après** le user message
  /// → `maxScrollExtent` augmente. Cibler `maxScrollExtent` est donc
  /// **instable** : on dérive vers la réponse IA en cours au lieu de
  /// caler le user message en haut. Il faut une cible **figée** sur
  /// la position du user message, indépendante du contenu qui suit.
  ///
  /// Stratégie : calcul d'une **cible théorique stable** depuis
  /// `oldMaxScrollExtent` (capturé AVANT le `setState` qui ajoute le
  /// user message) :
  ///
  /// ```
  /// oldTotalContent = oldMaxScrollExtent + viewportHeight
  ///                 = topPadding + Σ(items anciens) + dynamicBottom
  /// dynamicBottom    = viewportHeight - safetyTop - inputBarHeight
  /// →  topPadding + Σ(items anciens)
  ///                 = oldMaxScrollExtent + safetyTop + inputBarHeight
  /// ```
  ///
  /// Le top du nouveau user message dans le contenu est exactement
  /// `topPadding + Σ(items anciens)`. Pour l'aligner à `safetyTop`
  /// du top du viewport :
  ///
  /// ```
  /// target = (topPadding + Σ(items anciens)) - safetyTop
  ///        = oldMaxScrollExtent + inputBarHeight
  /// ```
  ///
  /// Cette quantité ne dépend QUE des items précédents → elle est
  /// stable même si l'IA pousse du contenu après pendant l'animation.
  ///
  /// Algorithme :
  ///   1. Animer `animateTo(target = oldMaxScrollExtent + inputBarHeight)`
  ///      en 300 ms easeOutCubic, clampé dans `[min, maxScrollExtent]`.
  ///   2. À l'arrivée, le widget user est construit (on est près de
  ///      lui). Petit ajustement final via `getOffsetToReveal` pour
  ///      gérer les user messages multi-lignes — la formule théorique
  ///      a une légère imprécision en cas de message long
  ///      (≤ ~30 px, imperceptible mais corrigée pour propreté).
  void _scrollLastUserToTop({double? oldMaxScrollExtent}) {
    // Stoppe toute simulation/animation de scroll en cours (ex.
    // ballistic scroll quand l'utilisateur tape « send » pendant le
    // relâchement d'un drag). Sans ça, la `BallisticSimulation` peut
    // continuer à modifier l'offset en parallèle de notre `animateTo`
    // et créer des dérives imprévisibles.
    if (_scrollController.hasClients) {
      _scrollController.position.jumpTo(_scrollController.offset);
    }

    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) return;
      if (!_scrollController.hasClients) return;

      // ── Phase 1 — animation principale ────────────────────────────
      // Cible théorique stable calculée à partir de `oldMaxScrollExtent`
      // (capturé AVANT le rebuild qui ajoute le user message) :
      //
      //     target = oldMaxScrollExtent + inputBarHeight
      //
      // Cette cible est INDÉPENDANTE du contenu ajouté APRÈS le user
      // message (typing indicator, réponse IA en streaming, etc.).
      // Elle reste valable même si l'IA commence à répondre pendant
      // l'animation. C'est la SEULE cible qui ne dérive pas.
      //
      // Si on n'a pas pu capturer (ex: premier message d'une conv
      // neuve), on retombe directement en phase 2 — RenderBox.
      double? theoreticalTarget;
      if (oldMaxScrollExtent != null) {
        final position = _scrollController.position;
        theoreticalTarget = (oldMaxScrollExtent + _kInputBarHeight)
            .clamp(position.minScrollExtent, position.maxScrollExtent);
        await _scrollController.animateTo(
          theoreticalTarget,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOutCubic,
        );
      }

      // ── Phase 2 — correction RenderBox avec garde anti-dérive ────
      // Maintenant qu'on est arrivé près du user message, le ListView.
      // builder a normalement construit son widget. On peut donc
      // raffiner via `getOffsetToReveal` pour gérer l'imprécision
      // théorique sur les user messages multi-lignes (≤ 30 px).
      //
      // GARDE ANTI-DÉRIVE : si la cible précise est très différente
      // de l'offset courant (> _kCorrectionMaxDelta), c'est qu'on
      // pointe vraisemblablement vers un autre widget (anomalie de
      // mesure, conv très longue où user_new pas encore construit
      // mais GlobalKey attachée à autre chose, etc.) → on ignore.
      // Mieux vaut une légère imprécision visible que dériver vers
      // un message IA.
      if (!mounted) return;
      if (!_scrollController.hasClients) return;
      final rb = _lastUserMessageRenderBox();
      if (rb == null) return;

      final viewport = RenderAbstractViewport.of(rb);
      final reveal = viewport.getOffsetToReveal(rb, 0.0);
      final p = _scrollController.position;
      final preciseTarget = (reveal.offset - _kScrollSafetyTop)
          .clamp(p.minScrollExtent, p.maxScrollExtent);
      final delta = (preciseTarget - _scrollController.offset).abs();

      if (delta < 1.0) return; // déjà aligné
      if (delta > _kCorrectionMaxDelta) return; // anti-dérive

      await _scrollController.animateTo(
        preciseTarget,
        duration: const Duration(milliseconds: 120),
        curve: Curves.easeOutCubic,
      );
    });
  }

  /// Seuil au-delà duquel la correction post-animation est considérée
  /// comme une dérive (anomalie de mesure, GlobalKey attachée à un
  /// widget inattendu, etc.) et donc ignorée. 100 px couvre largement
  /// l'imprécision théorique normale (max ≈ 30 px pour un user message
  /// multi-lignes), tout en bloquant les sauts de plusieurs centaines
  /// de px qui amèneraient la vue sur la réponse IA en cours.
  static const double _kCorrectionMaxDelta = 100.0;

  /// Récupère le `RenderBox` de la bulle marquée par
  /// `_lastUserMessageKey`. Renvoie `null` si la `GlobalKey` n'est pas
  /// (encore) attachée à un widget construit dans l'arbre.
  RenderBox? _lastUserMessageRenderBox() {
    final ctx = _lastUserMessageKey?.currentContext;
    if (ctx == null) return null;
    final ro = ctx.findRenderObject();
    if (ro is! RenderBox) return null;
    return ro;
  }

  /// Marge entre la navbar et le top du dernier user message quand on
  /// le cale en haut à l'envoi (cf. `_scrollLastUserToTop`). Token DS
  /// `AppSpacing.lg` (= 16 px) — séparation confortable façon iMessage.
  static const double _kScrollSafetyTop = AppSpacing.lg;

  @override
  Widget build(BuildContext context) {
    final topPadding = MediaQuery.paddingOf(context).top;
    final navBarHeight = topPadding + _kAppTopNavBarHeight;

    return Scaffold(
      // Aligne le ton de la page sur les autres écrans "liste" (Markets,
      // Articles…) : fond [pageBackground] gris clair. Cela donne le contraste
      // attendu pour les disques blancs (cardBackground) du [AppTopNavBar],
      // exactement comme dans Markets et la page detail bundle crypto.
      backgroundColor: AppColors.pageBackground,
      body: Stack(
        children: [
          Column(
            children: [
              SizedBox(height: navBarHeight),
              Expanded(
                // Le clavier est fermé automatiquement par [TextField.onTapOutside]
                // (cf. [_buildInputPill]) qui s'appuie sur un [TapRegion] interne :
                // captant le pointer-down avant que les [SelectableText] des
                // bulles assistant ne consomment le geste. Pas besoin d'un
                // [GestureDetector] englobant.
                child: _restoringHistory && _messages.isEmpty
                    ? _buildHistoryRestoreLoader()
                    : _messages.isEmpty
                        ? _buildEmptyState()
                        : _buildMessageList(),
              ),
              if (_error != null) _buildErrorBanner(),
              SizedBox(height: _kInputBarHeight + MediaQuery.paddingOf(context).bottom),
            ],
          ),
          // Nav bar transparent en haut → fade vers blur + titre au scroll up
          // (même comportement que [LayoutPageLevel2] sur les pages detail bundle).
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            height: navBarHeight,
            child: _buildNavBarWithBlur(),
          ),
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: SafeArea(
              top: false,
              child: _buildInputBar(),
            ),
          ),
        ],
      ),
    );
  }

  /// Hauteur native du [AppTopNavBar] (Figma `TopAppBar` : 60 px).
  static const double _kAppTopNavBarHeight = 60;

  /// Sigma maximum de blur appliqué au navbar quand il est entièrement opaque.
  static const double _kNavBlurSigma = 20;

  /// Navbar style detail bundle : transparent au-dessus du contenu, fade vers
  /// un fond blur quand on scrolle, titre qui apparaît progressivement.
  Widget _buildNavBarWithBlur() {
    final t = _navTitleOpacity;
    final sigma = _kNavBlurSigma * t;
    const fgColor = AppColors.textPrimary;

    final navBar = AppTopNavBar(
      leadingType: AppTopNavBarLeading.back,
      onBackTap: () {
        if (widget.onBack != null) {
          widget.onBack!();
        } else {
          Navigator.of(context).pop();
        }
      },
      actions: [
        AppTopNavBarAction(
          icon: Icons.edit_outlined,
          onPressed: _startNewConversation,
        ),
        AppTopNavBarAction(
          icon: Icons.history_rounded,
          onPressed: _openConversationsHistory,
        ),
      ],
      backgroundColor: Colors.transparent,
      foregroundColor: fgColor,
      useDashboardStyle: false,
      title: 'Assistance sur mesure',
      titleOpacity: t,
      centerTitle: true,
      titleTextStyle: AppTypography.itemPrimary.copyWith(color: fgColor),
    );

    if (t <= 0.01) return navBar;

    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: sigma, sigmaY: sigma),
        child: Container(
          color: AppColors.pageBackground.withValues(alpha: 0.6 * t),
          child: navBar,
        ),
      ),
    );
  }

  /// Tags proposés (mock). Sera remplacé par la base de données plus tard.
  static const List<String> _suggestedTags = [
    'Marché actions',
    'Portfolio',
    'Gestion du risque',
    'Épargne retraite',
    'Diversification',
    'Performance',
  ];

  Widget _buildEmptyState() {
    return LayoutBuilder(
      builder: (context, constraints) {
        return SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xxl),
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          child: Center(
            child: ConstrainedBox(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.sizeOf(context).width * 0.75,
                minHeight: constraints.maxHeight,
              ),
              child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              mainAxisSize: MainAxisSize.max,
              children: [
                SvgPicture.asset(
                  'assets/logo-black-icon.svg',
                  width: 56,
                  height: 56,
                ),
                const SizedBox(height: AppSpacing.lg),
                Text(
                  'Bonjour Gael, comment puis-je vous aider aujourd\'hui ?',
                  style: AppTypography.welcomeTitle,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  'Vous pouvez choisir parmi une des catégories suivantes et vous laisser guider pas à pas.',
                  style: AppTypography.paragraph.copyWith(color: AppColors.textSecondary),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpacing.sm),
                Wrap(
                  alignment: WrapAlignment.center,
                  spacing: 6,
                  runSpacing: 0,
                  children: _suggestedTags
                      .map((tag) => AppSuggestionChip(
                            label: tag,
                            onPressed: () {
                              _controller.text = tag;
                              _sendMessage();
                            },
                          ))
                      .toList(),
                ),
              ],
            ),
            ),
          ),
        );
      },
    );
  }

  static const Duration _loaderToMessageDuration = Duration(milliseconds: 100);
  static const double _kInputBarHeight = 72;

  /// Loader plein écran discret pendant la reprise de l'historique (D.1.6) :
  /// trois points animés au centre, exactement comme le typing indicator
  /// d'une réponse en cours, pour rester cohérent visuellement.
  Widget _buildHistoryRestoreLoader() {
    return const Center(child: _TypingDotsAnimated());
  }

  /// Convertit un [AssistanceHistoryMessage] (DTO API) en [_ChatMessage]
  /// (modèle UI), en propageant les colonnes multi-agents Phase 1
  /// (`agent_used`, `message_type`, `message_payload`) pour rendre les
  /// QCM persistés correctement à la reprise d'une conversation.
  _ChatMessage _chatMessageFromHistory(AssistanceHistoryMessage m) {
    return _ChatMessage(
      role: m.role,
      content: m.content,
      createdAt: m.createdAt,
      agentUsed: m.agentUsed,
      messageType: m.messageType,
      choicesPayload: m.choicesPayload,
      embeds: m.embeds,
      autoQcmPayload: m.autoQcmPayload,
    );
  }

  /// Sentinel utilisé comme `selectedChoiceId` pour marquer un QCM
  /// comme **consommé sans option identifiable**. Deux cas d'usage,
  /// même sémantique visuelle (toutes les options grisées, aucune en
  /// noir, aucun tap actif) :
  ///
  ///   1. **Reprise d'historique** — à l'ouverture d'une conv, les
  ///      QCM non-derniers sont déjà consommés mais l'API mobile
  ///      ne renvoie pas l'option cliquée (pas d'`agent_hint` dans
  ///      le DTO). On marque ces QCM avec ce sentinel pour qu'ils
  ///      apparaissent désactivés.
  ///
  ///   2. **Envoi d'un message libre** — si l'utilisateur tape un
  ///      texte libre dans l'input alors que le dernier message
  ///      assistant est un QCM encore en attente, on considère que
  ///      le QCM est implicitement court-circuité : on le marque
  ///      avec ce sentinel pour griser les options (symétrique du
  ///      clic sur option qui pose `selectedChoiceId = option.id`).
  ///
  /// Distinct de tout `option.id` réel (commence par `__` pour ne
  /// jamais matcher un agent_id ou le `freeform`/`retry_after_cancel`).
  static const String _kConsumedWithoutSelectionSentinel =
      '__consumed_without_selection__';

  /// Si le dernier message assistant de la liste est un QCM encore
  /// en attente (`isChoicesMessage && selectedChoiceId == null`),
  /// le marque comme **consommé sans sélection** via la sentinelle
  /// dédiée. Aucun effet sinon (idempotent).
  ///
  /// Appelé par [_sendMessage] juste avant l'ajout du message user
  /// dans le `setState`, pour que le QCM passe en état grisé/non
  /// cliquable dans le même rebuild que l'apparition de la nouvelle
  /// bulle user. Cas couverts :
  ///   - QCM router (multi-agents Phase 1) court-circuité par une
  ///     question libre.
  ///   - QCM « retry après cancel » court-circuité par un nouveau
  ///     message (le `_pendingRetryText` est par ailleurs déjà mis à
  ///     `null` dans le même `setState`).
  ///
  /// On s'arrête dès qu'on rencontre :
  ///   - un message user (pas de QCM actif au-dessus), ou
  ///   - n'importe quel QCM (qu'on vient juste de marquer, ou qu'il
  ///     soit déjà consommé) — on ne franchit jamais cette barrière
  ///     pour éviter de toucher un QCM plus ancien.
  void _markPendingChoicesAsConsumedWithoutSelection() {
    for (var i = _messages.length - 1; i >= 0; i--) {
      final m = _messages[i];
      if (m.role == 'user') return;
      if (m.isChoicesMessage) {
        if (m.selectedChoiceId == null) {
          _messages[i] =
              m.copyWithSelectedChoiceId(_kConsumedWithoutSelectionSentinel);
        }
        return;
      }
    }
  }

  /// Convertit l'historique serveur en messages UI **et** marque les
  /// QCM non-derniers comme consommés. Sans ça, un utilisateur qui
  /// rouvre une conv pourrait re-cliquer sur une option d'un ancien
  /// QCM router et déclencher un envoi alors que la conv a déjà
  /// poursuivi son cours (UX confuse + risque de doublon).
  ///
  /// Convention : un QCM **est** considéré consommé dès lors qu'il
  /// existe au moins un message après lui dans l'historique. Le
  /// dernier QCM (s'il y en a un) reste cliquable car il représente
  /// l'état actuel de la conversation (clarification en attente côté
  /// utilisateur).
  List<_ChatMessage> _historyMessagesToChat(
    List<AssistanceHistoryMessage> messages,
  ) {
    final result = messages.map(_chatMessageFromHistory).toList();
    for (var i = 0; i < result.length - 1; i++) {
      final m = result[i];
      if (m.isChoicesMessage && m.selectedChoiceId == null) {
        result[i] =
            m.copyWithSelectedChoiceId(_kConsumedWithoutSelectionSentinel);
      }
    }
    return result;
  }

  Widget _buildMessageList() {
    final itemCount = _messages.length + (_loading ? 1 : 0);
    // Index du dernier message user dans `_messages` (-1 si aucun).
    // Sert à attacher la `GlobalKey` (`_lastUserMessageKey`) à la
    // bonne bulle pour le scroll « user-en-haut » à l'envoi.
    int lastUserIndex = -1;
    for (int i = _messages.length - 1; i >= 0; i--) {
      if (_messages[i].role == 'user') {
        lastUserIndex = i;
        break;
      }
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        // Padding bottom dynamique élevé : on réserve un espace en bas
        // ≈ hauteur du viewport - input bar - marge top.
        // Cela garantit que le scroll « user-en-haut » de
        // `_scrollLastUserToTop` peut toujours atteindre sa position
        // cible, même quand la conversation est très courte (sinon
        // `maxScrollExtent` serait trop petit pour ce mouvement).
        // Conséquence visuelle : il reste un grand espace blanc sous
        // le dernier message → exactement l'UX recherchée.
        final dynamicBottom = (constraints.maxHeight -
                _kScrollSafetyTop -
                _kInputBarHeight)
            .clamp(_kInputBarHeight + AppSpacing.md, double.infinity);

        return ListView.builder(
          controller: _scrollController,
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          // Pas de bounce iOS sur la liste de messages : c'est lui qui
          // crée l'effet « yoyo » désagréable. `ClampingScrollPhysics`
          // clip net à la borne, le scroll reste stable comme dans
          // WhatsApp / iMessage.
          physics: const ClampingScrollPhysics(),
          // Cache élargi pour que le dernier user message soit
          // construit même quand l'utilisateur lit un peu plus haut
          // dans la conversation. Cela permet à la correction
          // post-animation de `_scrollLastUserToTop` d'avoir un
          // `RenderBox` disponible et d'aligner précisément à 16 px
          // sous la navbar. Compromis mémoire/UX : 4000 px ≈ 30-40
          // messages typiques en cache hors viewport, négligeable
          // pour un chat.
          cacheExtent: 4000.0,
          padding: EdgeInsets.only(
            left: AppSpacing.lg,
            right: AppSpacing.lg,
            // Padding top initial du ListView. La marge réelle « user
            // message ↔ navbar » à l'envoi est gérée par le calcul
            // d'offset dans `_scrollLastUserToTop` (cf.
            // `_kScrollSafetyTop`), pas par ce padding.
            top: AppSpacing.lg,
            bottom: dynamicBottom,
          ),
          itemCount: itemCount,
          itemBuilder: (context, index) {
            final isLastSlot = index == itemCount - 1;
            if (isLastSlot) {
              // Dernier slot : soit le typing indicator (pendant la
              // génération assistant), soit le dernier message via
              // [AnimatedSwitcher] qui fade les dots vers la bulle au
              // commit `done`. On préfixe par un séparateur de date si
              // le dernier message ouvre un nouveau jour.
              final lastIndex = _messages.length - 1;
              final showSeparator = !_loading &&
                  lastIndex >= 0 &&
                  _shouldShowDateSeparator(lastIndex);
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (showSeparator)
                    _DateSeparator(
                        label: _dateSeparatorLabel(_messages.last.createdAt)),
                  Padding(
                    padding: const EdgeInsets.only(bottom: AppSpacing.lg),
                    child: AnimatedSwitcher(
                      duration: _loaderToMessageDuration,
                      switchInCurve: Curves.easeOut,
                      switchOutCurve: Curves.easeIn,
                      transitionBuilder:
                          (Widget child, Animation<double> animation) {
                        return FadeTransition(opacity: animation, child: child);
                      },
                      child: _loading
                          ? _buildTypingDots(
                              key: const ValueKey<String>('typing'))
                          : KeyedSubtree(
                              key: ValueKey<String>(_messages.last.content),
                              child: _buildAssistantBubble(
                                _messages.last,
                                messageIndex: _messages.length - 1,
                              ),
                            ),
                    ),
                  ),
                ],
              );
            }
            final msg = _messages[index];
            final showSeparator = _shouldShowDateSeparator(index);
            // Attache la key au dernier user message pour le scroll
            // « user-en-haut ». L'assigne à la bulle elle-même (pas au
            // séparateur de date), car `Scrollable.ensureVisible`
            // alignera le top du widget cible avec le top du viewport.
            final keyForBubble =
                index == lastUserIndex ? _lastUserMessageKey : null;
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (showSeparator)
                  _DateSeparator(label: _dateSeparatorLabel(msg.createdAt)),
                Padding(
                  key: keyForBubble,
                  padding: const EdgeInsets.only(bottom: AppSpacing.lg),
                  child: msg.role == 'user'
                      ? _buildUserBubble(msg)
                      : _buildAssistantBubble(msg, messageIndex: index),
                ),
              ],
            );
          },
        );
      },
    );
  }

  // ── Helpers de date / heure (style WhatsApp en français) ────────────────
  //
  // Centralisés ici (dépendent de `DateTime.now()` au moment du rendu) plutôt
  // que dans des fonctions top-level pour éviter de polluer le scope du
  // fichier et garder la logique privée à l'écran.

  static const List<String> _frenchMonths = [
    'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
    'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre',
  ];

  bool _isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  /// `true` si le message à [index] doit être précédé d'un séparateur de
  /// date — cas : 1er message de la liste, ou jour différent de [index-1].
  bool _shouldShowDateSeparator(int index) {
    if (index == 0) return true;
    final prev = _messages[index - 1].createdAt;
    final cur = _messages[index].createdAt;
    return !_isSameDay(prev, cur);
  }

  /// Label du séparateur centré (style WhatsApp) : « Aujourd'hui »,
  /// « Hier » ou la date complète en français pour les jours antérieurs.
  String _dateSeparatorLabel(DateTime date) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final d = DateTime(date.year, date.month, date.day);
    final diff = today.difference(d).inDays;
    if (diff == 0) return "Aujourd'hui";
    if (diff == 1) return 'Hier';
    return '${d.day} ${_frenchMonths[d.month - 1]} ${d.year}';
  }

  /// Heure affichée en bas de chaque bulle :
  ///   • aujourd'hui   → « HH:MM »
  ///   • hier          → « Hier, HH:MM »
  ///   • avant-hier+   → « DD mois YYYY, HH:MM »
  String _messageTimeLabel(DateTime date) {
    final hh = date.hour.toString().padLeft(2, '0');
    final mm = date.minute.toString().padLeft(2, '0');
    final hhmm = '$hh:$mm';
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final d = DateTime(date.year, date.month, date.day);
    final diff = today.difference(d).inDays;
    if (diff == 0) return hhmm;
    if (diff == 1) return 'Hier, $hhmm';
    return '${d.day} ${_frenchMonths[d.month - 1]} ${d.year}, $hhmm';
  }

  Widget _buildUserBubble(_ChatMessage msg) {
    // Bulle user "shrink-to-fit" : largeur = max(longueur des lignes wrappées)
    // + padding horizontal. Sans cette mesure, [Container] prend toujours la
    // pleine largeur du [ConstrainedBox] (le [Text] s'étire jusqu'au maxWidth)
    // d'où l'espace résiduel à droite quand la dernière ligne est plus courte.
    const padding = EdgeInsets.symmetric(
      horizontal: AppSpacing.lg,
      vertical: AppSpacing.md,
    );
    // Bulle envoyée par l'utilisateur : fond accent indigo + texte blanc
    // (style "sent message" iMessage / iOS, cohérent avec la couleur primaire
    // du DS).
    final style = AppTypography.paragraph.copyWith(color: AppColors.white);
    final cap = MediaQuery.sizeOf(context).width * 0.82;

    return Align(
      alignment: Alignment.centerRight,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        mainAxisSize: MainAxisSize.min,
        children: [
          LayoutBuilder(
            builder: (context, constraints) {
              final outerMax = constraints.maxWidth.isFinite
                  ? (constraints.maxWidth < cap ? constraints.maxWidth : cap)
                  : cap;
              final textMax =
                  (outerMax - padding.horizontal).clamp(0.0, double.infinity);

              final painter = TextPainter(
                text: TextSpan(text: msg.content, style: style),
                textDirection: TextDirection.ltr,
                textScaler: MediaQuery.textScalerOf(context),
              )..layout(maxWidth: textMax);
              final bubbleWidth = painter.width + padding.horizontal;

              return Container(
                width: bubbleWidth,
                padding: padding,
                decoration: const BoxDecoration(
                  color: AppColors.accent,
                  // Coin top-right carré : la bulle « pointe » vers son
                  // émetteur (l'utilisateur, à droite) façon iMessage.
                  borderRadius: BorderRadius.only(
                    topLeft: Radius.circular(AppRadius.bubble),
                    topRight: Radius.zero,
                    bottomLeft: Radius.circular(AppRadius.bubble),
                    bottomRight: Radius.circular(AppRadius.bubble),
                  ),
                ),
                child: Text(msg.content, style: style),
              );
            },
          ),
          // Heure sous la bulle, alignée à droite (style iMessage / image
          // Figma fournie). Typo `meta` + couleur `textMuted` du DS.
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.xs, right: 4),
            child: Text(
              _messageTimeLabel(msg.createdAt),
              style: AppTypography.meta.copyWith(color: AppColors.textMuted),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAssistantBubble(_ChatMessage msg, {required int messageIndex}) {
    // Multi-agents Phase 1 — QCM poussé par le router quand son
    // intention est ambiguë. Rendu en boutons cliquables (cf.
    // docs/arquantix/MULTI_AGENTS.md § 1.9).
    if (msg.isChoicesMessage) {
      return _buildChoicesBubble(msg, messageIndex: messageIndex);
    }

    final agentBadge = _buildAgentBadge(msg.agentUsed);

    // Phase 2c.4 — fusion en un seul module visuel quand l'embed
    // self-suffit. Le prompt instruit le LLM à se taire après
    // `read_transaction_detail`, mais en pratique il écrit parfois
    // une phrase d'intro (« Tu as fait un virement bancaire qui a
    // été complété. Voici les détails ci-dessous. »). Or l'embed
    // contient déjà un `summary` composé serveur — chaleureux,
    // factuel, avec montant + date — qui dit la même chose en
    // mieux. La bulle texte LLM est donc **toujours redondante**
    // quand un embed self-contained porte un `summary` non-vide :
    // on la masque sans condition de longueur. Pour les cas où le
    // serveur n'a pas pu composer de summary (rétro-compat), on
    // retombe sur l'heuristique « contenu trivial < 60 chars ».
    final showLlmBubble = !_shouldHideLlmBubbleForEmbeds(msg);

    return Align(
      alignment: Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.92),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            if (agentBadge != null) ...[
              agentBadge,
              const SizedBox(height: AppSpacing.xs),
            ],
            if (showLlmBubble)
              // Module blanc encapsulant la réponse assistant : coin
              // top-left carré (« pointe » vers l'émetteur — l'assistant,
              // à gauche) en miroir de la bulle user (top-right carré).
              // Ombre et radius alignés sur le DS (`AppShadow`,
              // `AppRadius.bubble`).
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.lg,
                  vertical: AppSpacing.md,
                ),
                decoration: const BoxDecoration(
                  color: AppColors.cardBackground,
                  borderRadius: BorderRadius.only(
                    topLeft: Radius.zero,
                    topRight: Radius.circular(AppRadius.bubble),
                    bottomLeft: Radius.circular(AppRadius.bubble),
                    bottomRight: Radius.circular(AppRadius.bubble),
                  ),
                  boxShadow: AppShadow.defaultShadowList,
                ),
                child: ArticleParagraphMarkdown(
                  text: msg.content,
                  baseStyle: AppTypography.paragraph,
                  // Phase 2c.2 — bug fix : sans `onOpenLink`, le markdown
                  // résolu par `flutter_markdown` ouvre les liens via
                  // `launchUrl(externalApplication)` qui ne sait pas
                  // gérer notre scheme `vancelian://...`. Avec ce hook,
                  // tout deep-link assistance produit en markdown par un
                  // LLM (cas legacy / fallback) est correctement résolu
                  // par `AssistanceDeepLinkResolver`.
                  onOpenLink: (href) async {
                    await AssistanceDeepLinkResolver.resolve(context, href);
                  },
                  // Espacement vertical entre blocs Markdown pour des
                  // réponses multi-blocs (titres + paragraphes + listes
                  // + citations…), dans l'esprit ChatGPT : aéré sans
                  // exagérer.
                  blockSpacing: AppSpacing.md,
                ),
              ),
            // Phase 2c.2 — Embeds UI structurés produits par les tools
            // (ex. carte `transaction_detail`). Chaque embed est rendu
            // sous la bulle markdown (ou seul si la bulle est masquée),
            // dans le même alignement gauche. Les types inconnus du
            // client sont ignorés silencieusement.
            for (final emb in msg.embeds) ...[
              if (showLlmBubble) const SizedBox(height: AppSpacing.sm),
              _buildEmbed(emb),
            ],
            // Cognitive Bot v4 — Lot 7 V1.1 (2026-05-05). Footer
            // auto-QCM cliquable annexé sous la bulle texte. Distinct
            // de `_buildChoicesBubble` (qui remplace la bulle).
            // Filtre défensif : si le tour porte un embed self-contained
            // ou un embed avec ses propres CTAs, on saute le footer
            // pour éviter le doublon UI (le serveur applique déjà la
            // règle dans `decide_auto_qcm`, c'est une défense en
            // profondeur côté client).
            if (msg.hasAutoQcm && !_embedsBlockAutoQcmFooter(msg.embeds)) ...[
              const SizedBox(height: AppSpacing.sm),
              AutoQcmFooter(
                payload: msg.autoQcmPayload!,
                onOptionTapped: (opt) => _handleAutoQcmTapped(
                  opt,
                  messageIndex: messageIndex,
                ),
                selectedOptionId: msg.selectedAutoQcmOptionId,
                maxBubbleWidth: MediaQuery.sizeOf(context).width * 0.92,
              ),
            ],
            const SizedBox(height: AppSpacing.xs),
            // Actions hors module (copier / pouce haut / pouce bas) +
            // heure à droite. Discrètes, sous la bulle, esprit ChatGPT.
            _buildResponseActions(msg),
          ],
        ),
      ),
    );
  }

  /// Phase 2c.4 — un embed est dit « self-contained » s'il porte à
  /// lui seul l'intégralité du message (récap + données + actions),
  /// auquel cas la bulle texte LLM au-dessus est masquée pour éviter
  /// le doublon. Aujourd'hui : `transaction_detail`. Les futurs
  /// embeds auto-suffisants pourront être ajoutés ici.
  static bool _embedIsSelfContained(AssistanceEmbed emb) {
    return emb.type == 'transaction_detail' ||
        emb.type == 'portfolio_allocation_donut';
  }

  /// Décide si la bulle texte LLM doit être masquée au profit de
  /// l'embed seul. Règle :
  ///   1. Si un embed self-contained porte un `summary` non-vide
  ///      (composé serveur), il dit déjà tout ce qu'il faut — on
  ///      masque la bulle texte **sans condition de longueur**, même
  ///      si le LLM s'est répandu en intro malgré la consigne.
  ///   2. Sinon (pas de summary serveur), on retombe sur l'heuristique
  ///      « contenu trivial » : une intro courte (< 60 chars hors
  ///      ponctuation markdown) ne porte pas d'info essentielle.
  static bool _shouldHideLlmBubbleForEmbeds(_ChatMessage msg) {
    for (final emb in msg.embeds) {
      if (!_embedIsSelfContained(emb)) continue;
      if (emb.summary != null) return true;
      if (_isTrivialContent(msg.content)) return true;
    }
    return false;
  }

  /// Détermine si le contenu LLM est « trivial » au point qu'on
  /// peut s'en passer visuellement quand la carte est self-contained.
  /// Heuristique simple : strip whitespace + balises markdown très
  /// courantes ; si le résidu fait moins de 60 caractères, on
  /// considère qu'il s'agit d'une intro / formule de politesse non
  /// porteuse d'info essentielle.
  static bool _isTrivialContent(String raw) {
    final stripped = raw
        .replaceAll(RegExp(r'[#>*_`\-]'), ' ')
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim();
    return stripped.length < 60;
  }

  /// Phase 2c.2 — Dispatcher des embeds UI selon `embed.type`. Un type
  /// inconnu côté client est ignoré silencieusement (rétro-compat :
  /// le serveur peut introduire de nouveaux types sans bumper les
  /// clients existants).
  Widget _buildEmbed(AssistanceEmbed emb) {
    switch (emb.type) {
      case 'transaction_detail':
        final txId = emb.transactionId;
        if (txId == null) return const SizedBox.shrink();
        return TransactionDetailEmbed(
          transactionId: txId,
          actions: emb.actions,
          summary: emb.summary,
        );
      case 'portfolio_allocation_donut':
        return PortfolioAllocationDonutEmbed(
          slices: emb.allocationSlices,
          summary: emb.summary,
          currency: emb.currency ?? 'EUR',
          totalValue: emb.totalValue,
        );
      case 'instrument_detail_card':
        // Phase 2c.6 — carte instrument complémentaire d'un texte LLM
        // (cf. `show_instrument_card`). Jamais self-contained : le LLM
        // peut écrire son explication contextuelle au-dessus de la
        // carte, qui se contente d'afficher les chiffres factuels.
        final symbol = emb.instrumentSymbol;
        final price = emb.instrumentPrice;
        if (symbol == null || price == null) {
          return const SizedBox.shrink();
        }
        return InstrumentDetailCardEmbed(
          symbol: symbol,
          name: emb.instrumentName ?? symbol,
          currency: emb.currency ?? 'EUR',
          price: price,
          actions: emb.actions,
          logoUrl: emb.instrumentLogoUrl,
          change24hAbs: emb.instrumentChange24hAbs,
          change24hPct: emb.instrumentChange24hPct,
          sparkline: emb.instrumentSparkline24h,
        );
      case 'featured_articles_list':
        // Phase 2c.7 — liste d'articles « à la une » poussée par
        // `show_featured_articles`. Toujours complémentaire (LLM
        // rédige sa synthèse au-dessus). Tap article → deep-link
        // `open_article` → `ArticleDetailScreen(slug:)`.
        final items = emb.articleItems;
        if (items.isEmpty) return const SizedBox.shrink();
        return FeaturedArticlesListEmbed(
          title: emb.blockTitle ?? 'À la une',
          items: items,
        );
      case 'top_movers_crypto':
        // Phase 2c.7 — top movers crypto poussé par
        // `show_top_movers`. Toujours complémentaire (LLM commente
        // la dynamique au-dessus). Tap ligne → deep-link
        // `view_instrument` → `crypto_detail_screen`.
        final movers = emb.topMoverItems;
        if (movers.isEmpty) return const SizedBox.shrink();
        return TopMoversCryptoEmbed(
          title: emb.blockTitle ?? 'Top movers',
          items: movers,
          direction: emb.topMoversDirection ?? 'gainers',
        );
      case 'crypto_bundles_card':
        // Phase 2 wiki — slider Crypto Bundles poussé par
        // `show_crypto_bundles` (agent `product`). Réplique chat du
        // widget `CryptoBundlesWidget` de la page markets. Le LLM
        // peut écrire un texte d'introduction au-dessus.
        // Tap card → deep-link `view_bundle_detail` →
        // `ProductPreviewScreen`. Bouton « Investir » → deep-link
        // `invest_bundle` → `BundleInvestFlowController.start`.
        return CryptoBundlesCardEmbed(
          bundles: emb.cryptoBundleItems,
          title: emb.blockTitle,
        );
      case 'bundle_detail_card':
        // Phase 2 wiki v1.4 — fiche détaillée d'UN bundle poussée par
        // `show_bundle_detail` (agent `product`). Réplique chat de la
        // partie haute de `BundleInstrumentDetailHero` (page détail
        // bundle) : tag « Crypto Bundle » + avatars allocations + chart
        // de performance bord-à-bord + CTAs Voir/Investir.
        final bundle = emb.singleBundleItem;
        if (bundle == null) {
          return const SizedBox.shrink();
        }
        return BundleDetailCardEmbed(bundle: bundle);
      default:
        return const SizedBox.shrink();
    }
  }

  /// Multi-agents Phase 1 (cf. docs/arquantix/MULTI_AGENTS.md § 1.2).
  /// Petit badge discret au-dessus de la bulle assistant qui indique
  /// quel agent a répondu, **sauf pour le `default`** (pas de badge
  /// pour rester sobre sur les conversations généralistes) et **sauf
  /// pour le `router`** (un QCM a son propre traitement visuel via
  /// [_buildChoicesBubble]).
  Widget? _buildAgentBadge(String? agentUsed) {
    if (agentUsed == null || agentUsed.isEmpty) return null;
    if (agentUsed == 'default' || agentUsed == 'router') return null;

    final config = _agentBadgeConfig(agentUsed);
    return Padding(
      padding: const EdgeInsets.only(left: 4, top: 2),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              color: config.color,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: AppSpacing.xs),
          Text(
            config.label,
            style: AppTypography.meta.copyWith(
              color: config.color,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  _AgentBadgeConfig _agentBadgeConfig(String agentId) {
    switch (agentId) {
      case 'compliance':
        return const _AgentBadgeConfig(
          label: 'Assistance compte',
          color: AppColors.semanticInfo,
        );
      case 'advisor':
        return const _AgentBadgeConfig(
          label: 'Conseil placement',
          color: AppColors.indigo,
        );
      case 'product':
        return const _AgentBadgeConfig(
          label: 'Produits Vancelian',
          color: AppColors.accent,
        );
      case 'market':
        return const _AgentBadgeConfig(
          label: 'Veille marché',
          color: AppColors.semanticWarning,
        );
      default:
        return _AgentBadgeConfig(
          label: agentId,
          color: AppColors.textMuted,
        );
    }
  }

  /// Bulle « QCM » (`message_type='choices'`) — affiche le `prompt` du
  /// router puis une liste de boutons. Une fois qu'une option a été
  /// cliquée (`msg.selectedChoiceId != null`), le module passe en mode
  /// **consommé** : l'option choisie est mise en avant (contour noir),
  /// les autres sont atténuées en gris, et plus rien n'est cliquable
  /// (D.1.4.7 — anti double-tap + lecture limpide de l'historique).
  /// Cf. docs/arquantix/MULTI_AGENTS.md § 1.9.
  Widget _buildChoicesBubble(_ChatMessage msg, {required int messageIndex}) {
    final payload = msg.choicesPayload;
    if (payload == null) {
      return const SizedBox.shrink();
    }

    final selectedId = msg.selectedChoiceId;
    final isConsumed = selectedId != null;

    return Align(
      alignment: Alignment.centerLeft,
      child: ConstrainedBox(
        constraints:
            BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.92),
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.lg,
            vertical: AppSpacing.md,
          ),
          decoration: const BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.only(
              topLeft: Radius.zero,
              topRight: Radius.circular(AppRadius.bubble),
              bottomLeft: Radius.circular(AppRadius.bubble),
              bottomRight: Radius.circular(AppRadius.bubble),
            ),
            boxShadow: AppShadow.defaultShadowList,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              // 1ʳᵉ ligne du `content` = le `prompt` (cf. service.py
              // qui sérialise « prompt\n1. opt1\n2. opt2 » dans
              // `content` comme fallback texte). On s'en sert ici en
              // priorité — sinon fallback générique.
              Text(
                _extractChoicesPrompt(msg.content),
                style: AppTypography.paragraph,
              ),
              const SizedBox(height: AppSpacing.md),
              for (final option in payload.options)
                Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.xs),
                  child: _buildChoiceButton(
                    option,
                    messageIndex: messageIndex,
                    isConsumed: isConsumed,
                    isSelected: isConsumed && option.id == selectedId,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  /// Extrait le prompt (1ʳᵉ ligne avant les options numérotées) du
  /// `content` fallback texte d'un message `choices`. Si l'analyse
  /// échoue, retourne un prompt générique.
  String _extractChoicesPrompt(String content) {
    final trimmed = content.trim();
    if (trimmed.isEmpty) {
      return 'Pour mieux te répondre, peux-tu préciser ta question ?';
    }
    // Le serveur sérialise « prompt\n1. opt1\n2. opt2\n... » : on prend
    // la 1ʳᵉ ligne, ou tout si pas de retour à la ligne.
    final firstNewline = trimmed.indexOf('\n');
    if (firstNewline < 0) return trimmed;
    return trimmed.substring(0, firstNewline).trim();
  }

  /// Bouton d'une option dans un QCM. Trois états visuels exclusifs,
  /// tous construits **uniquement avec des tokens du DS** (pas de
  /// couleur ad hoc) :
  ///
  /// 1. **`isConsumed == false` — état idle** : style historique,
  ///    indigo pour les options agent, gris clair pour le freeform.
  ///    Cliquable.
  ///
  /// 2. **`isSelected == true` — option choisie après validation** :
  ///    fond transparent, contour `AppColors.textPrimary` (noir),
  ///    texte `AppColors.textPrimary` en `w600`, icône check noire.
  ///    Non cliquable (le QCM est consommé).
  ///
  /// 3. **`isConsumed == true && isSelected == false` — autre option
  ///    non choisie** : fond transparent, contour
  ///    `AppColors.textMuted` (gris clair), texte `AppColors.textMuted`
  ///    en `w400`, icône estompée. Non cliquable. Reste visible pour
  ///    que l'utilisateur garde la trace des alternatives qu'il aurait
  ///    pu choisir, mais visuellement clairement « hors jeu ».
  Widget _buildChoiceButton(
    AssistanceChoiceOption option, {
    required int messageIndex,
    required bool isConsumed,
    required bool isSelected,
  }) {
    final isFreeform = option.isFreeform;

    // Résolution centralisée des couleurs selon l'état. Tous les
    // tokens proviennent de `AppColors` (DS).
    final Color borderColor;
    final Color textColor;
    final Color iconColor;
    final FontWeight textWeight;
    final IconData iconData;

    if (isSelected) {
      // État 2 — option choisie.
      borderColor = AppColors.textPrimary;
      textColor = AppColors.textPrimary;
      iconColor = AppColors.textPrimary;
      textWeight = FontWeight.w600;
      iconData = Icons.check_rounded;
    } else if (isConsumed) {
      // État 3 — autre option non choisie (atténuée).
      borderColor = AppColors.textMuted.withValues(alpha: 0.3);
      textColor = AppColors.textMuted;
      iconColor = AppColors.textMuted;
      textWeight = FontWeight.w400;
      iconData =
          isFreeform ? Icons.edit_outlined : Icons.arrow_forward_ios;
    } else if (isFreeform) {
      // État 1a — idle, freeform.
      borderColor = AppColors.textMuted.withValues(alpha: 0.3);
      textColor = AppColors.textMuted;
      iconColor = AppColors.textMuted;
      textWeight = FontWeight.w400;
      iconData = Icons.edit_outlined;
    } else {
      // État 1b — idle, option agent.
      borderColor = AppColors.indigo.withValues(alpha: 0.3);
      textColor = AppColors.indigo;
      iconColor = AppColors.indigo;
      textWeight = FontWeight.w600;
      iconData = Icons.arrow_forward_ios;
    }

    // Background : seul l'état idle agent garde un wash indigo léger.
    // Les états « consommés » (selected ou dimmed) sont sur fond
    // transparent pour souligner qu'ils ne sont plus actionnables.
    final Color backgroundColor;
    if (isConsumed || isFreeform) {
      backgroundColor = AppColors.cardBackground;
    } else {
      backgroundColor = AppColors.indigo.withValues(alpha: 0.06);
    }

    return Material(
      color: backgroundColor,
      borderRadius: BorderRadius.circular(AppRadius.bubble),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.bubble),
        // `onTap == null` → le splash InkWell est désactivé et le
        // bouton n'est plus cliquable (anti double-tap, anti remap
        // d'un ancien QCM dans l'historique).
        onTap: isConsumed
            ? null
            : () => _handleChoiceTapped(option, messageIndex: messageIndex),
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.md,
            vertical: AppSpacing.sm,
          ),
          decoration: BoxDecoration(
            border: Border.all(color: borderColor, width: 1),
            borderRadius: BorderRadius.circular(AppRadius.bubble),
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  option.label,
                  style: AppTypography.paragraph.copyWith(
                    color: textColor,
                    fontWeight: textWeight,
                  ),
                ),
              ),
              const SizedBox(width: AppSpacing.xs),
              Icon(iconData, size: 14, color: iconColor),
            ],
          ),
        ),
      ),
    );
  }

  /// Multi-agents Phase 1 — handler du tap sur une option de QCM.
  ///
  /// Trois branches métier, dans cet ordre de priorité :
  ///
  /// 1. **D.1.4.7** — Option spéciale `_kRetryAfterCancelOptionId` (QCM
  ///    inséré localement après un stop volontaire) → renvoie le
  ///    **texte original mémorisé** dans `_pendingRetryText` comme un
  ///    nouveau tour, sans `agent_hint` (le router doit refaire sa
  ///    passe normale).
  ///
  /// 2. Option `freeform` (« rien de tout ça » ou « non, je reformule »
  ///    après un cancel) → ne renvoie rien, redonne le focus à l'input
  ///    texte. L'utilisateur reformule librement, le router refera sa
  ///    passe normale au prochain envoi.
  ///
  /// 3. Autre option (cas nominal QCM serveur) → envoie un nouveau
  ///    tour avec `agentHint=option.id` et `content=option.label`. Le
  ///    router est court-circuité côté serveur et l'agent ciblé répond
  ///    directement.
  ///
  /// **Quel que soit le branche** : on commence par marquer le QCM
  /// comme consommé (`selectedChoiceId = option.id`) AVANT toute action
  /// métier. Cela bascule visuellement le module dans l'état figé
  /// (option choisie en noir, autres en gris non cliquables) et
  /// constitue une garde forte anti double-tap pour les rebonds tactile
  /// et les ancien QCM cliqués au scroll dans l'historique.
  void _handleChoiceTapped(
    AssistanceChoiceOption option, {
    required int messageIndex,
  }) {
    if (!mounted || _loading) return;

    // ── Garde idempotence + verrou visuel ─────────────────────────
    // Si l'index est invalide (ne devrait pas arriver — `_messages`
    // est append-only et l'index est calculé dans le même build),
    // on s'abstient pour éviter un crash. Si une option a déjà été
    // sélectionnée (`selectedChoiceId != null`), on ignore le tap —
    // anti double-tap fort, doublé du fait que `onTap` est déjà
    // désactivé côté UI mais la garde reste utile en cas de bug
    // futur dans le wiring.
    if (messageIndex < 0 || messageIndex >= _messages.length) return;
    final currentMsg = _messages[messageIndex];
    if (currentMsg.selectedChoiceId != null) return;

    // Verrou visuel : marquer le QCM comme consommé. Le `setState`
    // déclenche un rebuild qui désactive immédiatement les autres
    // boutons et applique le style « selected » sur l'option choisie.
    setState(() {
      _messages[messageIndex] =
          currentMsg.copyWithSelectedChoiceId(option.id);
    });

    // ── Branche 1 — retry après cancel (D.1.4.7) ──────────────────
    if (option.id == _kRetryAfterCancelOptionId) {
      final retryText = _pendingRetryText;
      _pendingRetryText = null;
      if (retryText == null || retryText.trim().isEmpty) {
        // Cas pathologique : le texte a été clear entretemps (race
        // avec un autre handler). On retombe en freeform pour ne pas
        // bloquer l'utilisateur.
        FocusManager.instance.primaryFocus?.unfocus();
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) FocusScope.of(context).requestFocus(_inputFocusNode);
        });
        return;
      }
      // Renvoi du texte original. Pas d'`agentHint` : on veut que le
      // router refasse une passe complète (le 1er essai a été stoppé
      // avant qu'aucune décision ne soit commitée en BDD, donc on
      // repart à zéro proprement).
      _sendMessageWithText(retryText);
      return;
    }

    // ── Branche 2 — freeform (générique ou « Non, je reformule ») ─
    if (option.isFreeform) {
      // L'utilisateur a explicitement abandonné l'idée de relancer →
      // on libère la mémoire du retry pour ne pas le re-proposer.
      _pendingRetryText = null;
      // Focus sur l'input + clear éventuel : laisse l'utilisateur
      // reformuler. Le QCM reste visible dans l'historique en mode
      // « consommé » pour comprendre l'arborescence de la conversation.
      FocusManager.instance.primaryFocus?.unfocus();
      // Ré-ouvre le clavier sur l'input principal après un micro-délai
      // (sinon le tap propage et referme).
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) FocusScope.of(context).requestFocus(_inputFocusNode);
      });
      return;
    }

    // ── Branche 2.5 — Phase 2b : option avec deep_link (CTA navigation)
    // L'agent (ex: compliance.registration) a poussé un bouton type
    // "Reprendre l'inscription" / "Déposer". Le tap déclenche une
    // navigation native via le résolveur, sans relancer le LLM.
    if (option.hasDeepLink) {
      _pendingRetryText = null;
      // Le QCM reste consommé (selectedChoiceId déjà set ci-dessus).
      // On laisse le clavier fermé pendant la navigation.
      FocusManager.instance.primaryFocus?.unfocus();
      AssistanceDeepLinkResolver.resolve(context, option.deepLink!);
      return;
    }

    // ── Branche 3 — cas nominal QCM serveur ───────────────────────
    // Envoi explicite avec agent_hint pour shortcut le router. Phase 2b :
    // priorité à `option.agentHint` si présent (plus auto-documenté que
    // `option.id` qui reste un identifiant local de l'option).
    final hint = option.hasAgentHint ? option.agentHint : option.id;
    _sendMessageWithText(option.label, agentHint: hint);
  }

  /// Cognitive Bot v4 — Lot 7 V1.1 (2026-05-05). Tap sur une option
  /// du footer auto-QCM (cf. [AutoQcmFooter]). Symétrique de
  /// [_handleChoiceTapped] pour le QCM router, mais SANS la branche
  /// retry-after-cancel (irréaliste pour un footer post-réponse) et
  /// SANS la branche freeform (pas de freeform dans un footer auto-QCM
  /// — l'utilisateur peut toujours saisir librement dans l'input
  /// principal qui reste actif).
  void _handleAutoQcmTapped(
    AssistanceChoiceOption option, {
    required int messageIndex,
  }) {
    if (!mounted || _loading) return;
    if (messageIndex < 0 || messageIndex >= _messages.length) return;

    final currentMsg = _messages[messageIndex];
    if (currentMsg.selectedAutoQcmOptionId != null) return;

    setState(() {
      _messages[messageIndex] =
          currentMsg.copyWithSelectedAutoQcmOptionId(option.id);
    });

    // Branche deep-link : un futur listing pourra exposer des liens
    // natifs (« voir détail X »). Aujourd'hui le serveur n'en émet
    // pas via auto-QCM, mais on supporte par défense en profondeur.
    if (option.hasDeepLink) {
      FocusManager.instance.primaryFocus?.unfocus();
      AssistanceDeepLinkResolver.resolve(context, option.deepLink!);
      return;
    }

    // Cas nominal : envoi du label avec `agent_hint`. Le label de
    // l'option est canoniquement le titre court extrait du listing,
    // suffisant pour le routing serveur.
    final hint = option.hasAgentHint ? option.agentHint : option.id;
    _sendMessageWithText(option.label, agentHint: hint);
  }

  /// Lot 7 V1.1 — `true` si l'un des embeds attachés au message a
  /// déjà ses propres CTAs cliquables (slider bundles, fiche bundle,
  /// fiche instrument, transaction). Le serveur applique déjà cette
  /// garde dans `decide_auto_qcm` via `EMBEDS_WITH_BUILTIN_CTAS`,
  /// mais on garde la défense en profondeur côté client pour éviter
  /// un doublon visuel si la décision serveur évolue.
  static bool _embedsBlockAutoQcmFooter(List<AssistanceEmbed> embeds) {
    for (final emb in embeds) {
      switch (emb.type) {
        case 'crypto_bundles_card':
        case 'bundle_detail_card':
        case 'instrument_detail_card':
        case 'transaction_detail':
          return true;
      }
    }
    return false;
  }

  /// Envoie un message en réutilisant la mécanique standard de
  /// [_sendMessage], mais avec un `text` imposé et un `agentHint`
  /// optionnel — utilisé après clic sur un QCM (cf.
  /// [_handleChoiceTapped]).
  void _sendMessageWithText(String text, {String? agentHint}) {
    _controller.text = text;
    _controller.selection = TextSelection.fromPosition(
      TextPosition(offset: _controller.text.length),
    );
    _sendMessage(agentHint: agentHint);
  }

  /// Barre d'actions sous une réponse type ChatGPT : copier la réponse en
  /// Markdown puis notation positive / négative (notation à venir). À
  /// droite, l'heure du message dans la même row pour économiser une
  /// ligne et rester aligné sur le bord droit du module assistant.
  Widget _buildResponseActions(_ChatMessage msg) {
    final content = msg.content;
    return Row(
      children: [
        _ResponseActionButton(
          icon: KalaiIcons.clipboard1,
          tooltip: 'Copier la réponse',
          onTap: () => _copyResponseToClipboard(content),
        ),
        _ResponseActionButton(
          icon: KalaiIcons.thumbsUp,
          tooltip: 'Réponse utile',
          onTap: () => _rateResponse(content, positive: true),
        ),
        _ResponseActionButton(
          icon: KalaiIcons.thumbsDown,
          tooltip: 'Réponse non utile',
          onTap: () => _rateResponse(content, positive: false),
        ),
        const Spacer(),
        Padding(
          padding: const EdgeInsets.only(right: 4),
          child: Text(
            _messageTimeLabel(msg.createdAt),
            style: AppTypography.meta.copyWith(color: AppColors.textMuted),
          ),
        ),
      ],
    );
  }

  /// Copie la réponse complète dans le presse-papier au format Markdown brut
  /// (= contenu original, sans rendu) et affiche un [AppSnackbar] DS au-dessus
  /// de la barre de saisie.
  void _copyResponseToClipboard(String content) {
    Clipboard.setData(ClipboardData(text: content));
    if (!mounted) return;
    final bottomInset = _kInputBarHeight +
        MediaQuery.paddingOf(context).bottom +
        AppSpacing.md;
    ScaffoldMessenger.of(context)
      ..clearSnackBars()
      ..showSnackBar(
        SnackBar(
          elevation: 0,
          backgroundColor: Colors.transparent,
          padding: EdgeInsets.zero,
          behavior: SnackBarBehavior.floating,
          margin: EdgeInsets.fromLTRB(
            AppSpacing.pageEdge,
            0,
            AppSpacing.pageEdge,
            bottomInset,
          ),
          duration: const Duration(seconds: 2),
          content: const AppSnackbar(
            text: 'Réponse copiée',
            variant: AppSnackbarVariant.dark,
          ),
        ),
      );
  }

  /// Notation positive / négative d'une réponse — fonction à brancher
  /// ultérieurement (pas d'appel serveur pour l'instant).
  void _rateResponse(String content, {required bool positive}) {
    // No-op : l'enregistrement de la notation sera ajouté plus tard.
  }

  /// Bulle « en train d'écrire » (typing indicator) façon WhatsApp :
  /// dots animés dans un module blanc identique à la bulle assistant.
  Widget _buildTypingDots({Key? key}) {
    return Padding(
      key: key,
      padding: const EdgeInsets.only(bottom: AppSpacing.lg),
      child: const _TypingBubble(),
    );
  }

  Widget _buildErrorBanner() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.sm),
      color: AppColors.errorBackground,
      child: Text(
        _error!,
        style: AppTypography.meta.copyWith(color: AppColors.errorText),
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }

  static const double _kInputSingleLineHeight = 44;

  Widget _buildInputBar() {
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          padding: const EdgeInsets.fromLTRB(AppSpacing.sm, AppSpacing.sm, AppSpacing.sm, AppSpacing.sm + 8),
          decoration: BoxDecoration(
            // Wash gradient pour adoucir la transition messages → input bar.
            // Sur fond [pageBackground] gris, on évite le pur blanc qui
            // créerait une bande visible : on tire vers le ton de la page.
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                AppColors.pageBackground.withValues(alpha: 0.0),
                AppColors.pageBackground.withValues(alpha: 0.5),
                AppColors.pageBackground.withValues(alpha: 0.85),
              ],
              stops: const [0.0, 0.4, 1.0],
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              _buildLeftActionButton(),
              const SizedBox(width: AppSpacing.sm),
              Expanded(child: _buildInputPill()),
            ],
          ),
        ),
      ),
    );
  }

  /// Bouton à gauche de l'input bar — change selon le state voice :
  ///
  /// - `idle` : bouton "+" classique (modale pièces jointes).
  /// - `recording` : bouton stop ⊠ rond → **stop + inject** (le texte
  ///   transcrit sera placé dans le TextField, l'utilisateur peut
  ///   éditer puis envoyer). C'est la règle métier validée par le
  ///   brief : "si le bouton stop est cliqué alors on injecte le
  ///   texte transcrit dans l'input".
  /// - `transcribing` : bouton stop ⊠ rond → annule la transcription
  ///   (audio jeté, pas d'injection). Cas validé par le brief comme
  ///   échappatoire en cas de transcription longue (Whisper).
  ///
  /// La position et le diamètre restent identiques entre les états
  /// pour ne pas faire sauter l'UI.
  Widget _buildLeftActionButton() {
    switch (_voiceState) {
      case _VoiceInputState.idle:
        return _buildPlusButton();
      case _VoiceInputState.recording:
        return _buildVoiceLeftStopButton(
          onTap: () => unawaited(_stopVoiceAndInject()),
        );
      case _VoiceInputState.transcribing:
        return _buildVoiceLeftStopButton(
          onTap: () => unawaited(_cancelVoiceFlow()),
        );
    }
  }

  /// Bouton "+" : disque blanc cardBackground, diamètre = hauteur d'une
  /// ligne de l'input ([_kInputSingleLineHeight]) pour s'aligner parfaitement
  /// avec la pill quand l'input est replié sur une ligne. Ouvre la modale
  /// pièces jointes.
  Widget _buildPlusButton() {
    return SizedBox(
      width: _kInputSingleLineHeight,
      height: _kInputSingleLineHeight,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => ChatAttachmentModal.show(context),
          borderRadius: BorderRadius.circular(_kInputSingleLineHeight / 2),
          child: Container(
            decoration: const BoxDecoration(
              color: AppColors.cardBackground,
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: const Icon(
              Icons.add,
              size: 24,
              color: AppColors.textPrimary,
            ),
          ),
        ),
      ),
    );
  }

  /// Bouton stop ⊠ rond, à la place du "+" pendant `recording` ou
  /// `transcribing`. Carré sombre dans un disque blanc bordé — même
  /// recette visuelle que les autres boutons d'action de l'input bar
  /// pour cohérence. L'action varie selon l'état (stop+inject vs
  /// cancel) et est passée en paramètre.
  Widget _buildVoiceLeftStopButton({required VoidCallback onTap}) {
    return SizedBox(
      width: _kInputSingleLineHeight,
      height: _kInputSingleLineHeight,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(_kInputSingleLineHeight / 2),
          child: Container(
            decoration: BoxDecoration(
              color: AppColors.cardBackground,
              shape: BoxShape.circle,
              border: Border.all(
                color: AppColors.textPrimary.withValues(alpha: 0.12),
                width: 1,
              ),
            ),
            alignment: Alignment.center,
            child: Container(
              width: 12,
              height: 12,
              decoration: BoxDecoration(
                color: AppColors.textPrimary,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildInputPill() {
    final hasText = _controller.text.trim().isNotEmpty;

    // D.1.4.8 — pendant le voice flow on remplace le TextField par
    // soit la waveform (recording), soit l'indicateur "Transcription…"
    // (transcribing). Le bouton de droite reflète aussi l'état :
    //   - recording   → ✓ (envoie après transcription)
    //   - transcribing → ↑ désactivé (attend la fin)
    final Widget centerWidget;
    switch (_voiceState) {
      case _VoiceInputState.recording:
        centerWidget = _buildVoiceRecordingCenter();
        break;
      case _VoiceInputState.transcribing:
        centerWidget = const Padding(
          padding: EdgeInsets.only(top: 0, bottom: 0),
          child: VoiceTranscribingIndicator(),
        );
        break;
      case _VoiceInputState.idle:
        centerWidget = _buildTextFieldInput();
        break;
    }

    // En mode recording on inverse le fond de la pill (sombre), comme
    // ChatGPT, pour faire ressortir la waveform blanche. En transcribing
    // et idle on garde le cardBackground blanc habituel pour ne pas
    // créer un flash visuel.
    final pillColor = _voiceState == _VoiceInputState.recording
        ? AppColors.textPrimary
        : AppColors.cardBackground;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 180),
      curve: Curves.easeOutCubic,
      constraints: const BoxConstraints(minHeight: _kInputSingleLineHeight),
      decoration: BoxDecoration(
        color: pillColor,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(child: centerWidget),
          Padding(
            padding: const EdgeInsets.only(right: 6, bottom: 6, top: 6),
            child: _buildSendButton(hasContent: hasText),
          ),
        ],
      ),
    );
  }

  /// TextField classique (état `idle`). Extrait pour clarté.
  Widget _buildTextFieldInput() {
    return TextField(
      controller: _controller,
      focusNode: _inputFocusNode,
      decoration: InputDecoration(
        hintText: 'Poser une question',
        hintStyle: AppTypography.paragraph.copyWith(color: AppColors.chatInputHint),
        filled: true,
        fillColor: Colors.transparent,
        isDense: true,
        border: InputBorder.none,
        enabledBorder: InputBorder.none,
        focusedBorder: InputBorder.none,
        contentPadding: const EdgeInsets.fromLTRB(AppSpacing.lg, 11, AppSpacing.sm, 12),
      ),
      style: AppTypography.paragraph,
      maxLines: 4,
      minLines: 1,
      textInputAction: TextInputAction.newline,
      onSubmitted: (_) => _sendMessage(),
      // Tap n'importe où en dehors du champ → on retire le focus pour
      // faire redescendre le clavier (Flutter ne le fait pas par
      // défaut sur iOS/Android, contrairement aux desktops). Ceci
      // capte aussi les taps sur les [SelectableText] des bulles
      // assistant qui consomment habituellement le geste.
      //
      // En complément on appelle `TextInput.hide` côté plateforme :
      // [SelectableText] (rendu par flutter_markdown quand
      // `selectable: true`) appelle `requestKeyboard()` sur son
      // [EditableText] readOnly au tap-up, ce qui réattache une
      // connexion IME et fait remonter brièvement le clavier sur
      // iOS — d'où l'effet "down-then-up". Forcer la fermeture
      // explicitement supprime ce flash.
      onTapOutside: (_) {
        FocusManager.instance.primaryFocus?.unfocus();
        SystemChannels.textInput.invokeMethod<void>('TextInput.hide');
      },
    );
  }

  /// Contenu central de la pill pendant `recording` : la waveform
  /// alimentée par le sound level stream du transcriber. Centrée
  /// verticalement, hauteur = celle d'une ligne d'input pour ne pas
  /// faire bouger les boutons de gauche/droite.
  Widget _buildVoiceRecordingCenter() {
    final transcriber = _voiceTranscriber;
    if (transcriber == null) {
      // Cas pathologique : le state dit recording mais le transcriber
      // n'existe pas. On affiche un placeholder neutre.
      return const SizedBox(height: _kInputSingleLineHeight);
    }
    return SizedBox(
      height: _kInputSingleLineHeight,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
          child: VoiceWaveformIndicator(
            soundLevelStream: transcriber.soundLevelStream,
            color: AppColors.cardBackground,
          ),
        ),
      ),
    );
  }

  Widget _buildSendButton({required bool hasContent}) {
    const double size = 32.0;

    // D.1.4.7 + D.1.4.8 — état visuel du bouton droit, par ordre de
    // priorité (mutuellement exclusif) :
    //
    //   A. `_loading` (génération IA en cours)
    //      → carré blanc cliquable dans disque sombre. Cancel génération.
    //   B. `_voiceState == recording`
    //      → flèche blanche dans disque sombre. Stop & send (transcript).
    //   C. `_voiceState == transcribing`
    //      → flèche blanche dans disque gris atténué. Désactivé.
    //   D. `hasContent && !_loading`
    //      → flèche blanche dans disque sombre. Envoi classique.
    //   E. `!hasContent && !_loading && _voiceState == idle`
    //      → MICRO blanc dans disque sombre. Démarre voice flow.
    //
    // Les transitions A/E sont les plus fréquentes ; les autres sont
    // des sous-cas du voice flow.
    final isStopMode = _loading;
    final isVoiceRecording = _voiceState == _VoiceInputState.recording;
    final isVoiceTranscribing = _voiceState == _VoiceInputState.transcribing;
    final isMicMode = !isStopMode && !isVoiceRecording && !isVoiceTranscribing && !hasContent;

    final bool isEnabled;
    final VoidCallback? onTap;
    if (isStopMode) {
      isEnabled = true;
      onTap = _cancelGeneration;
    } else if (isVoiceRecording) {
      isEnabled = true;
      onTap = () => unawaited(_stopVoiceAndSend());
    } else if (isVoiceTranscribing) {
      isEnabled = false;
      onTap = null;
    } else if (hasContent) {
      isEnabled = true;
      onTap = _sendMessage;
    } else if (isMicMode) {
      isEnabled = true;
      onTap = () => unawaited(_startVoiceRecording());
    } else {
      isEnabled = false;
      onTap = null;
    }

    final Color discColor = isEnabled
        ? AppColors.textPrimary
        : AppColors.chatInputHint.withValues(alpha: 0.4);

    // Choix du contenu central, avec key unique pour l'AnimatedSwitcher.
    final Widget innerContent;
    if (isStopMode) {
      innerContent = Container(
        key: const ValueKey<String>('stop'),
        // Carré blanc plein, taille modérée pour lire « stop » sans
        // masquer le disque sombre. Les coins légèrement arrondis
        // (2 px) évitent l'aspect pixel-art tout en restant clairement
        // carré.
        width: 11,
        height: 11,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(2),
        ),
      );
    } else if (isMicMode) {
      innerContent = const Icon(
        Icons.mic_rounded,
        key: ValueKey<String>('mic'),
        // Légèrement plus grand que la flèche (20) pour un meilleur
        // rendu optique du micro dans le disque, sans toucher le bord.
        size: 22,
        color: Colors.white,
      );
    } else {
      innerContent = Icon(
        Icons.arrow_upward_rounded,
        key: const ValueKey<String>('send'),
        size: 20,
        color: isEnabled ? Colors.white : Colors.white70,
      );
    }

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(size / 2),
        child: AnimatedContainer(
          // Petite transition (200 ms) entre les états visuels pour un
          // rendu propre quand le tour démarre/se termine — sinon le
          // basculement icône → carré est trop sec.
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOutCubic,
          width: size,
          height: size,
          decoration: BoxDecoration(
            color: discColor,
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 180),
            transitionBuilder: (child, anim) =>
                FadeTransition(opacity: anim, child: child),
            child: innerContent,
          ),
        ),
      ),
    );
  }
}

/// Typing indicator façon WhatsApp : 3 points qui pulsent en opacité
/// (0.3 ↔ 1.0) avec décalage temporel entre eux. Animation douce
/// (`Curves.easeInOut`, cycle 1.4 s) — pas de scale/rebond pour rester
/// discret et précis. Couleur `AppColors.textMuted` du DS.
class _TypingDotsAnimated extends StatefulWidget {
  const _TypingDotsAnimated();

  @override
  State<_TypingDotsAnimated> createState() => _TypingDotsAnimatedState();
}

class _TypingDotsAnimatedState extends State<_TypingDotsAnimated>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  static const double _dotSize = 7;
  static const double _dotSpacing = 4;
  static const double _minOpacity = 0.3;
  static const double _maxOpacity = 1.0;
  // Décalage temporel entre les dots dans le cycle [0..1].
  static const double _dotDelayStep = 0.2;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: _dotSize,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: List.generate(3, (i) {
          return AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              // `t` ∈ [0..1) après application du décalage du dot.
              final t = (_controller.value + i * _dotDelayStep) % 1.0;
              // Triangle 0 → 1 → 0 sur la durée du cycle.
              final triangle = t < 0.5 ? t * 2 : (1 - t) * 2;
              final eased =
                  Curves.easeInOut.transform(triangle.clamp(0.0, 1.0));
              final opacity = _minOpacity + (_maxOpacity - _minOpacity) * eased;
              return Padding(
                padding: EdgeInsets.only(right: i < 2 ? _dotSpacing : 0),
                child: Opacity(
                  opacity: opacity,
                  child: Container(
                    width: _dotSize,
                    height: _dotSize,
                    decoration: const BoxDecoration(
                      color: AppColors.textMuted,
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
              );
            },
          );
        }),
      ),
    );
  }
}

/// Bulle « en train d'écrire » alignée à gauche, encapsulant les dots
/// animés. Reprend strictement le style des bulles assistant existantes
/// (`AppColors.cardBackground`, `AppShadow.defaultShadowList`,
/// `AppRadius.bubble`, top-left carré) — tokens DS uniquement.
class _TypingBubble extends StatelessWidget {
  const _TypingBubble();

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg,
          vertical: AppSpacing.md,
        ),
        decoration: const BoxDecoration(
          color: AppColors.cardBackground,
          borderRadius: BorderRadius.only(
            topLeft: Radius.zero,
            topRight: Radius.circular(AppRadius.bubble),
            bottomLeft: Radius.circular(AppRadius.bubble),
            bottomRight: Radius.circular(AppRadius.bubble),
          ),
          boxShadow: AppShadow.defaultShadowList,
        ),
        child: const _TypingDotsAnimated(),
      ),
    );
  }
}

/// Séparateur de date centré (style WhatsApp) inséré au-dessus du 1ᵉʳ
/// message d'une nouvelle journée. Pill blanche avec ombre — réutilise
/// strictement les tokens DS (`AppColors.cardBackground`,
/// `AppShadow.defaultShadowList`, `AppRadius.bubble`, `AppTypography.meta`,
/// `AppColors.textMuted`, `AppSpacing.*`) pour rester cohérent avec les
/// modules de la page.
/// Configuration d'affichage d'un badge agent (multi-agents Phase 1, cf.
/// docs/arquantix/MULTI_AGENTS.md § 1.2). Tuple immutable : label
/// utilisateur + couleur design system.
class _AgentBadgeConfig {
  const _AgentBadgeConfig({required this.label, required this.color});
  final String label;
  final Color color;
}

class _DateSeparator extends StatelessWidget {
  const _DateSeparator({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.lg),
      child: Center(
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.md,
            vertical: AppSpacing.xs,
          ),
          decoration: const BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.all(Radius.circular(AppRadius.bubble)),
            boxShadow: AppShadow.defaultShadowList,
          ),
          child: Text(
            label,
            style: AppTypography.meta.copyWith(color: AppColors.textMuted),
          ),
        ),
      ),
    );
  }
}

/// Petit bouton icône type ChatGPT (copier / pouce haut / pouce bas) affiché
/// sous une réponse assistant. Hit area confortable (44x44) avec icône 18px
/// gris clair, pour rester discret et accessible.
class _ResponseActionButton extends StatelessWidget {
  const _ResponseActionButton({
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });

  final String icon;
  final String tooltip;
  final VoidCallback onTap;

  static const double _iconSize = 18;
  static const double _hitSize = 36;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: _hitSize,
      height: _hitSize,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(_hitSize / 2),
          child: Center(
            child: KalaiIcon(
              icon,
              size: _iconSize,
              color: AppColors.textSecondary,
              semanticLabel: tooltip,
            ),
          ),
        ),
      ),
    );
  }
}
