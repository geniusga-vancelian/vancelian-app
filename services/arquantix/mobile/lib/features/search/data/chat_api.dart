import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';

/// Réponse de l'API assistance : un tour assistant + identifiants conversation/message.
class ChatTurnResponse {
  const ChatTurnResponse({
    required this.conversationId,
    required this.messageId,
    required this.content,
    this.agentUsed,
  });

  final String conversationId;
  final String messageId;
  final String content;

  /// Multi-agents Phase 1 — agent qui a produit la réponse, ou null
  /// (compat. legacy / message user). Sert au badge UI.
  final String? agentUsed;

  factory ChatTurnResponse.fromJson(Map<String, dynamic> json) {
    return ChatTurnResponse(
      conversationId: (json['conversation_id'] as String?) ?? '',
      messageId: (json['message_id'] as String?) ?? '',
      content: (json['content'] as String?) ?? '',
      agentUsed: json['agent_used'] as String?,
    );
  }
}

/// Une option d'un QCM `choices` poussé par le router multi-agents
/// quand son intention est ambiguë (cf. docs/arquantix/MULTI_AGENTS.md § 1.9).
///
/// Phase 2b — extension :
///   - [agentHint] (optionnel) : si présent, le tap relance le LLM avec
///     ce hint (ex: "product"). Préféré à l'ancien fallback `id`.
///   - [deepLink] (optionnel) : si présent, le tap déclenche une
///     navigation Flutter via `AssistanceDeepLinkResolver` au lieu
///     d'un nouveau message. Mutuellement exclusif avec [agentHint] —
///     le backend valide cette contrainte côté `ask_user_question`.
class AssistanceChoiceOption {
  const AssistanceChoiceOption({
    required this.id,
    required this.label,
    this.agentHint,
    this.deepLink,
  });

  /// `agent_id` à renvoyer comme `agent_hint` au prochain tour, sauf
  /// valeur spéciale `'freeform'` qui veut dire « rien de tout ça ».
  final String id;
  final String label;

  /// Phase 2b. Si non-null, le tap envoie un nouveau tour avec cet
  /// `agent_hint` (priorité sur [id] qui peut rester un identifiant
  /// d'option locale).
  final String? agentHint;

  /// Phase 2b. Si non-null, le tap déclenche une navigation native
  /// résolue par `AssistanceDeepLinkResolver`.
  final String? deepLink;

  bool get isFreeform => id == 'freeform';
  bool get hasDeepLink => deepLink != null && deepLink!.isNotEmpty;
  bool get hasAgentHint => agentHint != null && agentHint!.isNotEmpty;

  factory AssistanceChoiceOption.fromJson(Map<String, dynamic> json) {
    return AssistanceChoiceOption(
      id: (json['id'] as String?) ?? '',
      label: (json['label'] as String?) ?? '',
      agentHint: (json['agent_hint'] as String?),
      deepLink: (json['deep_link'] as String?),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'label': label,
        if (agentHint != null) 'agent_hint': agentHint,
        if (deepLink != null) 'deep_link': deepLink,
      };
}

/// Payload d'un message `message_type='choices'` (QCM router) côté DB.
class AssistanceChoicesPayload {
  const AssistanceChoicesPayload({
    required this.options,
    required this.allowFreeform,
  });

  final List<AssistanceChoiceOption> options;
  final bool allowFreeform;

  factory AssistanceChoicesPayload.fromJson(Map<String, dynamic> json) {
    final raw = (json['options'] as List?) ?? const [];
    return AssistanceChoicesPayload(
      options: raw
          .whereType<Map<String, dynamic>>()
          .map(AssistanceChoiceOption.fromJson)
          .toList(),
      allowFreeform: (json['allow_freeform'] as bool?) ?? true,
    );
  }
}

/// Phase 2c.2 — Bloc UI structuré attaché à un message assistant.
///
/// Le serveur produit ces blocs via les tools (ex.
/// `read_transaction_detail`) et les agrège dans
/// `message_payload.embeds[]`. Le client les rend via des widgets
/// dédiés au lieu de dépendre d'un markdown formaté par le LLM
/// (cela évite hallucinations + tipping-off + permet d'afficher
/// les vraies données chargées via API authentifiée).
///
/// Chaque embed a un [type] (string ouvert) qui détermine quel
/// widget Flutter le rend. Les autres champs sont passés tels
/// quels via [data] (sérialisés depuis le JSON serveur). Cela
/// permet d'ajouter de nouveaux types côté backend sans bumper
/// les clients existants : un client qui ne connaît pas un type
/// l'ignore silencieusement.
///
/// Slice d'allocation portefeuille pour l'embed
/// ``portfolio_allocation_donut`` (Phase 2c.5 Lot 3).
class AssistanceAllocationSlice {
  const AssistanceAllocationSlice({
    required this.key,
    required this.label,
    required this.value,
    required this.percentage,
  });

  /// Identifiant interne stable (`fiat`, `crypto_direct`, `bundles`).
  /// Utilisé pour mapper vers une couleur de marque côté client.
  final String key;

  /// Label FR humanisé (`Cash (EUR)`, `Crypto en direct`, `Bundles`).
  final String label;

  /// Valeur absolue en devise (€ par défaut).
  final double value;

  /// Pourcentage de la slice dans le NAV total (0-100).
  final double percentage;

