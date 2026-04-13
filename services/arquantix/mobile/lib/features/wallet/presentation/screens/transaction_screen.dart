import 'dart:developer' as developer;
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:share_plus/share_plus.dart';

import '../../../../design_system/design_system.dart';
import '../../data/transaction_detail_api.dart';
import '../../data/transaction_operation_pdf_api.dart';
import '../../domain/models/transaction_detail.dart';
import '../../domain/transaction_detail_presentation.dart';

class TransactionScreen extends StatefulWidget {
  const TransactionScreen({
    super.key,
    this.transactionId,
    required this.merchant,
    required this.dateTime,
    required this.amount,
    required this.icon,
    required this.iconColor,
  });

  final String? transactionId;
  final String merchant;
  final String dateTime;
  final String amount;
  final IconData icon;
  final Color iconColor;

  @override
  State<TransactionScreen> createState() => _TransactionScreenState();
}

class _TransactionScreenState extends State<TransactionScreen> {
  final TransactionDetailApi _api = const TransactionDetailApi();
  final TransactionOperationPdfApi _operationPdfApi = TransactionOperationPdfApi();

  TransactionDetail? _detail;
  bool _loading = true;
  bool _error = false;
  bool _notFound = false;
  bool _operationPdfLoading = false;

  @override
  void initState() {
    super.initState();
    _loadDetail();
  }

  Future<void> _loadDetail() async {
    final txId = widget.transactionId;
    if (txId == null || txId.isEmpty) {
      setState(() {
        _loading = false;
        _notFound = true;
      });
      return;
    }
    setState(() {
      _loading = true;
      _error = false;
      _notFound = false;
    });
    try {
      final detail = await _api.fetchDetail(txId);
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

  // ─────────────── Computed properties ───────────────

  TransactionBadgeStatus get _badgeStatus {
    final s = _detail?.status ?? 'completed';
    switch (s) {
      case 'pending':
      case 'processing':
        return TransactionBadgeStatus.pending;
      case 'failed':
      case 'reversed':
        return TransactionBadgeStatus.cancelled;
      default:
        return TransactionBadgeStatus.completed;
    }
  }

  String get _statusLabel {
    switch (_badgeStatus) {
      case TransactionBadgeStatus.pending:
        return 'En cours';
      case TransactionBadgeStatus.cancelled:
        return 'Échoué';
      case TransactionBadgeStatus.completed:
        return 'Complété';
    }
  }

  String get _displayTitle => _detail?.title ?? widget.merchant;

  String get _displayDate {
    if (_detail == null) return widget.dateTime;
    try {
      final dt = DateTime.parse(_detail!.createdAt);
      return DateFormat('dd/MM/yyyy à HH:mm', 'fr_FR').format(dt.toLocal());
    } catch (_) {
      final fallback = widget.dateTime.trim();
      return fallback.isNotEmpty ? fallback : '—';
    }
  }

  String get _displayAmount {
    if (_detail == null) return widget.amount;
    final d = _detail!;
    final formatted = NumberFormat.currency(
      locale: 'fr_FR',
      symbol: d.currencySymbol,
      decimalDigits: 2,
    ).format(d.amount);
    return d.isCredit ? '+$formatted' : '-$formatted';
  }

  /// Statut affiché dans la ligne secondaire du hero uniquement si utile (pas « Complété »).
  String? get _heroSecondaryStatus {
    switch (_badgeStatus) {
      case TransactionBadgeStatus.pending:
      case TransactionBadgeStatus.cancelled:
        return _statusLabel;
      case TransactionBadgeStatus.completed:
        return null;
    }
  }

  List<TableInformationRowData> get _transactionInfoRows {
    if (_detail == null) return [];
    final d = _detail!;
    return [
      TableInformationRowData(left: 'Transaction ID', right: _truncateId(d.id)),
      TableInformationRowData(left: 'Devise', right: '${d.currency} (${d.currencySymbol})'),
      if (d.providerName != null)
        TableInformationRowData(left: 'Provider', right: d.providerName!),
      TableInformationRowData(left: 'Montant crédité', right: _displayAmount),
      TableInformationRowData(left: 'Date / heure', right: _displayDate),
      if (d.bookingDate != null)
        TableInformationRowData(left: 'Date de valeur comptable', right: d.bookingDate!),
      if (d.valueDate != null)
        TableInformationRowData(left: 'Date de valeur', right: d.valueDate!),
    ];
  }

  List<TableInformationRowData> get _bankInfoRows {
    if (_detail == null) return [];
    final d = _detail!;
    return [
      if (d.remitterName != null)
        TableInformationRowData(left: 'Nom de l\'émetteur', right: d.remitterName!),
      if (d.remitterIban != null)
        TableInformationRowData(left: 'IBAN émetteur', right: d.remitterIban!),
      if (d.remitterBankName != null)
        TableInformationRowData(left: 'Banque émettrice', right: d.remitterBankName!),
      if (d.targetIban != null)
        TableInformationRowData(left: 'IBAN Vancelian crédité', right: d.targetIban!),
      if (d.accountHolderName != null)
        TableInformationRowData(left: 'Titulaire du compte', right: d.accountHolderName!),
    ];
  }

  List<TableInformationRowData> get _referenceRows {
    if (_detail == null) return [];
    final d = _detail!;
    return [
      if (d.externalReference != null)
        TableInformationRowData(left: 'Référence externe', right: d.externalReference!),
      if (d.providerReference != null)
        TableInformationRowData(left: 'Référence provider', right: d.providerReference!),
      if (d.narrative != null)
        TableInformationRowData(left: 'Note / narrative', right: d.narrative!),
    ];
  }

  String _truncateId(String id) {
    if (id.length <= 12) return id;
    return '${id.substring(0, 8)}…${id.substring(id.length - 4)}';
  }

  List<ArticleCategoryBadgeData>? _categoryBadgesFor(TransactionDetail d) {
    final label = d.heroCategoryBadgeLabel;
    if (label.trim().isEmpty) return null;
    return [
      ArticleCategoryBadgeData(
        label: label,
        dotColor: AppColors.accent,
      ),
    ];
  }

  void _onJustify(BuildContext context, TransactionDetail d) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Justificatif — bientôt disponible')),
    );
  }

