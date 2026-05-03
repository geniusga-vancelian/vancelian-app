import 'dart:async';

import 'dart:async';

import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../data/assistance_conversation_storage.dart';
import '../../data/chat_api.dart';
import 'search_screen.dart';

/// Page « Mes conversations » (MVP D.1.4).
///
/// Liste les conversations passées et actives du client. Deux modes d'usage :
///
/// 1. **Picker** (défaut, [standalone] = `false`) : utilisée par
///    `SearchScreen` via le bouton historique de la navbar. Le tap sur une
///    carte fait `pop(conversationId)` et le caller restaure l'historique.
///
/// 2. **Page autonome** ([standalone] = `true`) : entrée directe depuis
///    `Profile › Support › Assistance de compte sur mesure` (D.1.4.3). Le tap
///    push la `SearchScreen` avec la conversation chargée. Une action « + »
///    en navbar et un CTA dans l'empty-state permettent de démarrer une
///    nouvelle conversation. Au retour de la `SearchScreen`, la liste est
///    rafraîchie pour effacer la pastille « non lu » de la conversation
///    consultée.
///
/// Architecture identique à `HelpCenterScreen` (charte du projet) :
/// - Shell `PageSimpleNavBarTopTitlePageContent`
/// - Body `ListCardModule` avec un `ListCardItem` par conversation
/// - Loader / erreur / empty-state cohérents avec le DS
class AssistanceConversationsScreen extends StatefulWidget {
  const AssistanceConversationsScreen({
    super.key,
    this.onBack,
    this.standalone = false,
  });

  final VoidCallback? onBack;

  /// `true` ⇒ page autonome qui pousse `SearchScreen` au tap (cf. doc classe).
  final bool standalone;

  @override
  State<AssistanceConversationsScreen> createState() =>
      _AssistanceConversationsScreenState();
}