  factory AssistanceAllocationSlice.fromJson(Map<String, dynamic> json) {
    double parseNum(dynamic v) {
      if (v is num) return v.toDouble();
      if (v is String) return double.tryParse(v) ?? 0;
      return 0;
    }

    return AssistanceAllocationSlice(
      key: (json['key'] as String?) ?? '',
      label: (json['label'] as String?) ?? '',
      value: parseNum(json['value']),
      percentage: parseNum(json['percentage']),
    );
  }
}

/// Types reconnus aujourd'hui :
///  - `transaction_detail` : carte de détail d'une transaction.
///  - `portfolio_allocation_donut` : carte donut chart d'allocation
///    portefeuille (Phase 2c.5 Lot 3).
///  - `instrument_detail_card` : carte instrument (logo + prix + perf
///    24h + mini-sparkline + boutons Acheter/Vendre) — Phase 2c.6.
///    Émise par les agents `product` / `advisor` en complément d'un
///    message texte explicatif sur un actif (Bitcoin, Ether, …).
///  - `featured_articles_list` : liste d'articles « à la une » filtrée
///    par type (NEWS / ANALYSIS / RESEARCH) — Phase 2c.7. Émise par
///    les agents `market` / `advisor` en complément d'une synthèse
///    texte. Chaque ligne ouvre `ArticleDetailScreen` via deep-link
///    `vancelian://app/article/{slug}`.
///  - `top_movers_crypto` : liste des top hausses / baisses / volumes
///    24h — Phase 2c.7. Émise par `market` / `advisor`. Chaque ligne
///    ouvre la fiche instrument via deep-link
///    `vancelian://app/instrument/{id}`.
class AssistanceEmbed {
  const AssistanceEmbed({
    required this.type,
    required this.data,
  });

  /// Discriminateur — détermine le widget Flutter qui rend l'embed.
  final String type;

  /// Données brutes JSON du serveur. Lecture via accesseurs ou
  /// parsing dédié selon [type].
  final Map<String, dynamic> data;

  /// Helper : transaction_id si l'embed en contient un (utilisé par
  /// les types `transaction_detail` et futurs `transaction_*`).
  String? get transactionId {
    final v = data['transaction_id'];
    return v is String && v.isNotEmpty ? v : null;
  }

  /// Helper : récap textuel optionnel (Phase 2c.4).
  ///
  /// Composé par le serveur (ex. tool `read_transaction_detail` →
  /// *« Tu as fait un dépôt par virement bancaire de 45 000 € le
  /// 3 mai 2026. Voici les détails ci-dessous. »*) et inséré au-dessus
  /// du contenu détaillé pour produire **un seul module visuel**
  /// (au lieu de deux bulles : intro LLM + carte).
  String? get summary {
    final v = data['summary'];
    return v is String && v.trim().isNotEmpty ? v : null;
  }

  /// Helper : devise courante (utilisé par les embeds qui exposent
  /// des montants — ``portfolio_allocation_donut``, …).
  String? get currency {
    final v = data['currency'];
    return v is String && v.isNotEmpty ? v : null;
  }

  /// Helper : valeur totale (NAV, etc.) — embeds portfolio.
  double? get totalValue {
    final v = data['total_value'];
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v);
    return null;
  }

  /// Helper : slices d'allocation pour l'embed
  /// ``portfolio_allocation_donut``. Chaque slice contient
  /// ``key`` (interne), ``label`` (FR), ``value`` (€) et
  /// ``percentage`` (0-100).
  List<AssistanceAllocationSlice> get allocationSlices {
    final raw = data['slices'];
    if (raw is! List) return const [];
    return raw
        .whereType<Map<String, dynamic>>()
        .map(AssistanceAllocationSlice.fromJson)
        .where((s) => s.percentage > 0)
        .toList();
  }

  // ──────────────────────────────────────────────────────────────────
  // Helpers `instrument_detail_card` (Phase 2c.6)
  // ──────────────────────────────────────────────────────────────────

  /// Identifiant interne de l'instrument (clé primaire
  /// `market_data_instruments.id`). Utilisé par le resolver de
  /// deep-links pour reconstituer le `CryptoAssetItem` cible du
  /// BuyFlow.
  int? get instrumentId {
    final v = data['instrument_id'];
    if (v is int) return v;
    if (v is num) return v.toInt();
    if (v is String) return int.tryParse(v);
    return null;
  }

  /// Symbol court (ex. `BTC`, `ETH`).
  String? get instrumentSymbol {
    final v = data['symbol'];
    return v is String && v.isNotEmpty ? v : null;
  }

  /// Nom complet (ex. `Bitcoin`).
  String? get instrumentName {
    final v = data['name'];
    return v is String && v.isNotEmpty ? v : null;
  }

  /// URL relatif du logo (préfixé par `/media/...`). Le client doit
  /// préfixer son `Config.baseUrl` pour obtenir un URL absolu.
  String? get instrumentLogoUrl {
    final v = data['logo_url'];
    return v is String && v.isNotEmpty ? v : null;
  }