  Future<void> _onDownload(BuildContext context, TransactionDetail d) async {
    final messenger = ScaffoldMessenger.of(context);
    final shareOrigin = _sharePositionOrigin(context);
    final id = widget.transactionId ?? d.id;
    if (id.isEmpty) {
      messenger.showSnackBar(
        const SnackBar(content: Text('Identifiant de transaction manquant.')),
      );
      return;
    }
    setState(() => _operationPdfLoading = true);
    try {
      final bytes = await _operationPdfApi.fetchOperationStatementPdf(id);
      if (!mounted) return;
      developer.log(
        'OPERATION_STATEMENT_PDF: fetch OK bytes=${bytes.length}',
        name: 'TransactionScreen',
      );
      final name =
          'releve-operation-${DateFormat('yyyy-MM-dd').format(DateTime.now())}.pdf';
      final file = File('${Directory.systemTemp.path}/$name');
      await file.writeAsBytes(bytes, flush: true);
      developer.log(
        'OPERATION_STATEMENT_PDF: file written path=${file.path}',
        name: 'TransactionScreen',
      );
      await Share.shareXFiles(
        [XFile(file.path, mimeType: 'application/pdf', name: name)],
        subject: 'Relevé d\'opération',
        sharePositionOrigin: shareOrigin,
      );
    } on TransactionOperationPdfException catch (e) {
      if (!mounted) return;
      developer.log(
        'OPERATION_STATEMENT_PDF: HTTP ${e.statusCode} — ${e.message}',
        name: 'TransactionScreen',
      );
      messenger.showSnackBar(
        SnackBar(content: Text(e.message)),
      );
    } catch (e, st) {
      if (!mounted) return;
      developer.log(
        'OPERATION_STATEMENT_PDF: post-fetch failure $e',
        name: 'TransactionScreen',
        error: e,
        stackTrace: st,
      );
      messenger.showSnackBar(
        SnackBar(content: Text('Erreur : $e')),
      );
    } finally {
      if (mounted) setState(() => _operationPdfLoading = false);
    }
  }

  /// iPad : [sharePositionOrigin] requis pour le popover de partage.
  Rect _sharePositionOrigin(BuildContext context) {
    final size = MediaQuery.sizeOf(context);
    return Rect.fromLTWH(0, size.height * 0.45, size.width, size.height * 0.45);
  }

