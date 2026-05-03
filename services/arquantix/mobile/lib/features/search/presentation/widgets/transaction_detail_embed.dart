import 'dart:developer' as developer;
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:share_plus/share_plus.dart';

import '../../../../design_system/design_system.dart';
import '../../../news/presentation/markdown/article_paragraph_markdown.dart';
import '../../../wallet/data/transaction_detail_api.dart';
import '../../../wallet/data/transaction_operation_pdf_api.dart'
    show TransactionOperationPdfApi, TransactionOperationPdfException;
import '../../../wallet/domain/models/transaction_detail.dart';
import '../../application/assistance_deep_link_resolver.dart';
import '../../data/chat_api.dart';

/// Carte « détail d'une transaction » embarquée dans une bulle assistant.
///
/// Phase 2c.2 — l'agent `compliance.transactional` produit un embed via
/// le tool `read_transaction_detail`. Le serveur n'envoie au client que
/// l'`transaction_id` + une liste d'actions whitelistées (deep-links
/// `view_transaction_detail` + `download_transaction_statement`). Ce
/// widget :
///
///   1. fetch les détails complets via `TransactionDetailApi` (API
///      authentifiée du user, donc aucun risque de leak côté LLM ;
///      les vraies données ne transitent jamais par le LLM) ;
///   2. affiche un **skeleton animé** pendant le fetch (UX premium) ;
///   3. compose un **markdown structuré** (titre H2 + tableau 2
///      colonnes au header invisible + 2 liens sur 2 lignes
///      différentes) qui est rendu par [ArticleParagraphMarkdown] —
///      design cohérent avec le reste du chat assistant (pas de
///      carte custom à maintenir) ;
///   4. intercepte les liens : `…/statement` → download PDF + Share
///      natif (pas de navigation), tout autre deep-link → résolu via
///      [AssistanceDeepLinkResolver].
///
/// Robustesse :
///   - 404 : message d'erreur compact + lien fallback « Voir mes
///     transactions ».
///   - Réseau / 5xx : message d'erreur compact + lien retry.
///   - L'utilisateur n'est jamais bloqué : la bulle assistant texte
///     reste lisible au-dessus de la carte.
class TransactionDetailEmbed extends StatefulWidget {
  const TransactionDetailEmbed({
    super.key,
    required this.transactionId,
    required this.actions,
    this.summary,
  });

  /// ID opaque de la transaction (UUID). Doit être whitelisté côté
  /// backend (vérification d'ownership dans `read_transaction_detail`).
  final String transactionId;

  /// Liste d'actions whitelistées. Chacune devient un lien markdown
  /// `[label](deep_link)` rendu sur sa propre ligne. Cas habituels :
  ///   - `view_transaction_detail` (push fiche détail)
  ///   - `download_transaction_statement` (download PDF + Share)
  final List<AssistanceChoiceOption> actions;

  /// Récap textuel composé serveur (Phase 2c.4) — phrase chaleureuse
  /// avec montant + date + mention du problème uniquement si statut
  /// ≠ completed. Inséré en haut de la carte pour fusionner
  /// l'intro LLM et la carte détail en **un seul module visuel**.
  /// `null` si le serveur n'a pas pu composer (rétro-compat).
  final String? summary;

  @override
  State<TransactionDetailEmbed> createState() => _TransactionDetailEmbedState();
}

class _TransactionDetailEmbedState extends State<TransactionDetailEmbed> {
  final TransactionDetailApi _api = const TransactionDetailApi();
  final TransactionOperationPdfApi _pdfApi = TransactionOperationPdfApi();

  TransactionDetail? _detail;
  bool _loading = true;
  bool _notFound = false;
  bool _error = false;
  bool _downloadingPdf = false;

  @override
  void initState() {
    super.initState();
    _loadDetail();
  }