  /// Prix dans la devise affichée (`currency`). Pour
  /// `instrument_detail_card`, contrairement à `total_value`.
  double? get instrumentPrice {
    final v = data['price'];
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v);
    return null;
  }

  /// Variation absolue sur 24 h dans la devise affichée. Peut être
  /// négative (perte) ou nulle si non calculable.
  double? get instrumentChange24hAbs {
    final v = data['change_24h_abs'];
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v);
    return null;
  }

  /// Variation relative sur 24 h (%). Peut être négative ou nulle.
  double? get instrumentChange24hPct {
    final v = data['change_24h_pct'];
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v);
    return null;
  }

  /// Points de la mini-sparkline sur 24 h (closes des bougies 5 min,
  /// jusqu'à ~288 points). Vide si indisponible.
  List<double> get instrumentSparkline24h {
    final raw = data['sparkline_24h'];
    if (raw is! List) return const [];
    return raw
        .map((e) {
          if (e is num) return e.toDouble();
          if (e is String) return double.tryParse(e) ?? 0;
          return 0.0;
        })
        .where((d) => d > 0)
        .toList(growable: false);
  }

  // ──────────────────────────────────────────────────────────────────
  // Helpers `featured_articles_list` (Phase 2c.7)
  // ──────────────────────────────────────────────────────────────────

  /// Titre composé serveur du bloc (`À la une`, `Analyses`,
  /// `Notes de recherche`, éventuellement suffixé par la query).
  String? get blockTitle {
    final v = data['title'];
    return v is String && v.trim().isNotEmpty ? v.trim() : null;
  }

  /// Items de la liste d'articles. Chaque entrée porte `slug`,
  /// `title`, `cover_url`, `published_at`, `deep_link`.
  List<AssistanceArticleItem> get articleItems {
    final raw = data['items'];
    if (raw is! List) return const [];
    return raw
        .whereType<Map<String, dynamic>>()
        .map(AssistanceArticleItem.fromJson)
        .where((it) => it.title.isNotEmpty)
        .toList();
  }

  // ──────────────────────────────────────────────────────────────────
  // Helpers `top_movers_crypto` (Phase 2c.7)
  // ──────────────────────────────────────────────────────────────────

  /// Items de la liste top movers. Chaque entrée porte `instrument_id`,
  /// `symbol`, `name`, `price`, `change_24h_pct`, `deep_link`, …
  List<AssistanceTopMoverItem> get topMoverItems {
    final raw = data['items'];
    if (raw is! List) return const [];
    return raw
        .whereType<Map<String, dynamic>>()
        .map(AssistanceTopMoverItem.fromJson)
        .where((it) => it.symbol.isNotEmpty)
        .toList();
  }

  /// Direction du tri pour l'embed `top_movers_crypto`
  /// (`gainers`, `losers`, `volume`).
  String? get topMoversDirection {
    final v = data['direction'];
    return v is String && v.isNotEmpty ? v : null;
  }

  /// Helper : liste d'actions whitelisées (chacune est un
  /// [AssistanceChoiceOption] avec deep_link). Présent quand
  /// l'embed embarque ses propres CTAs (ex. carte transaction).
  List<AssistanceChoiceOption> get actions {
    final raw = data['actions'];
    if (raw is! List) return const [];
    return raw
        .whereType<Map<String, dynamic>>()
        .map(
          (e) => AssistanceChoiceOption(
            id: (e['kind'] as String?) ?? '',
            label: (e['label'] as String?) ?? '',
            deepLink: e['deep_link'] as String?,
          ),
        )
        .where((o) => o.label.isNotEmpty && o.hasDeepLink)
        .toList();
  }

  factory AssistanceEmbed.fromJson(Map<String, dynamic> json) {
    return AssistanceEmbed(
      type: (json['type'] as String?) ?? '',
      data: json,
    );
  }
}

/// Slice d'un embed `featured_articles_list` (Phase 2c.7).
///
/// Le serveur compose ces items à partir de la table `articles`
/// (Prisma) : un article publié, son slug, sa cover, son titre, son
/// standfirst, sa date. Le `deepLink` est whitelisté côté serveur via
/// `action_cta_catalog.build_action("open_article", ...)`.
class AssistanceArticleItem {
  const AssistanceArticleItem({
    required this.slug,
    required this.title,
    required this.standfirst,
    required this.coverUrl,
    required this.publishedAt,
    required this.deepLink,
    required this.isFeatured,
  });

  final String slug;
  final String title;
  final String standfirst;
  final String? coverUrl;

  /// ISO-8601 (UTC) tel que renvoyé par le serveur. `null` si l'article
  /// n'a pas de `published_at` (ne devrait pas arriver pour un article
  /// `PUBLISHED`).
  final DateTime? publishedAt;

  /// Deep-link `vancelian://app/article/{slug}` à passer à
  /// `AssistanceDeepLinkResolver`. `null` si non whitelisté côté
  /// serveur (cas anormal — la ligne reste affichée mais non
  /// cliquable).
  final String? deepLink;

  /// Article tagué `isFeatured` côté CMS — peut servir à mettre une
  /// pastille / mise en avant côté UI.
  final bool isFeatured;

  bool get hasDeepLink => deepLink != null && deepLink!.isNotEmpty;