class _AssistanceConversationsScreenState
    extends State<AssistanceConversationsScreen>
    with WidgetsBindingObserver {
  bool _loading = true;
  String? _error;
  List<AssistanceConversationSummary> _conversations = const [];

  // ── Auto-refresh « live » de la liste (D.1.4.7) ────────────────────
  //
  // Tant que la page est ouverte, on relit l'API toutes les 2 s en mode
  // silencieux (sans toucher `_loading` ni `_error`) pour détecter :
  //   - l'arrivée d'une réponse assistant (transition pastille grise →
  //     indigo, doit être bien visible — d'où l'intervalle court),
  //   - la mise à jour de l'heure relative,
  //   - une lecture explicite faite depuis un autre device,
  //   - une nouvelle conversation créée hors de cet écran.
  //
  // 2 s = 30 req/min/client max ⇒ pile sous le rate-limit serveur. Le
  // payload est petit et la requête est cheap (pas de jointure msg).
  //
  // Complète :
  //   - le reload `_load()` au mount + au pop d'un push,
  //   - le reload sur retour foreground via `WidgetsBindingObserver`.
  Timer? _refreshTimer;
  static const Duration _refreshInterval = Duration(seconds: 2);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _load();
    _startAutoRefresh();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _refreshTimer?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && mounted) {
      // Retour foreground : refresh immédiat puis on relance le timer
      // (qui peut avoir glissé pendant la pause).
      unawaited(_silentReload());
      _startAutoRefresh();
    } else if (state == AppLifecycleState.paused) {
      _refreshTimer?.cancel();
    }
  }

  void _startAutoRefresh() {
    _refreshTimer?.cancel();
    _refreshTimer = Timer.periodic(_refreshInterval, (_) {
      if (!mounted) return;
      // Pas de refresh pendant un load explicite (évite les flashes).
      if (_loading) return;
      unawaited(_silentReload());
    });
  }

  /// Reload « invisible » : ne touche pas `_loading` ni `_error`. Ne
  /// repaint que si la liste a effectivement changé pour éviter les
  /// rebuilds inutiles.
  Future<void> _silentReload() async {
    try {
      final list = await fetchAssistanceConversations();
      if (!mounted) return;
      if (_areListsEqual(list, _conversations)) return;
      setState(() => _conversations = list);
    } catch (_) {
      // Silencieux : un échec de refresh n'a aucune incidence visible.
    }
  }

  /// Compare deux listes de conversations sur les champs qui peuvent
  /// changer entre deux ticks (ordre, états pastille, lastMessageAt, title).
  bool _areListsEqual(
    List<AssistanceConversationSummary> a,
    List<AssistanceConversationSummary> b,
  ) {
    if (a.length != b.length) return false;
    for (int i = 0; i < a.length; i++) {
      final x = a[i];
      final y = b[i];
      if (x.id != y.id ||
          x.awaitingResponse != y.awaitingResponse ||
          x.unreadResponse != y.unreadResponse ||
          x.title != y.title ||
          x.status != y.status ||
          x.lastMessageAt != y.lastMessageAt) {
        return false;
      }
    }
    return true;
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final list = await fetchAssistanceConversations();
      if (!mounted) return;
      setState(() {
        _conversations = list;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e is ChatApiException ? e.message : e.toString();
      });
    }
  }

  /// Tap sur une conversation dans la liste.
  ///
  /// - **Mode picker** (défaut) : on `pop(conversationId)` ; le caller
  ///   (`SearchScreen`) restaure l'historique au retour.
  /// - **Mode standalone** (depuis Profile) : on push `SearchScreen` qui
  ///   restaurera l'historique via le storage. On rafraîchit la liste au
  ///   retour pour resynchroniser (sortDate notamment).
  ///
  /// Définition « lu » (D.1.4.2 — règle métier mise à jour) : dès que
  /// l'utilisateur ouvre la conversation, on la considère comme lue
  /// (peu importe qu'il ait fait défiler tout le contenu ou non). On
  /// signale donc immédiatement la lecture au serveur (fire-and-forget,
  /// idempotent) et on met à jour optimistiquement l'état local pour
  /// faire disparaître la pastille indigo sans attendre le retour du
  /// serveur ni le prochain `_load()`.
  Future<void> _selectConversation(AssistanceConversationSummary conv) async {
    // Marquer comme lu dès qu'on a une *réponse* à signaler (pastille
    // indigo). Le flag `awaiting_response` (pastille grise) ne se
    // « lit » pas explicitement — il disparaîtra naturellement quand
    // l'assistant aura commité côté serveur.
    if (conv.unreadResponse) {
      unawaited(markAssistanceConversationRead(conv.id));
      setState(() {
        _conversations = [
          for (final c in _conversations)
            c.id == conv.id ? c.copyWith(unreadResponse: false) : c,
        ];
      });
    }
    await AssistanceConversationStorage.instance.write(conv.id);
    if (!mounted) return;
    if (widget.standalone) {
      await Navigator.of(context).push<void>(
        MaterialPageRoute(builder: (_) => const SearchScreen()),
      );
      if (!mounted) return;
      await _load();
      return;
    }
    Navigator.of(context).pop(conv.id);
  }

  /// Mode standalone : lance une nouvelle conversation depuis la liste.
  ///
  /// Efface l'éventuel `conversation_id` du storage avant de pousser le
  /// `SearchScreen` ; au retour, la liste est rafraîchie (la nouvelle
  /// conversation y apparaît si l'utilisateur a échangé au moins un tour).
  Future<void> _startNewConversationFromList() async {
    await AssistanceConversationStorage.instance.clear();
    if (!mounted) return;
    await Navigator.of(context).push<void>(
      MaterialPageRoute(builder: (_) => const SearchScreen()),
    );
    if (!mounted) return;
    await _load();
  }

  /// Date relative à l'utilisateur (Aujourd'hui · 14:32, Hier, il y a 3j…),
  /// dans l'esprit ChatGPT.
  String _relativeDate(DateTime date) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final d = DateTime(date.year, date.month, date.day);
    final diffDays = today.difference(d).inDays;

    String hhmm() {
      final h = date.hour.toString().padLeft(2, '0');
      final m = date.minute.toString().padLeft(2, '0');
      return '$h:$m';
    }

    if (diffDays == 0) return "Aujourd'hui · ${hhmm()}";
    if (diffDays == 1) return 'Hier · ${hhmm()}';
    if (diffDays < 7) return 'Il y a ${diffDays}j';
    if (diffDays < 30) {
      final weeks = (diffDays / 7).floor();
      return weeks == 1 ? 'Il y a 1 sem' : 'Il y a $weeks sem';
    }
    if (diffDays < 365) {
      final months = (diffDays / 30).floor();
      return months == 1 ? 'Il y a 1 mois' : 'Il y a $months mois';
    }
    final years = (diffDays / 365).floor();
    return years == 1 ? 'Il y a 1 an' : 'Il y a $years ans';
  }

  /// Description de la carte : date relative, suivie du marqueur « Fermée »
  /// quand la conversation est close (cf. D.1.5 à venir).
  String _description(AssistanceConversationSummary conv) {
    final rel = _relativeDate(conv.sortDate);
    if (conv.status == 'closed') return '$rel · Fermée';
    return rel;
  }

  /// Titre de la carte : `title` côté serveur (auto = 6 premiers mots du
  /// 1er message), fallback explicite si jamais le serveur renvoie `null`.
  String _title(AssistanceConversationSummary conv) {
    final t = conv.title?.trim();
    if (t == null || t.isEmpty) return 'Conversation';
    return t;
  }

  @override
  Widget build(BuildContext context) {
    return PageSimpleNavBarTopTitlePageContent(
      pageTitle: 'Mes conversations',
      onBackTap: widget.onBack,
      onRefresh: _load,
      navBarActions: widget.standalone
          ? [
              AppTopNavBarAction(
                icon: Icons.edit_outlined,
                onPressed: _startNewConversationFromList,
              ),
            ]
          : const [],
      content: [
        _buildBody(),
      ],
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const SizedBox(
        height: 220,
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (_error != null) {
      return _buildError(_error!);
    }
    if (_conversations.isEmpty) {
      return _buildEmpty();
    }
    // Une carte blanche par conversation (UX « bulle de conversation »).
    // Chaque conversation est un `ListCard` autonome séparé du suivant par
    // un gap de 8px (`AppSpacing.sm`) plutôt qu'agrégées dans un même
    // `ListCardModule`.
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (int i = 0; i < _conversations.length; i++) ...[
          _buildConversationCard(_conversations[i]),
          if (i < _conversations.length - 1)
            const SizedBox(height: AppSpacing.sm),
        ],
      ],
    );
  }

  Widget _buildConversationCard(AssistanceConversationSummary conv) {
    final iconData = conv.status == 'closed'
        ? Icons.lock_outline_rounded
        : Icons.chat_bubble_outline_rounded;
    // D.1.4.6 — deux états distincts pour la pastille :
    //  - réponse arrivée non lue ⇒ badge indigo + check
    //  - réponse en attente      ⇒ badge gris   + horloge
    // `unreadResponse` prime visuellement sur `awaitingResponse` (cas où
    // une nouvelle question est posée alors qu'une vieille réponse n'a
    // pas encore été ouverte : on signale l'info la plus actionnable).
    final _PastilleVariant? variant = conv.unreadResponse
        ? _PastilleVariant.unreadResponse
        : (conv.awaitingResponse ? _PastilleVariant.awaitingResponse : null);
    return ListCard(
      icon: variant == null ? iconData : null,
      leadingWidget: variant == null
          ? null
          : _UnreadAvatar(icon: iconData, variant: variant),
      title: _title(conv),
      description: _description(conv),
      showChevron: true,
      onTap: () => _selectConversation(conv),
    );
  }

  Widget _buildEmpty() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xxl * 2),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.chat_bubble_outline_rounded,
            size: 48,
            color: AppColors.textSecondary.withValues(alpha: 0.6),
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            'Aucune conversation',
            style: AppTypography.itemPrimary.copyWith(
              color: AppColors.textPrimary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            'Vos discussions avec l\'assistance apparaîtront ici.',
            style: AppTypography.paragraph.copyWith(
              color: AppColors.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
          if (widget.standalone) ...[
            const SizedBox(height: AppSpacing.lg),
            AppPrimaryButton(
              label: 'Démarrer une conversation',
              onPressed: _startNewConversationFromList,
              shrinkWrap: true,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildError(String msg) {
    return SizedBox(
      height: 220,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
          child: Text(
            msg,
            style: AppTypography.bodyMedium.copyWith(color: AppColors.errorText),
            textAlign: TextAlign.center,
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// _UnreadAvatar — avatar 36×36 + badge top-right (D.1.4.2 + D.1.4.6)
// ─────────────────────────────────────────────────────────────────────────────
//
// Réplique du rendu d'avatar par défaut de `ListCardItem` (cf. list_card.dart :
// cercle 36×36, fond #E5E5EA, icône 20px #8E8E93), avec un badge superposé
// reprenant exactement le concept de `TransactionStatusBadge`
// (cf. transaction_list_card.dart) : cercle 20×20, bordure blanche 2px,
// icône 12px à l'intérieur. Différences :
//   - position en miroir top-right (vs bottom-right pour les transactions),
//   - couleur dépendante de l'état (`_PastilleVariant`).
//
// Deux variantes (D.1.4.6) :
//   - `awaitingResponse` : badge gris #AEAEB2 + icône `KalaiIcons.clock`,
//     aligné sur `TransactionBadgeStatus.pending` du DS.
//   - `unreadResponse`   : badge indigo (couleur de marque) + icône
//     `KalaiIcons.check`, équivalent fonctionnel de
//     `TransactionBadgeStatus.completed` (« réponse prête à lire »).

enum _PastilleVariant { awaitingResponse, unreadResponse }

class _UnreadAvatar extends StatelessWidget {
  const _UnreadAvatar({required this.icon, required this.variant});

  final IconData icon;
  final _PastilleVariant variant;

  static const double _avatarSize = 36;
  static const double _avatarIconSize = 20;
  static const double _badgeSize = 20;
  static const double _badgeBorder = 2;
  static const double _badgeIconSize = 12;

  @override
  Widget build(BuildContext context) {
    final Color badgeColor;
    final String badgeIcon;
    switch (variant) {
      case _PastilleVariant.awaitingResponse:
        badgeColor = const Color(0xFFAEAEB2);
        badgeIcon = KalaiIcons.clock;
      case _PastilleVariant.unreadResponse:
        badgeColor = AppColors.indigo;
        badgeIcon = KalaiIcons.check;
    }

    return SizedBox(
      width: _avatarSize,
      height: _avatarSize,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Container(
            width: _avatarSize,
            height: _avatarSize,
            decoration: const BoxDecoration(
              color: Color(0xFFE5E5EA),
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Icon(
              icon,
              size: _avatarIconSize,
              color: const Color(0xFF8E8E93),
            ),
          ),
          Positioned(
            top: -4,
            right: -6,
            child: Container(
              width: _badgeSize,
              height: _badgeSize,
              decoration: BoxDecoration(
                color: badgeColor,
                shape: BoxShape.circle,
                border: Border.all(
                  color: AppColors.white,
                  width: _badgeBorder,
                ),
              ),
              child: Center(
                child: KalaiIcon(
                  badgeIcon,
                  size: _badgeIconSize,
                  color: AppColors.white,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