  Future<void> _loadDetail() async {
    setState(() {
      _loading = true;
      _notFound = false;
      _error = false;
    });
    try {
      final detail = await _api.fetchDetail(widget.transactionId);
      if (!mounted) return;
      setState(() {
        _detail = detail;
        _loading = false;
      });
    } on TransactionDetailApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _notFound = e.statusCode == 404;
        _error = e.statusCode != 404;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = true;
      });
    }
  }

  Future<void> _onLinkTap(String href) async {
    if (href.endsWith('/statement')) {
      await _downloadStatement();
      return;
    }
    if (!mounted) return;
    await AssistanceDeepLinkResolver.resolve(context, href);
  }

  Future<void> _downloadStatement() async {
    if (_downloadingPdf) return;
    setState(() => _downloadingPdf = true);
    final messenger = ScaffoldMessenger.maybeOf(context);
    messenger?.showSnackBar(
      const SnackBar(
        content: Text('Téléchargement du relevé en cours…'),
        duration: Duration(seconds: 2),
      ),
    );
    // Étape par étape, pour distinguer dans les logs :
    //   - une erreur HTTP (BFF / API Python),
    //   - une erreur d'écriture fichier locale (FS),
    //   - une erreur du Share Sheet natif (notamment iOS simulator
    //     où `share_plus` peut lever sans message lisible).
    String stage = 'init';
    try {
      stage = 'http_fetch';
      final Uint8List bytes =
          await _pdfApi.fetchOperationStatementPdf(widget.transactionId);
      if (!mounted) return;

      stage = 'file_write';
      final fileName =
          'releve-operation-${DateFormat('yyyy-MM-dd').format(DateTime.now())}.pdf';
      final file = File('${Directory.systemTemp.path}/$fileName');
      await file.writeAsBytes(bytes, flush: true);
      developer.log(
        'TransactionDetailEmbed.statement_written path=${file.path} bytes=${bytes.length}',
        name: 'ASSISTANCE_EMBED',
      );

      stage = 'share';
      await Share.shareXFiles(
        [XFile(file.path, mimeType: 'application/pdf', name: fileName)],
        subject: 'Relevé d\'opération',
      );
    } on TransactionOperationPdfException catch (e) {
      developer.log(
        'TransactionDetailEmbed.statement_http_error '
        'stage=$stage status=${e.statusCode} message=${e.message}',
        name: 'ASSISTANCE_EMBED',
      );
      if (!mounted) return;
      _showSnack(
        messenger,
        'Téléchargement impossible (HTTP ${e.statusCode}) — ${e.message}',
      );
    } catch (e, st) {
      developer.log(
        'TransactionDetailEmbed.statement_failed stage=$stage err=$e',
        name: 'ASSISTANCE_EMBED',
        error: e,
        stackTrace: st,
      );
      if (!mounted) return;
      _showSnack(
        messenger,
        stage == 'share'
            // Erreur du Share Sheet → on dit clairement que le PDF est
            // bien généré mais que le partage natif n'a pas pu être
            // ouvert. C'est un cas fréquent en simulateur iOS.
            ? 'Relevé généré, mais l\'ouverture du partage a échoué.'
            : 'Impossible de télécharger le relevé pour le moment.',
      );
    } finally {
      if (mounted) setState(() => _downloadingPdf = false);
    }
  }

  void _showSnack(ScaffoldMessengerState? messenger, String message) {
    messenger?.showSnackBar(
      SnackBar(
        content: Text(message),
        duration: const Duration(seconds: 5),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const _TransactionDetailSkeleton();
    if (_notFound || _error || _detail == null) {
      return _TransactionDetailErrorMarkdown(
        notFound: _notFound,
        onLinkTap: _onLinkTap,
        onRetry: _error ? _loadDetail : null,
      );
    }
    return _TransactionDetailMarkdown(
      markdown: _buildMarkdown(_detail!, widget.actions, widget.summary),
      onLinkTap: _onLinkTap,
    );
  }
}

// ─────────────────────────────────────────────────────────────────────
// Composition du markdown
// ─────────────────────────────────────────────────────────────────────

String _buildMarkdown(
  TransactionDetail d,
  List<AssistanceChoiceOption> actions,
  String? summary,
) {
  final dateFmt = DateFormat('d MMMM yyyy à HH:mm', 'fr_FR');
  final amountFormatted = NumberFormat.currency(
    locale: 'fr_FR',
    symbol: d.currencySymbol,
    decimalDigits: 2,
  ).format(d.amount);
  final amountDisplay =
      d.isCredit ? '+$amountFormatted' : '-$amountFormatted';

  String safeDate(String? raw) {
    if (raw == null || raw.isEmpty) return '—';
    try {
      return dateFmt.format(DateTime.parse(raw).toLocal());
    } catch (_) {
      return raw;
    }
  }

  // Lignes du tableau, 2 colonnes (libellé | valeur). On laisse les
  // optionnels en `null` puis on filtre, pour un tableau compact qui
  // s'adapte aux données disponibles.
  final rows = <List<String>>[];
  rows.add([
    'Type',
    _humanizeKind(d.transactionKind ?? d.transactionType),
  ]);
  rows.add(['Statut', d.statusLabel]);
  rows.add(['Montant', amountDisplay]);
  rows.add(['Date', safeDate(d.createdAt)]);
  if (d.providerName != null && d.providerName!.isNotEmpty) {
    rows.add(['Prestataire', d.providerName!]);
  }
  if (d.remitterName != null && d.remitterName!.isNotEmpty) {
    rows.add(['Émetteur', d.remitterName!]);
  }
  if (d.remitterBankName != null && d.remitterBankName!.isNotEmpty) {
    rows.add(['Banque', d.remitterBankName!]);
  }
  if (d.remitterIban != null && d.remitterIban!.isNotEmpty) {
    rows.add(['IBAN émetteur', _maskIban(d.remitterIban!)]);
  }
  if (d.bookingDate != null && d.bookingDate!.isNotEmpty) {
    rows.add(['Date comptable', d.bookingDate!]);
  }
  if (d.valueDate != null && d.valueDate!.isNotEmpty) {
    rows.add(['Date de valeur', d.valueDate!]);
  }
  if (d.narrative != null && d.narrative!.isNotEmpty) {
    rows.add(['Libellé', d.narrative!]);
  }

  // Construction de la table markdown — 2 colonnes, **header
  // visuellement invisible**. `flutter_markdown` exige
  // syntaxiquement une ligne d'en-tête (sinon il ne reconnaît pas
  // la table GFM), mais on n'a aucune valeur sémantique à afficher
  // ici (les libellés « Champ » / « Valeur » polluent l'UX). On
  // remplit donc chaque cellule du header avec un caractère
  // insécable (\u00A0) : la syntaxe markdown reste valide, mais le
  // texte rendu est vide. Le `MarkdownStyleSheet` partagé applique
  // un padding de cellule modéré ; le résultat visuel est juste un
  // léger blanc en haut de la table — préférable à un header textuel
  // redondant avec les libellés en gras de la première colonne.
  final table = StringBuffer();
  table.writeln('| \u00A0 | \u00A0 |');
  table.writeln('|---|---|');
  for (final r in rows) {
    final v = _escapePipes(r[1]);
    table.writeln('| **${r[0]}** | $v |');
  }

  // 2 liens sur 2 lignes différentes (paragraphes markdown séparés
  // par une ligne vide pour que `flutter_markdown` les rende sur
  // des lignes distinctes — sinon les liens consécutifs seraient
  // collés sur la même ligne).
  final linkLines = StringBuffer();
  for (final a in actions) {
    final href = a.deepLink;
    if (href == null || href.isEmpty || a.label.isEmpty) continue;
    linkLines.writeln('[${a.label}]($href)');
    linkLines.writeln();
  }

  // Phase 2c.4 — `summary` (composé serveur) en haut de la carte
  // pour produire un seul module visuel cohérent. La phrase est
  // rendue comme un paragraphe markdown standard (pas en italique
  // ni en blockquote) — ton chaleureux, lisible, en continuité
  // visuelle avec le titre H2 et le tableau.
  //
  // Le titre est en H2 (et non H1) pour rester subordonné à la
  // bulle assistant : on n'est pas dans un article où le H1
  // ouvrirait la page, mais dans une carte de détail.
  final blocks = <String>[];
  if (summary != null && summary.trim().isNotEmpty) {
    blocks.add(summary.trim());
  }
  blocks.add('## Information de transaction');
  blocks.add(table.toString().trimRight());
  blocks.add(linkLines.toString().trimRight());
  return blocks.join('\n\n');
}

String _humanizeKind(String raw) {
  final lower = raw.trim().toLowerCase();
  switch (lower) {
    case 'bank_transfer_in':
      return 'Virement bancaire entrant';
    case 'bank_transfer_out':
      return 'Virement bancaire sortant';
    case 'card_in':
      return 'Dépôt par carte';
    case 'crypto_in':
      return 'Dépôt en crypto';
    case 'deposit':
      return 'Dépôt';
    case 'withdrawal':
      return 'Retrait';
    case 'exchange_buy':
      return 'Achat (exchange)';
    case 'exchange_sell':
      return 'Vente (exchange)';
    default:
      return lower
          .split('_')
          .where((s) => s.isNotEmpty)
          .map((s) =>
              '${s[0].toUpperCase()}${s.length > 1 ? s.substring(1) : ''}')
          .join(' ');
  }
}

String _maskIban(String iban) {
  final clean = iban.replaceAll(' ', '');
  if (clean.length <= 8) return iban;
  final start = clean.substring(0, 4);
  final end = clean.substring(clean.length - 4);
  return '$start ···· $end';
}

/// Échappe les `|` à l'intérieur d'une cellule pour ne pas casser la
/// table markdown si une donnée contient un pipe (rare mais pas
/// impossible — narrative libre côté banque).
String _escapePipes(String s) => s.replaceAll('|', r'\|');

// ─────────────────────────────────────────────────────────────────────
// Rendu — markdown loaded
// ─────────────────────────────────────────────────────────────────────

class _TransactionDetailMarkdown extends StatelessWidget {
  const _TransactionDetailMarkdown({
    required this.markdown,
    required this.onLinkTap,
  });

  final String markdown;
  final Future<void> Function(String href) onLinkTap;

  @override
  Widget build(BuildContext context) {
    return _CardShell(
      child: ArticleParagraphMarkdown(
        text: markdown,
        baseStyle: AppTypography.paragraph,
        onOpenLink: onLinkTap,
        blockSpacing: AppSpacing.sm,
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────
// Rendu — markdown d'erreur (404 / réseau)
// ─────────────────────────────────────────────────────────────────────

class _TransactionDetailErrorMarkdown extends StatelessWidget {
  const _TransactionDetailErrorMarkdown({
    required this.notFound,
    required this.onLinkTap,
    this.onRetry,
  });

  final bool notFound;
  final Future<void> Function(String href) onLinkTap;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final body = StringBuffer();
    body.writeln('## Information de transaction');
    body.writeln();
    if (notFound) {
      body.writeln('Détail indisponible (transaction introuvable).');
      body.writeln();
      body.writeln('[Voir mes transactions](vancelian://app/transactions)');
    } else {
      body.writeln(
        'Impossible de charger le détail pour le moment.',
      );
      body.writeln();
      // Lien spécial `retry://reload` capté ci-dessous.
      body.writeln('[Réessayer](retry://reload)');
    }

    return _CardShell(
      child: ArticleParagraphMarkdown(
        text: body.toString().trimRight(),
        baseStyle: AppTypography.paragraph.copyWith(
          color: AppColors.textSecondary,
        ),
        onOpenLink: (href) async {
          if (href == 'retry://reload') {
            onRetry?.call();
            return;
          }
          await onLinkTap(href);
        },
        blockSpacing: AppSpacing.sm,
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────
// Skeleton premium : lignes shimmer animées
// ─────────────────────────────────────────────────────────────────────

class _TransactionDetailSkeleton extends StatefulWidget {
  const _TransactionDetailSkeleton();

  @override
  State<_TransactionDetailSkeleton> createState() =>
      _TransactionDetailSkeletonState();
}

class _TransactionDetailSkeletonState extends State<_TransactionDetailSkeleton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1100),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return _CardShell(
      child: AnimatedBuilder(
        animation: _controller,
        builder: (_, __) {
          final t = _controller.value;
          final base = Color.lerp(
            const Color(0xFFE5E7EB),
            const Color(0xFFF1F5F9),
            t,
          )!;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _shimmerLine(width: 200, height: 22, color: base),
              const SizedBox(height: AppSpacing.md),
              _shimmerLine(width: double.infinity, height: 12, color: base),
              const SizedBox(height: AppSpacing.xs),
              _shimmerLine(width: 280, height: 12, color: base),
              const SizedBox(height: AppSpacing.xs),
              _shimmerLine(width: 240, height: 12, color: base),
              const SizedBox(height: AppSpacing.xs),
              _shimmerLine(width: 200, height: 12, color: base),
              const SizedBox(height: AppSpacing.md),
              _shimmerLine(width: 140, height: 14, color: base),
            ],
          );
        },
      ),
    );
  }

  Widget _shimmerLine({
    required double width,
    required double height,
    required Color color,
  }) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(6),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────
// Coquille « bulle assistant » réutilisée à l'identique : surface
// blanche, radius asymétrique (top-left carré → la pointe « point
// vers l'émetteur assistant »), ombre douce du DS. Visuellement
// l'embed se lit comme une seconde bulle assistant juste sous celle
// qui contient l'intro courte du LLM.
// ─────────────────────────────────────────────────────────────────────

class _CardShell extends StatelessWidget {
  const _CardShell({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
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
      child: child,
    );
  }
}