  factory AssistanceArticleItem.fromJson(Map<String, dynamic> json) {
    DateTime? published;
    final raw = json['published_at'];
    if (raw is String && raw.isNotEmpty) {
      published = DateTime.tryParse(raw)?.toLocal();
    }
    return AssistanceArticleItem(
      slug: (json['slug'] as String?) ?? '',
      title: (json['title'] as String?) ?? '',
      standfirst: (json['standfirst'] as String?) ?? '',
      coverUrl: (json['cover_url'] as String?),
      publishedAt: published,
      deepLink: (json['deep_link'] as String?),
      isFeatured: json['is_featured'] == true,
    );
  }
}

/// Item d'un embed `top_movers_crypto` (Phase 2c.7).
class AssistanceTopMoverItem {
  const AssistanceTopMoverItem({
    required this.instrumentId,
    required this.symbol,
    required this.name,
    required this.logoUrl,
    required this.currency,
    required this.price,
    required this.change24hAbs,
    required this.change24hPct,
    required this.volume24h,
    required this.deepLink,
  });

  final int? instrumentId;
  final String symbol;
  final String name;
  final String? logoUrl;
  final String currency;
  final double price;
  final double? change24hAbs;
  final double? change24hPct;
  final double? volume24h;
  final String? deepLink;

  bool get hasDeepLink => deepLink != null && deepLink!.isNotEmpty;

  factory AssistanceTopMoverItem.fromJson(Map<String, dynamic> json) {
    double parseNum(dynamic v) {
      if (v is num) return v.toDouble();
      if (v is String) return double.tryParse(v) ?? 0;
      return 0;
    }

    double? parseOptionalNum(dynamic v) {
      if (v is num) return v.toDouble();
      if (v is String) return double.tryParse(v);
      return null;
    }

    int? parseOptionalInt(dynamic v) {
      if (v is int) return v;
      if (v is num) return v.toInt();
      if (v is String) return int.tryParse(v);
      return null;
    }

    return AssistanceTopMoverItem(
      instrumentId: parseOptionalInt(json['instrument_id']),
      symbol: (json['symbol'] as String?) ?? '',
      name: (json['name'] as String?) ?? '',
      logoUrl: (json['logo_url'] as String?),
      currency: (json['currency'] as String?) ?? 'EUR',
      price: parseNum(json['price']),
      change24hAbs: parseOptionalNum(json['change_24h_abs']),
      change24hPct: parseOptionalNum(json['change_24h_pct']),
      volume24h: parseOptionalNum(json['volume_24h']),
      deepLink: (json['deep_link'] as String?),
    );
  }
}

/// Envoie un tour utilisateur (`content`) à l'API d'assistance authentifiée.
///
/// Le serveur Python résout le `client_id` depuis le bearer JWT, applique le
/// rate-limit, persiste le tour user puis assistant et retourne le contenu
/// Markdown. Si [conversationId] est `null`, une nouvelle conversation est
/// créée avec un titre auto-généré (premiers mots du message).
///
/// Multi-agents Phase 1 ([agentHint]) : si l'utilisateur a cliqué une option
/// d'un QCM précédent (`messageType=='choices'`), passer l'`id` de l'option
/// (= `agent_id`) ici → le router est court-circuité côté serveur. Si
/// `null`, le router classifie normalement.
Future<ChatTurnResponse> sendAssistanceTurn({
  String? conversationId,
  required String content,
  String? agentHint,
}) async {
  final uri = Uri.parse(Config.mobileAssistanceChatTurnUrl);
  final headers = await SessionBearerHttp.jsonHeadersAppScoped(
    uri: uri,
    debugTag: 'assistance_chat_turn',
    withJsonContentType: true,
  );
  final body = jsonEncode({
    if (conversationId != null) 'conversation_id': conversationId,
    'content': content,
    if (agentHint != null) 'agent_hint': agentHint,
  });
  final response = await http.post(uri, headers: headers, body: body);
  if (response.statusCode != 200) {
    final raw = jsonDecode(response.body);
    String message;
    if (raw is Map<String, dynamic>) {
      final detail = raw['detail'];
      if (detail is Map<String, dynamic>) {
        final inner = detail['error'];
        if (inner is Map<String, dynamic>) {
          message = (inner['message'] as String?) ??
              (inner['code'] as String?) ??
              response.body;
        } else {
          message = detail.toString();
        }
      } else {
        message = (raw['error'] as Object?)?.toString() ?? response.body;
      }
    } else {
      message = response.body;
    }
    throw ChatApiException(response.statusCode, message);
  }
  final data = jsonDecode(response.body) as Map<String, dynamic>;
  return ChatTurnResponse.fromJson(data);
}

class ChatApiException implements Exception {
  ChatApiException(this.statusCode, this.message);
  final int statusCode;
  final String message;
  @override
  String toString() => 'ChatApiException($statusCode): $message';
}

/// Un message historique (D.1.6) — utilisé pour rejouer une conversation
/// existante dans l'UI au démarrage du Search Screen.
class AssistanceHistoryMessage {
  const AssistanceHistoryMessage({
    required this.id,
    required this.turnIndex,
    required this.role,
    required this.content,
    required this.createdAt,
    this.agentUsed,
    this.messageType = 'text',
    this.choicesPayload,
    this.embeds = const [],
  });

  final String id;
  final int turnIndex;
  final String role; // 'user' | 'assistant'
  final String content;

  /// Date serveur du message (`ConversationMessageItem.created_at`). Utilisée
  /// côté UI pour afficher l'heure sous chaque bulle et regrouper les
  /// messages par jour (séparateurs « Aujourd'hui » / « Hier » / « DATE »).
  final DateTime createdAt;

