import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../../core/config.dart';
import '../../../../../design_system/design_system.dart';
import '../../../../wallet/presentation/screens/bundle_invest_flow/bundle_invest_flow_controller.dart';
import '../../../data/lending_invest_api.dart';
import '../../../domain/models/offer_project.dart';

/// Confirmation / preview screen for Exclusive Offer investment.
///
/// Uses [ConfirmationPageLayout] for the shared page structure.
class LendingInvestPreviewScreen extends StatefulWidget {
  const LendingInvestPreviewScreen({
    super.key,
    required this.project,
    required this.fundingAsset,
    required this.fundingAmount,
    this.sourceAccount,
  });

  final OfferProject project;
  final String fundingAsset;
  final double fundingAmount;
  final BundleSourceAccount? sourceAccount;

  @override
  State<LendingInvestPreviewScreen> createState() =>
      _LendingInvestPreviewScreenState();
}

class _LendingInvestPreviewScreenState
    extends State<LendingInvestPreviewScreen> {
  final LendingInvestApi _api = const LendingInvestApi();
  LendingInvestPreviewResult? _preview;
  bool _loading = true;
  String? _error;
  bool _executing = false;

  TransactionStepState _step1State = TransactionStepState.pending;
  TransactionStepState _step2State = TransactionStepState.pending;

  static final _eurFormatter = NumberFormat.currency(
    locale: 'fr_FR', symbol: '€', decimalDigits: 2,
  );

  @override
  void initState() {
    super.initState();
    _loadPreview();
  }

  Future<void> _loadPreview() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final productId = widget.project.lendingProductId;
      if (productId == null || productId.isEmpty) {
        setState(() {
          _loading = false;
          _error = 'Identifiant produit manquant';
        });
        return;
      }
      final preview = await _api.previewInvest(
        productId: productId,
        fundingAsset: widget.fundingAsset,
        fundingAmount: widget.fundingAmount,
      );
      if (!mounted) return;
      setState(() {
        _preview = preview;
        _loading = false;
      });
    } on LendingInvestApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e.message;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Erreur de connexion';
      });
    }
  }

  String _formatAmount(double amount, String asset) {
    if (asset.toUpperCase() == 'EUR') {
      return _eurFormatter.format(amount);
    }
    final precision = amount < 1 ? 6 : 2;
    return '${amount.toStringAsFixed(precision)} $asset';
  }

  Future<void> _confirmInvest() async {
    if (_executing) return;
    final productId = widget.project.lendingProductId;
    if (productId == null || productId.isEmpty) return;

    final preview = _preview;
    final requiresConversion = preview != null && preview.requiresConversion;

    setState(() {
      _executing = true;
      _error = null;
      _step1State = TransactionStepState.processing;
      _step2State = TransactionStepState.pending;
    });

    try {
      // Step 1: simulated conversion delay if needed
      if (requiresConversion) {
        await Future<void>.delayed(const Duration(milliseconds: 600));
      }

      if (!mounted) return;
      setState(() {
        _step1State = TransactionStepState.completed;
        _step2State = TransactionStepState.processing;
      });

      // Step 2: execute investment
      final result = await _api.executeInvest(
        productId: productId,
        fundingAsset: widget.fundingAsset,
        fundingAmount: widget.fundingAmount,
      );

      if (!mounted) return;

      if (!result.isCompleted) {
        setState(() {
          _executing = false;
          _step1State = TransactionStepState.pending;
          _step2State = TransactionStepState.pending;
          _error = 'Statut inattendu : ${result.status}';
        });
        return;
      }

      setState(() {
        _step2State = TransactionStepState.completed;
      });

      await _showSuccessModal(result);
    } on LendingInvestApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _executing = false;
        _step1State = TransactionStepState.pending;
        _step2State = TransactionStepState.pending;
        _error = e.message;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _executing = false;
        _step1State = TransactionStepState.pending;
        _step2State = TransactionStepState.pending;
        _error = 'Erreur de connexion';
      });
    }
  }

  Future<void> _showSuccessModal(LendingInvestResult result) async {
    if (!mounted) return;

    final poolAsset = widget.project.lendingAsset ?? result.entryAssetUsed;
    final suppliedLabel =
        '${_fmtAmount(result.amountSupplied, poolAsset)} $poolAsset';

    final hadConversion =
        result.fundingAsset.toUpperCase() != poolAsset.toUpperCase();

    String subtitle;
    String? detail;

    if (hadConversion) {
      final fundingLabel =
          '${_fmtAmount(result.fundingAmount, result.fundingAsset)} ${result.fundingAsset}';
      subtitle = 'pour $fundingLabel';

      if (result.fundingAmount > 0 && result.amountSupplied > 0) {
        final rate = result.fundingAmount / result.amountSupplied;
        detail =
            'Execution price: ${_fmtCrypto(rate)} ${result.fundingAsset} / $poolAsset';
      }
    } else {
      subtitle = '${widget.project.title} · via ${widget.fundingAsset}';
    }

    await showTransactionSuccessOverlay(
      context: context,
      title: 'Investissement réussi',
      amount: suppliedLabel,
      subtitle: subtitle,
      detail: detail,
    );
  }

  static const _fiatSymbols = {'EUR', 'USD', 'USDC', 'USDT'};

  String _fmtAmount(double v, String asset) {
    if (_fiatSymbols.contains(asset.toUpperCase())) {
      return v.toStringAsFixed(2);
    }
    return _fmtCrypto(v);
  }

  String _fmtCrypto(double v) {
    if (v < 0.0001) return v.toStringAsExponential(2);
    String s;
    if (v < 1) {
      s = v.toStringAsFixed(8);
    } else {
      s = v.toStringAsFixed(6);
    }
    if (s.contains('.')) {
      s = s.replaceAll(RegExp(r'0+$'), '');
      s = s.replaceAll(RegExp(r'\.$'), '');
    }
    return s;
  }

  bool get _showEurEquivalent {
    final ccy = widget.fundingAsset.toUpperCase();
    return ccy != 'EUR' && ccy != 'EURC' && ccy != 'EURT';
  }

  @override
  Widget build(BuildContext context) {
    final preview = _preview;
    final isReady = !_loading && _error == null && preview != null;

    return ConfirmationPageLayout(
      onBack: () => Navigator.of(context).pop(),
      executing: _executing,
      loading: _loading,
      errorMessage: _error,
      onRetry: _loadPreview,
      directionIndicator: _buildExchangeDirection(),
      headline: 'Vous êtes sur le point d\'investir',
      heroAmount: _formatAmount(widget.fundingAmount, widget.fundingAsset),
      approximateValue: _showEurEquivalent && isReady
          ? '≈ ${_eurFormatter.format(preview.estimatedPoolAssetAmount)}'
          : null,
      subtitle: 'dans l\'offre exclusive ${widget.project.title}',
      ctaLabel: 'Confirmer l\'investissement',
      onConfirm: _confirmInvest,
      bodyChildren: isReady
          ? [
              _buildStepsModule(preview),
              const SizedBox(height: 16),
              _buildLegalFooter(preview),
            ]
          : [],
    );
  }

  String? get _sourceLogoUrl {
    final account = widget.sourceAccount;
    if (account != null && account.logoUrl != null) return account.logoUrl;
    final slug = widget.fundingAsset.trim().toLowerCase();
    if (slug == 'eur') return null;
    return Config.resolveLogoUrl('/media/crypto_logos/$slug.png');
  }

  Widget _buildExchangeDirection() {
    final account = widget.sourceAccount;
    final lendingAsset = widget.project.lendingAsset ?? widget.fundingAsset;

    return CryptoExchangeWidget(
      fromTicker: account?.currency ?? widget.fundingAsset,
      toTicker: lendingAsset,
      fromLogoUrl: _sourceLogoUrl,
      fromIcon: account?.icon ?? Icons.euro_rounded,
      toIcon: Icons.savings_rounded,
    );
  }

  Widget _buildStepsModule(LendingInvestPreviewResult preview) {
    final hasConversion = preview.requiresConversion;
    final isSameAsset = preview.fundingAsset.toUpperCase() ==
        preview.entryAssetUsed.toUpperCase();

    final TransactionStepItem step1;

    if (isSameAsset && !hasConversion) {
      step1 = TransactionStepItem(
        number: 1,
        title: 'Transfert',
        primaryText: 'Depuis votre wallet ${preview.entryAssetUsed}',
        secondaryText: 'Aucun frais de transfert',
        state: _step1State,
      );
    } else {
      final fromStr =
          _formatAmount(preview.fundingAmount, preview.fundingAsset);
      final toStr =
          '≈ ${_formatAmount(preview.estimatedPoolAssetAmount, preview.poolAsset)}';

      step1 = TransactionStepItem(
        number: 1,
        title: 'Conversion',
        state: _step1State,
        primaryWidget: Text(
          '$fromStr  →  $toStr',
          style: TransactionStepStyles.body,
        ),
        secondaryText: 'Montant estimé selon le prix de marché',
        approximate: true,
      );
    }

    final allocPrefix = hasConversion ? '≈ ' : '';
    final allocStr =
        '$allocPrefix${_formatAmount(preview.estimatedSupplyAmount, preview.poolAsset)}';

    return TransactionStepsModule(
      title: 'Étapes de votre investissement',
      steps: [
        step1,
        TransactionStepItem(
          number: 2,
          title: 'Allocation',
          state: _step2State,
          primaryWidget: Text(
            '$allocStr alloués au programme de prêt',
            style: TransactionStepStyles.body,
          ),
          secondaryText:
              'Votre allocation sera affectée au programme selon le statut du produit',
          approximate: hasConversion,
        ),
      ],
    );
  }

  Widget _buildLegalFooter(LendingInvestPreviewResult preview) {
    final poolAsset = preview.poolAsset;
    final hasConversion = preview.requiresConversion;
    final conversionClause =
        hasConversion ? 'une conversion éventuelle puis ' : '';

    return LegalFooterNote(
      segments: [
        LegalTextSegment(
          text:
              'En confirmant, vous reconnaissez que cette opération comprend ${conversionClause}une allocation à un programme de prêt en $poolAsset lié à cette offre. Consultez les ',
        ),
        const LegalTextSegment(
          text: 'Conditions générales',
          url: 'https://arquantix.com/legal/exclusive-offers',
        ),
        const LegalTextSegment(text: ' avant de confirmer.'),
      ],
    );
  }
}