  Widget _buildHeroActionsBlock(BuildContext context, TransactionDetail d) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        InstrumentDetailHeroSupportingLine(
          text: _displayDate,
          secondarySuffix: _heroSecondaryStatus,
        ),
        const SizedBox(height: AppSpacing.md),
        InstrumentDetailHeroCtaRow(
          children: [
            if (d.isJustifiable)
              AppSecondaryButton(
                label: 'Justifier',
                horizontalPadding: AppSpacing.s4,
                leading: const Icon(Icons.policy_outlined, size: 20),
                onPressed:
                    _operationPdfLoading ? null : () => _onJustify(context, d),
              ),
            AppSecondaryButton(
              label: _operationPdfLoading ? 'Patientez…' : 'Télécharger',
              horizontalPadding: AppSpacing.s4,
              leading: _operationPdfLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.download_outlined, size: 20),
              onPressed: _operationPdfLoading
                  ? null
                  : () {
                      _onDownload(context, d);
                    },
            ),
          ],
        ),
      ],
    );
  }

  // ─────────────── Build ───────────────

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return _wrapWithSimpleNav(
        body: _buildLoading(),
      );
    }
    if (_notFound) {
      return _wrapWithSimpleNav(
        body: _buildNotFound(),
      );
    }
    if (_error || _detail == null) {
      return _wrapWithSimpleNav(
        body: _buildError(),
      );
    }

    return _buildInstrumentLayoutDetail(context);
  }

  Widget _wrapWithSimpleNav({required Widget body}) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.back,
        title: _displayTitle,
        centerTitle: false,
        titleTextStyle: AppTypography.paragraph.copyWith(
          color: AppColors.textPrimary,
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
        onBackTap: () => Navigator.of(context).pop(),
      ),
      body: SafeArea(
        bottom: false,
        child: body,
      ),
    );
  }

  Widget _buildInstrumentLayoutDetail(BuildContext context) {
    final d = _detail!;
    const hp = EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge);
    final txInfoRows = _transactionInfoRows;
    final bankRows = _bankInfoRows;
    final refRows = _referenceRows;

    return LayoutPageInstrumentDetail(
      /// 40px entre la fin du hero (boutons) et le premier module ([AppSpacing.s10]).
      contentTopSpacing: AppSpacing.s10,
      categoryBadges: _categoryBadgesFor(d),
      titleLeading: _TransactionHeroAvatar(
        icon: widget.icon,
        backgroundColor: widget.iconColor,
      ),
      title: _displayTitle,
      subtitle: _displayAmount,
      subtitleStyle: AppTypography.amountPrimary.copyWith(
        color: AppColors.textPrimary,
      ),
      heroActions: _buildHeroActionsBlock(context, d),
      onLeadingTap: () => Navigator.of(context).pop(),
      onRefresh: _loadDetail,
      content: [
        if (txInfoRows.isNotEmpty)
          Padding(
            padding: hp,
            child: TableInformationModule(
              title: 'Informations transaction',
              rows: txInfoRows,
            ),
          ),
        if (bankRows.isNotEmpty)
          Padding(
            padding: hp,
            child: TableInformationModule(
              title: 'Coordonnées bancaires',
              rows: bankRows,
            ),
          ),
        if (refRows.isNotEmpty)
          Padding(
            padding: hp,
            child: TableInformationModule(
              title: 'Références',
              rows: refRows,
            ),
          ),
      ],
    );
  }

  Widget _buildLoading() {
    return const Center(
      child: Padding(
        padding: EdgeInsets.only(top: 80),
        child: CircularProgressIndicator.adaptive(),
      ),
    );
  }

  Widget _buildNotFound() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.only(top: 80),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.search_off_rounded, size: 48, color: AppColors.textSecondary),
            const SizedBox(height: AppSpacing.md),
            Text(
              'Transaction introuvable',
              style: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildError() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.only(top: 80),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline_rounded, size: 48, color: AppColors.textSecondary),
            const SizedBox(height: AppSpacing.md),
            Text(
              'Impossible de charger la transaction',
              style: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: AppSpacing.md),
            TextButton(onPressed: _loadDetail, child: const Text('Réessayer')),
          ],
        ),
      ),
    );
  }
}

/// Avatar circulaire 24px, même ordre de grandeur que [CryptoAvatarSize.small].
class _TransactionHeroAvatar extends StatelessWidget {
  const _TransactionHeroAvatar({
    required this.icon,
    required this.backgroundColor,
  });

  final IconData icon;
  final Color backgroundColor;

  static const double _size = 24;
  static const double _iconSize = 14;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: _size,
      height: _size,
      child: ClipOval(
        child: ColoredBox(
          color: backgroundColor,
          child: Icon(
            icon,
            size: _iconSize,
            color: Colors.white,
          ),
        ),
      ),
    );
  }
}