  /// Multi-agents Phase 1 (cf. docs/arquantix/MULTI_AGENTS.md § 1.2 et § 4).
  /// Identifiant de l'agent qui a produit le message assistant
  /// (`compliance`, `advisor`, `product`, `market`, `default`, `router`).
  /// `null` pour les messages user et les anciens messages assistant.
  final String? agentUsed;

  /// `'text'` (bulle Markdown classique) ou `'choices'` (QCM cliquable).
  final String messageType;

  /// Payload structuré quand `messageType == 'choices'`. `null` sinon.
  final AssistanceChoicesPayload? choicesPayload;

  /// Phase 2c.2 — Embeds UI structurés (cartes `transaction_detail`,
  /// etc.) attachés au message dans `message_payload.embeds[]`. Vide
  /// par défaut pour les messages legacy / sans bloc structuré.
  /// Compatible avec n'importe quel `messageType` (pas seulement
  /// `'text'`) : un QCM peut aussi porter un embed contextuel à
  /// l'avenir.
  final List<AssistanceEmbed> embeds;

  bool get isChoicesMessage => messageType == 'choices';

  factory AssistanceHistoryMessage.fromJson(Map<String, dynamic> json) {
    AssistanceChoicesPayload? choicesPayload;
    List<AssistanceEmbed> parsedEmbeds = const [];
    final rawPayload = json['message_payload'];
    if (rawPayload is Map<String, dynamic>) {
      // `message_type='choices'` : le payload contient `options` +
      // `allow_freeform`. On le parse uniquement si c'est ce qu'on
      // attend (présence d'`options`).
      if (rawPayload['options'] is List) {
        choicesPayload = AssistanceChoicesPayload.fromJson(rawPayload);
      }
      // Embeds : présent indépendamment du `message_type`.
      final rawEmbeds = rawPayload['embeds'];
      if (rawEmbeds is List) {
        parsedEmbeds = rawEmbeds
            .whereType<Map<String, dynamic>>()
            .map(AssistanceEmbed.fromJson)
            .where((e) => e.type.isNotEmpty)
            .toList();
      }
    }
    return AssistanceHistoryMessage(
      id: (json['id'] as String?) ?? '',
      turnIndex: (json['turn_index'] as num?)?.toInt() ?? 0,
      role: (json['role'] as String?) ?? 'assistant',
      content: (json['content'] as String?) ?? '',
      createdAt: DateTime.tryParse((json['created_at'] as String?) ?? '')
              ?.toLocal() ??
          DateTime.fromMillisecondsSinceEpoch(0),
      agentUsed: json['agent_used'] as String?,
      messageType: (json['message_type'] as String?) ?? 'text',
      choicesPayload: choicesPayload,
      embeds: parsedEmbeds,
    );
  }
}

/// Historique complet retourné par `GET …/conversations/{id}/messages`.
class AssistanceConversationHistory {
  const AssistanceConversationHistory({
    required this.conversationId,
    required this.title,
    required this.status,
    required this.messages,
  });

  final String conversationId;
  final String? title;
  final String status; // 'active' | 'closed'
  final List<AssistanceHistoryMessage> messages;

  factory AssistanceConversationHistory.fromJson(Map<String, dynamic> json) {
    final raw = (json['messages'] as List?) ?? const [];
    return AssistanceConversationHistory(
      conversationId: (json['conversation_id'] as String?) ?? '',
      title: json['title'] as String?,
      status: (json['status'] as String?) ?? 'active',
      messages: raw
          .whereType<Map<String, dynamic>>()
          .map(AssistanceHistoryMessage.fromJson)
          .toList(),
    );
  }
}

/// Résumé d'une conversation pour la page « Mes conversations » (D.1.4).
class AssistanceConversationSummary {
  const AssistanceConversationSummary({
    required this.id,
    required this.title,
    required this.status,
    required this.createdAt,
    required this.lastMessageAt,
    required this.awaitingResponse,
    required this.unreadResponse,
  });

  final String id;
  final String? title;
  final String status; // 'active' | 'closed'
  final DateTime createdAt;
  final DateTime? lastMessageAt;

  /// D.1.4.6 — l'utilisateur a posté un message, l'assistant n'a pas
  /// encore commité sa réponse (stream en cours / échec / offline).
  /// → pastille **grise + horloge** côté UI.
  final bool awaitingResponse;

  /// D.1.4.6 — l'assistant a commité une réponse postérieure à
  /// `last_read_at`. → pastille **indigo + check** côté UI.
  final bool unreadResponse;

  /// Helper legacy (D.1.4.2) : true s'il y a quelque chose à signaler
  /// (l'un ou l'autre des deux états).
  bool get unread => awaitingResponse || unreadResponse;

  /// Date pertinente pour le tri/affichage (priorise [lastMessageAt],
  /// fallback [createdAt] si la conversation n'a pas encore de tour).
  DateTime get sortDate => lastMessageAt ?? createdAt;

