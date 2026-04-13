import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../../core/config.dart';
import '../../../../../design_system/design_system.dart';
import '../../../data/exchange_api.dart';
import 'sell_all_processing_sheet.dart';

class SellAllConfirmationScreen extends StatefulWidget {
  const SellAllConfirmationScreen({super.key});

  @override
  State<SellAllConfirmationScreen> createState() =>
      _SellAllConfirmationScreenState();
}

class _SellAllConfirmationScreenState extends State<SellAllConfirmationScreen> {
  final ExchangeApi _exchangeApi = ExchangeApi();

  bool _loading = true;
  SellAllPreviewResult? _preview;
  String? _error;
  bool _executing = false;

  static final _eurFormatter = NumberFormat.currency(
    locale: 'fr_FR',
    symbol: '€',
    decimalDigits: 2,
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
      final result = await _exchangeApi.previewSellAll();
      if (!mounted) return;
      if (result.error != null) {
        setState(() {
          _loading = false;
          _error = result.error;
        });
        return;
      }
      if (result.items.isEmpty) {
        setState(() {
          _loading = false;
          _error = 'Aucune position crypto à vendre';
        });
        return;
      }
      setState(() {
        _preview = result;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Impossible de charger la preview';
      });
    }
  }

  Future<void> _executeSellAll() async {
    if (_executing || _preview == null) return;
    setState(() => _executing = true);

    try {
      final result = await _exchangeApi.executeSellAll();
      if (!mounted) return;

      if (result.totalAssetsFailed == 0) {
        await showTransactionSuccessOverlay(
          context: context,
          title: 'Liquidation terminée',
          amount: _eurFormatter.format(result.actualTotalEurReceived),
          subtitle: '${result.totalAssetsSold} position${result.totalAssetsSold > 1 ? 's' : ''} vendue${result.totalAssetsSold > 1 ? 's' : ''}',
        );
        return;
      }

      // Partial or complex result — fall back to processing sheet
      if (!mounted) return;
      final didSell = await showModalBottomSheet<bool>(
        context: context,
        isDismissible: false,
        enableDrag: false,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (_) => SellAllProcessingSheet(
          preview: _preview!,
          exchangeApi: _exchangeApi,
          preloadedResult: result,
        ),
      );
      if (!mounted) return;
      setState(() => _executing = false);
      if (didSell == true) {
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _executing = false);

      final didSell = await showModalBottomSheet<bool>(
        context: context,
        isDismissible: false,
        enableDrag: false,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (_) => SellAllProcessingSheet(
          preview: _preview!,
          exchangeApi: _exchangeApi,
          preloadedError: e is ExchangeApiException ? e.message : e.toString(),
        ),
      );
      if (!mounted) return;
      if (didSell == true) {
        Navigator.of(context).pop(true);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.back,
        title: 'Vendre tout',
        titleOpacity: 1,
        centerTitle: true,
      ),
      body: SafeArea(
        child: _loading
            ? const Center(
                child: CircularProgressIndicator(
                  color: AppColors.indigo,
                  strokeWidth: 2,
                ),
              )
            : _error != null
                ? _buildError()
                : _buildContent(),
      ),
    );
  }

  Widget _buildError() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline_rounded, size: 48, color: AppColors.textSecondary),
            const SizedBox(height: 16),
            Text(
              _error!,
              style: AppTypography.bodyLarge.copyWith(color: AppColors.textSecondary),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () => Navigator.of(context).pop(false),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.indigo,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                child: const Text('Fermer'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent() {
    final preview = _preview!;
    final readyItems = preview.items.where((i) => i.isReady).toList();
    final unavailableItems = preview.items.where((i) => !i.isReady).toList();

    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
            children: [
              const SizedBox(height: AppSpacing.xl),
              Text(
                'Vendre toutes mes cryptos',
                style: AppTypography.titleLarge.copyWith(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w800,
                  fontSize: 24,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Vous êtes sur le point de vendre l\'intégralité de vos positions crypto et de recevoir le produit en euros sur votre Compte Euro.',
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.textSecondary,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 24),
              _buildSummaryCard(preview),
              const SizedBox(height: 20),
              AppSectionTitle2('Positions à vendre'),
              const SizedBox(height: 12),
              _buildItemsCard(readyItems),
              if (unavailableItems.isNotEmpty) ...[
                const SizedBox(height: 20),
                AppSectionTitle2('Indisponibles'),
                const SizedBox(height: 12),
                _buildItemsCard(unavailableItems, isUnavailable: true),
              ],
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFF3CD),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.warning_amber_rounded, color: Color(0xFF856404), size: 20),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Les prix peuvent varier entre le moment de cette preview et l\'exécution réelle. Les montants affichés sont des estimations.',
                        style: AppTypography.bodySmall.copyWith(
                          color: const Color(0xFF856404),
                          height: 1.4,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 32),
            ],
          ),
        ),
        _buildBottomBar(readyItems.isNotEmpty),
      ],
    );
  }

  Widget _buildSummaryCard(SellAllPreviewResult preview) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: AmountDisplay(
        amount: _eurFormatter.format(preview.estimatedTotalEur),
        subtitle: 'Estimation totale',
        subtext: '${preview.totalAssets} position${preview.totalAssets > 1 ? 's' : ''}',
      ),
    );
  }

  Widget _buildItemsCard(List<SellAllPreviewItem> items, {bool isUnavailable = false}) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: items.map((item) {
            final logoKey = item.asset.toLowerCase();
            final logoUrl = Config.resolveLogoUrl('/media/crypto_logos/$logoKey.png');

            return Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              child: Row(
                children: [
                  CryptoAvatar(
                    ticker: item.asset,
                    logoUrl: logoUrl,
                    size: CryptoAvatarSize.large,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          item.asset,
                          style: AppTypography.bodyMedium.copyWith(
                            color: AppColors.textPrimary,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        Text(
                          '${item.amountAvailable} ${item.asset}',
                          style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary),
                        ),
                      ],
                    ),
                  ),
                  if (isUnavailable)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: const Color(0xFFDC2626).withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        'Indisponible',
                        style: AppTypography.bodySmall.copyWith(
                          color: const Color(0xFFDC2626),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    )
                  else
                    Text(
                      _eurFormatter.format(item.estimatedEurNet),
                      style: AppTypography.bodyMedium.copyWith(
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                ],
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  Widget _buildBottomBar(bool canProceed) {
    return Container(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 12, AppSpacing.lg, 24),
      decoration: BoxDecoration(
        color: AppColors.pageBackground,
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.04),
            blurRadius: 8,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: OutlinedButton(
              onPressed: _executing ? null : () => Navigator.of(context).pop(false),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.textPrimary,
                side: BorderSide(color: AppColors.textSecondary.withValues(alpha: 0.3)),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
              child: const Text('Annuler'),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            flex: 2,
            child: ElevatedButton(
              onPressed: (canProceed && !_executing) ? _executeSellAll : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFDC2626),
                foregroundColor: Colors.white,
                disabledBackgroundColor: const Color(0xFFDC2626).withValues(alpha: 0.4),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
              child: _executing
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                    )
                  : const Text(
                      'Confirmer la vente',
                      style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
                    ),
            ),
          ),
        ],
      ),
    );
  }
}