  factory AssistanceConversationSummary.fromJson(Map<String, dynamic> json) {
    // Back-compat : si le serveur ne renvoie pas encore les flags
    // séparés, on retombe sur l'ancien `unread` global qu'on traite
    // comme `unreadResponse` (cas le plus fréquent).
    final awaiting = json['awaiting_response'] as bool?;
    final unreadRes = json['unread_response'] as bool?;
    final legacyUnread = json['unread'] as bool?;
    return AssistanceConversationSummary(
      id: (json['id'] as String?) ?? '',
      title: json['title'] as String?,
      status: (json['status'] as String?) ?? 'active',
      createdAt: DateTime.tryParse((json['created_at'] as String?) ?? '')
              ?.toLocal() ??
          DateTime.fromMillisecondsSinceEpoch(0),
      lastMessageAt: json['last_message_at'] is String
          ? DateTime.tryParse(json['last_message_at'] as String)?.toLocal()
          : null,
      awaitingResponse: awaiting ?? false,
      unreadResponse: unreadRes ?? legacyUnread ?? false,
    );
  }

  /// Copie immutable. Utilisé notamment pour la mise à jour optimiste de
  /// l'état « non lu » côté UI au moment où l'utilisateur ouvre la
  /// conversation, sans attendre le `_load()` suivant.
  AssistanceConversationSummary copyWith({
    String? id,
    String? title,
    String? status,
    DateTime? createdAt,
    DateTime? lastMessageAt,
    bool? awaitingResponse,
    bool? unreadResponse,
  }) {
    return AssistanceConversationSummary(
      id: id ?? this.id,
      title: title ?? this.title,
      status: status ?? this.status,
      createdAt: createdAt ?? this.createdAt,
      lastMessageAt: lastMessageAt ?? this.lastMessageAt,
      awaitingResponse: awaitingResponse ?? this.awaitingResponse,
      unreadResponse: unreadResponse ?? this.unreadResponse,
    );
  }
}

/// Liste les conversations du client courant (D.1.4).
///
/// `status` accepte `'active'` ou `'closed'` ; `null` renvoie tout.
/// La réponse serveur est déjà triée par activité décroissante.
Future<List<AssistanceConversationSummary>> fetchAssistanceConversations({
  String? status,
  int? limit,
}) async {
  final uri = Uri.parse(
    Config.mobileAssistanceConversationsUrl(status: status, limit: limit),
  );
  final headers = await SessionBearerHttp.jsonHeadersAppScoped(
    uri: uri,
    debugTag: 'assistance_conversations',
  );
  final response = await http.get(uri, headers: headers);
  if (response.statusCode != 200) {
    throw ChatApiException(response.statusCode, response.body);
  }
  final data = jsonDecode(response.body) as Map<String, dynamic>;
  final raw = (data['conversations'] as List?) ?? const [];
  return raw
      .whereType<Map<String, dynamic>>()
      .map(AssistanceConversationSummary.fromJson)
      .toList();
}

/// Charge l'historique d'une conversation d'assistance (D.1.6).
///
/// - Retourne `null` si le serveur répond `404` (conversation supprimée
///   côté serveur ou ID local devenu obsolète) — l'appelant doit alors
///   nettoyer le storage local.
/// - Lève [ChatApiException] sur les autres erreurs (401, 5xx…).
Future<AssistanceConversationHistory?> fetchAssistanceHistory(
  String conversationId, {
  int? limit,
}) async {
  final uri = Uri.parse(
    Config.mobileAssistanceConversationMessagesUrl(
      conversationId,
      limit: limit,
    ),
  );
  final headers = await SessionBearerHttp.jsonHeadersAppScoped(
    uri: uri,
    debugTag: 'assistance_history',
  );
  final response = await http.get(uri, headers: headers);
  if (response.statusCode == 404) {
    return null;
  }
  if (response.statusCode != 200) {
    throw ChatApiException(response.statusCode, response.body);
  }
  final data = jsonDecode(response.body) as Map<String, dynamic>;
  return AssistanceConversationHistory.fromJson(data);
}

/// Un event SSE applicatif émis par `POST /chat/turn/stream` (D.1.4.5).
///
/// `type` ∈ {`started`, `delta`, `choices`, `done`, `error`} :
/// - `started` : tout début du stream — porte `conversation_id` et
///   `user_message_id`. Permet au client de persister l'ID de
///   conversation **avant même** le 1ᵉʳ token assistant (utile si l'user
///   ferme l'app pendant la génération).
/// - `delta` : porte `content` (chaîne incrémentale). Concaténer ces
///   deltas dans l'ordre reçu reconstitue le message assistant complet.
/// - `choices` : Multi-agents Phase 1 — le router est indécis, il pousse
///   un QCM avec `prompt`, `options` et `allow_freeform` pour que
///   l'utilisateur précise son intention (cf. § 1.9 du doc).
/// - `done` : commit serveur effectué — porte `message_id`, `completed`,
///   et (multi-agents) `agent_used` + `message_type`.
/// - `error` : signal d'erreur (LLM down, conversation_gone…) avec un
///   `message` lisible côté UI.
class AssistanceTurnEvent {
  const AssistanceTurnEvent(this.type, this.data);

  final String type;
  final Map<String, dynamic> data;

  String? get conversationId => data['conversation_id'] as String?;
  String? get userMessageId => data['user_message_id'] as String?;
  String? get messageId => data['message_id'] as String?;
  String? get deltaContent => data['content'] as String?;
  String? get errorMessage => data['message'] as String?;

  /// Multi-agents Phase 1 — identifiant de l'agent qui a répondu, présent
  /// sur l'event `done`. `null` pour les anciens serveurs ou les events
  /// pré-multi-agents.
  String? get agentUsed => data['agent_used'] as String?;

  /// Type de message persisté serveur — `'text'` (bulle classique) ou
  /// `'choices'` (QCM). Présent sur `done`.
  String? get messageType => data['message_type'] as String?;

  /// Multi-agents Phase 1 — pour les events `choices`.
  String? get choicesPrompt => data['prompt'] as String?;

  /// Pour les events `choices` : liste des options sélectionnables.
  List<AssistanceChoiceOption> get choicesOptions {
    final raw = data['options'];
    if (raw is List) {
      return raw
          .whereType<Map<String, dynamic>>()
          .map(AssistanceChoiceOption.fromJson)
          .toList();
    }
    return const [];
  }

  bool get choicesAllowFreeform =>
      (data['allow_freeform'] as bool?) ?? true;

  /// Phase 2c.2 — Embeds UI structurés émis sur l'event `done` (cartes
  /// `transaction_detail`, etc.). Le client les rend dans la même
  /// bulle assistant que le markdown principal.
  ///
  /// Identique au parsing `AssistanceHistoryMessage.embeds` : safe,
  /// silencieux sur types inconnus.
  List<AssistanceEmbed> get doneEmbeds {
    final raw = data['embeds'];
    if (raw is! List) return const [];
    return raw
        .whereType<Map<String, dynamic>>()
        .map(AssistanceEmbed.fromJson)
        .where((e) => e.type.isNotEmpty)
        .toList();
  }
}

/// Handle d'un tour assistant en streaming (MVP D.1.4.7).
///
/// Encapsule à la fois le `Stream<AssistanceTurnEvent>` consommable par
/// l'écran et une primitive [cancel] qui :
///   1. Ferme le `http.Client` côté mobile (interrompt la connexion SSE
///      sans attendre la fin) ;
///   2. Si un `conversationId` est connu (typiquement après réception
///      du frame `started`), appelle `POST /chat/turn/{conv_id}/cancel`
///      côté API pour **tuer la task background** côté serveur — ainsi
///      aucun message assistant n'est commité en BDD pour ce tour.
///
/// Sans cette double action, fermer juste le client côté mobile laisse
/// le pipeline OpenAI tourner côté serveur (cf. `_PENDING_STREAM_TASKS`)
/// et le message annulé réapparaît au prochain refresh de la conv —
/// effet « zombie » indésirable.
class AssistanceTurnHandle {
  AssistanceTurnHandle._({
    required this.events,
    required void Function(String? conversationId) cancelImpl,
  }) : _cancelImpl = cancelImpl;

  /// Stream à consommer via `await for`. Termine normalement au `done`
  /// (ou prématurément en cas d'annulation / erreur).
  final Stream<AssistanceTurnEvent> events;

  final void Function(String? conversationId) _cancelImpl;

  bool _cancelled = false;

  /// `true` si [cancel] a déjà été appelé sur ce handle. Permet au
  /// caller de distinguer une exception « annulation volontaire »
  /// d'une vraie erreur réseau pour décider de déclencher (ou non)
  /// le polling de catch-up.
  bool get isCancelled => _cancelled;

  /// Annule le tour en cours. Idempotent — un 2ᵉ appel ne fait rien.
  ///
  /// [conversationId] : ID de la conversation côté serveur (récupéré
  /// du frame `started`). Si fourni, déclenche aussi le cancel API
  /// côté serveur (sinon seul le client local est fermé et le serveur
  /// continuera de commit le message — à éviter sauf si la conv n'a
  /// pas encore été créée).
  void cancel({String? conversationId}) {
    if (_cancelled) return;
    _cancelled = true;
    _cancelImpl(conversationId);
  }
}

/// Streaming SSE d'un tour assistant (MVP D.1.4.5 + D.1.4.7).
///
/// Implémentation : utilise `http.Client.send(Request)` pour obtenir un
/// `StreamedResponse` non-bufferisé, puis parse manuellement les events
/// SSE format `event: <t>\ndata: <json>\n\n`. Pas de dépendance externe.
///
/// Robustesse :
/// - Si le statut initial n'est pas 200 → throw [ChatApiException].
/// - Si le client se ferme **involontairement** avant le `done` (ex.
///   user kill l'app, perte réseau), le serveur Python continue le
///   pipeline OpenAI et commit le message complet en BDD
///   (cf. `_PENDING_STREAM_TASKS` côté API). Comportement voulu pour
///   la robustesse réseau.
/// - Si le caller appelle [AssistanceTurnHandle.cancel] **explicitement**
///   (bouton stop), un POST sur `/chat/turn/{conv_id}/cancel` est
///   envoyé pour tuer la task côté serveur — aucun message n'est
///   commité.
AssistanceTurnHandle startAssistanceTurnStream({
  String? conversationId,
  required String content,
  String? agentHint,
}) {
  final client = http.Client();

  void doCancel(String? convId) {
    // 1) Côté serveur : tuer la task pour empêcher le commit BDD.
    //    Fire-and-forget — on ne bloque pas le doCancel sur la réponse.
    if (convId != null && convId.isNotEmpty) {
      // ignore: discarded_futures
      _cancelAssistanceTurn(convId);
    }
    // 2) Côté mobile : couper la connexion SSE pour libérer l'UI.
    //    Dans certains cas le client peut déjà être fermé (stream
    //    terminé naturellement) — `client.close()` est idempotent.
    try {
      client.close();
    } catch (_) {
      // ignore
    }
  }

  return AssistanceTurnHandle._(
    events: _runAssistanceTurnStream(
      client: client,
      conversationId: conversationId,
      content: content,
      agentHint: agentHint,
    ),
    cancelImpl: doCancel,
  );
}

Stream<AssistanceTurnEvent> _runAssistanceTurnStream({
  required http.Client client,
  String? conversationId,
  required String content,
  String? agentHint,
}) async* {
  final uri = Uri.parse(Config.mobileAssistanceChatTurnStreamUrl);
  final headers = await SessionBearerHttp.jsonHeadersAppScoped(
    uri: uri,
    debugTag: 'assistance_chat_turn_stream',
    withJsonContentType: true,
  );
  final body = jsonEncode({
    if (conversationId != null) 'conversation_id': conversationId,
    'content': content,
    if (agentHint != null) 'agent_hint': agentHint,
  });

  final request = http.Request('POST', uri);
  request.headers.addAll(headers);
  request.body = body;

  try {
    final streamed = await client.send(request);
    if (streamed.statusCode != 200) {
      final raw = await streamed.stream.bytesToString();
      throw ChatApiException(streamed.statusCode, raw);
    }

    final lines = streamed.stream.transform(utf8.decoder);
    final buffer = StringBuffer();

    await for (final chunk in lines) {
      buffer.write(chunk);
      while (true) {
        final s = buffer.toString();
        final idx = s.indexOf('\n\n');
        if (idx < 0) break;
        final block = s.substring(0, idx);
        final rest = s.substring(idx + 2);
        buffer
          ..clear()
          ..write(rest);

        String? eventType;
        final dataLines = StringBuffer();
        for (final line in block.split('\n')) {
          if (line.startsWith('event:')) {
            eventType = line.substring(6).trim();
          } else if (line.startsWith('data:')) {
            if (dataLines.isNotEmpty) dataLines.write('\n');
            // SSE spec : la valeur après `data:` peut avoir un espace optionnel.
            final value = line.substring(5);
            dataLines.write(value.startsWith(' ') ? value.substring(1) : value);
          }
        }
        if (eventType == null) continue;
        Map<String, dynamic> data = const {};
        final dataStr = dataLines.toString();
        if (dataStr.isNotEmpty) {
          try {
            final decoded = jsonDecode(dataStr);
            if (decoded is Map<String, dynamic>) data = decoded;
          } catch (_) {
            // Frame data malformée : on ignore.
          }
        }
        yield AssistanceTurnEvent(eventType, data);
      }
    }
  } finally {
    client.close();
  }
}

/// API call interne (D.1.4.7) — POST `/chat/turn/{conv_id}/cancel`.
///
/// Fire-and-forget : on n'attend pas la réponse pour libérer l'UI au
/// plus vite. L'endpoint est idempotent côté serveur (204 même sans
/// task en flight). Toute erreur (réseau, 4xx, 5xx) est loguée
/// silencieusement — au pire le message s'écrira tout de même côté
/// serveur, mais l'UX (carré stop) reste cohérente côté client.
Future<void> _cancelAssistanceTurn(String conversationId) async {
  try {
    final uri = Uri.parse(
      Config.mobileAssistanceChatTurnCancelUrl(conversationId),
    );
    final headers = await SessionBearerHttp.jsonHeadersAppScoped(
      uri: uri,
      debugTag: 'assistance_chat_turn_cancel',
    );
    final response = await http.post(uri, headers: headers);
    if (response.statusCode != 204 && response.statusCode != 200) {
      // ignore: avoid_print
      print(
        '[assistance.cancel] non-success status=${response.statusCode} body=${response.body}',
      );
    }
  } catch (e) {
    // ignore: avoid_print
    print('[assistance.cancel] error: $e');
  }
}

/// Marque une conversation comme lue côté serveur (MVP D.1.4.2).
///
/// Convention : un message assistant arrive « non lu » par défaut. C'est
/// au client de signaler explicitement la lecture après affichage. À
/// appeler :
///   - juste après la réception d'une réponse via [sendAssistanceTurn] ;
///   - juste après le chargement d'un historique via [fetchAssistanceHistory].
///
/// L'appel est conçu pour être *fire-and-forget* (idempotent côté serveur,
/// 204 No Content). Toute erreur (réseau, 4xx, 5xx) est silencieusement
/// loguée et avalée — la pastille restera simplement à l'état précédent
/// jusqu'au prochain succès.
Future<void> markAssistanceConversationRead(String conversationId) async {
  try {
    final uri = Uri.parse(
      Config.mobileAssistanceConversationReadUrl(conversationId),
    );
    final headers = await SessionBearerHttp.jsonHeadersAppScoped(
      uri: uri,
      debugTag: 'assistance_read',
    );
    final response = await http.post(uri, headers: headers);
    if (response.statusCode != 204 && response.statusCode != 200) {
      // ignore: avoid_print
      print(
        '[assistance.read] non-success status=${response.statusCode} body=${response.body}',
      );
    }
  } catch (e) {
    // ignore: avoid_print
    print('[assistance.read] error: $e');
  }
}
