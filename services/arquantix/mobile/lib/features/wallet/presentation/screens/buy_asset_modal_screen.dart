import 'dart:async';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

import '../../../../core/currency_preference.dart';
import '../../../../design_system/design_system.dart';
import '../../data/cash_api.dart';
import '../../data/exchange_api.dart';
import '../trading_flow_session_guard.dart';

// ── Confirm-button phases ─────────────────────────────────────

enum _ConfirmPhase { idle, refreshingPrice, executing }

/// Full-screen modal for buying a crypto asset.
///
/// Wired to the real exchange engine (JWT → client portfolio, plus de « current test ») :
/// - Loads EUR balance from le BFF cash
/// - Preview / exécution buy via `/api/mobile/flutter/exchange/buy*`
/// - Shows a premium success overlay before closing
class BuyAssetModalScreen extends StatefulWidget {
  const BuyAssetModalScreen({
    super.key,
    required this.assetSymbol,
    required this.assetName,
    this.assetLogoUrl,
    this.unitPrice,
  });

  final String assetSymbol;
  final String assetName;
  final String? assetLogoUrl;
  final double? unitPrice;

  static Future<bool?> show(
    BuildContext context, {
    required String assetSymbol,
    required String assetName,
    String? assetLogoUrl,
    double? unitPrice,
  }) async {
    if (!await TradingFlowSessionGuard.ensureSessionOrPrompt(context)) {
      return null;
    }
    if (!context.mounted) return null;
    return Navigator.of(context).push<bool>(
      PageRouteBuilder<bool>(
        opaque: true,
        pageBuilder: (_, __, ___) => BuyAssetModalScreen(
          assetSymbol: assetSymbol,
          assetName: assetName,
          assetLogoUrl: assetLogoUrl,
          unitPrice: unitPrice,
        ),
        transitionsBuilder: (_, animation, __, child) {
          final curved = CurvedAnimation(
            parent: animation,
            curve: Curves.easeOutCubic,
            reverseCurve: Curves.easeInCubic,
          );
          return SlideTransition(
            position: Tween<Offset>(
              begin: const Offset(0, 1),
              end: Offset.zero,
            ).animate(curved),
            child: child,
          );
        },
        transitionDuration: const Duration(milliseconds: 300),
        reverseTransitionDuration: const Duration(milliseconds: 250),
      ),
    );
  }

  @override
  State<BuyAssetModalScreen> createState() => _BuyAssetModalScreenState();
}

class _BuyAssetModalScreenState extends State<BuyAssetModalScreen> {
  final TextEditingController _amountCtrl = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  final CashApi _cashApi = const CashApi();
  final ExchangeApi _exchangeApi = const ExchangeApi();

  double _parsedAmount = 0;
  double _eurBalance = 0;
  bool _balanceLoaded = false;

  BuyPreviewResult? _preview;
  bool _previewLoading = false;
  String? _previewError;
  Timer? _debounceTimer;
  DateTime? _previewReceivedAt;

  _ConfirmPhase _confirmPhase = _ConfirmPhase.idle;
  String? _buyError;

  static const _previewMaxAge = Duration(seconds: 3);

  static final _fiatFormatterEur = NumberFormat.currency(
    locale: 'fr_FR', symbol: '€', decimalDigits: 2,
  );
  static final _fiatFormatterUsd = NumberFormat.currency(
    locale: 'en_US', symbol: '\$', decimalDigits: 2,
  );

  NumberFormat get _fiatFormatter =>
      CurrencyPreference.instance.currency == ReferenceCurrency.usd
          ? _fiatFormatterUsd
          : _fiatFormatterEur;

  String get _currencySymbol => CurrencyPreference.instance.currency.symbol;

  @override
  void initState() {
    super.initState();
    _amountCtrl.addListener(_onAmountChanged);
    _loadBalance();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final route = ModalRoute.of(context);
      final animation = route?.animation;
      if (animation != null && !animation.isCompleted) {
        late void Function(AnimationStatus) listener;
        listener = (status) {
          if (status == AnimationStatus.completed) {
            animation.removeStatusListener(listener);
            if (mounted) _openKeyboard();
          }
        };
        animation.addStatusListener(listener);
      } else {
        _openKeyboard();
      }
    });
  }

  void _openKeyboard() {
    _focusNode.requestFocus();
    Future.delayed(const Duration(milliseconds: 50), () {
      if (mounted) SystemChannels.textInput.invokeMethod('TextInput.show');
    });
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    _amountCtrl.removeListener(_onAmountChanged);
    _amountCtrl.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  // ── Balance EUR ──────────────────────────────────────────────

  Future<void> _loadBalance() async {
    try {
      final data = await _cashApi.fetchCashData();
      if (!mounted) return;
      setState(() {
        _eurBalance = data.cashAccount?.availableBalance ?? 0;
        _balanceLoaded = true;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _balanceLoaded = true);
    }
  }

  // ── Amount input ─────────────────────────────────────────────

  void _onAmountChanged() {
    final raw = _amountCtrl.text.replaceAll(',', '.').replaceAll(' ', '');
    final parsed = double.tryParse(raw) ?? 0;
    if (parsed != _parsedAmount) {
      setState(() {
        _parsedAmount = parsed;
        _buyError = null;
      });
      _schedulePreview();
    }
  }

  void _schedulePreview() {
    _debounceTimer?.cancel();
    if (_parsedAmount <= 0) {
      setState(() {
        _preview = null;
        _previewError = null;
        _previewLoading = false;
        _previewReceivedAt = null;
      });
      return;
    }
    setState(() => _previewLoading = true);
    _debounceTimer = Timer(const Duration(milliseconds: 500), _fetchPreview);
  }

  Future<void> _fetchPreview() async {
    final amount = _parsedAmount;
    if (amount <= 0) return;
    try {
      final result = await _exchangeApi.previewBuy(
        asset: widget.assetSymbol,
        amountFiat: amount,
      );
      if (!mounted || _parsedAmount != amount) return;
      setState(() {
        if (result.hasError) {
          _previewError = _humanError(result.error ?? '');
          _preview = null;
          _previewReceivedAt = null;
        } else {
          _preview = result;
          _previewError = null;
          _previewReceivedAt = DateTime.now();
        }
        _previewLoading = false;
      });
    } catch (e) {
      if (!mounted || _parsedAmount != amount) return;
      setState(() {
        _previewError = 'Impossible de charger la preview';
        _preview = null;
        _previewLoading = false;
        _previewReceivedAt = null;
      });
    }
  }

  // ── Preview freshness ────────────────────────────────────────

  bool get _isPreviewFresh {
    if (_preview == null || _previewReceivedAt == null) return false;
    return DateTime.now().difference(_previewReceivedAt!) < _previewMaxAge;
  }

  // ── Validation ───────────────────────────────────────────────

  bool get _isValid =>
      _parsedAmount > 0 &&
      _balanceLoaded &&
      (_eurBalance <= 0 || _parsedAmount <= _eurBalance) &&
      _preview != null &&
      !_preview!.hasError &&
      _confirmPhase == _ConfirmPhase.idle;

  bool get _isOverBalance =>
      _balanceLoaded && _eurBalance > 0 && _parsedAmount > _eurBalance;

  // ── Buy execution with freshness guard ───────────────────────

  Future<void> _onConfirm() async {
    if (!_isValid || _confirmPhase != _ConfirmPhase.idle) return;

    setState(() => _buyError = null);

    if (!_isPreviewFresh) {
      setState(() => _confirmPhase = _ConfirmPhase.refreshingPrice);
      try {
        final result = await _exchangeApi.previewBuy(
          asset: widget.assetSymbol,
          amountFiat: _parsedAmount,
        );
        if (!mounted) return;
        if (result.hasError) {
          setState(() {
            _confirmPhase = _ConfirmPhase.idle;
            _buyError = _humanError(result.error ?? '');
          });
          return;
        }
        setState(() {
          _preview = result;
          _previewReceivedAt = DateTime.now();
        });
      } catch (e) {
        if (!mounted) return;
        setState(() {
          _confirmPhase = _ConfirmPhase.idle;
          _buyError = 'Impossible d\'actualiser le prix';
        });
        return;
      }
    }

    setState(() => _confirmPhase = _ConfirmPhase.executing);

    try {
      final result = await _exchangeApi.executeBuy(
        asset: widget.assetSymbol,
        amountFiat: _parsedAmount,
      );
      if (!mounted) return;

      if (result.isSuccess) {
        await _showSuccessOverlay(result);
        return;
      }

      setState(() {
        _confirmPhase = _ConfirmPhase.idle;
        _buyError = _humanError(result.errorCode ?? 'unknown_error');
      });
    } on ExchangeApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _confirmPhase = _ConfirmPhase.idle;
        _buyError = _humanError(e.errorCode ?? e.message);
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _confirmPhase = _ConfirmPhase.idle;
        _buyError = _humanError(e.toString());
      });
    }
  }

  // ── Success overlay ──────────────────────────────────────────

  Future<void> _showSuccessOverlay(BuyResult result) async {
    _focusNode.unfocus();
    await showGeneralDialog(
      context: context,
      barrierDismissible: false,
      barrierColor: Colors.transparent,
      transitionDuration: const Duration(milliseconds: 250),
      transitionBuilder: (_, anim, __, child) {
        return FadeTransition(
          opacity: CurvedAnimation(parent: anim, curve: Curves.easeOut),
          child: ScaleTransition(
            scale: Tween<double>(begin: 0.92, end: 1.0).animate(
              CurvedAnimation(parent: anim, curve: Curves.easeOutBack),
            ),
            child: child,
          ),
        );
      },
      pageBuilder: (ctx, _, __) {
        return _BuySuccessOverlay(
          assetSymbol: widget.assetSymbol,
          amountCrypto: result.amountCrypto ?? 0,
          amountFiat: result.amountFiat ?? _parsedAmount,
          feeAmount: result.feeAmount,
          feeAsset: result.feeAsset ?? widget.assetSymbol,
          currencySymbol: _currencySymbol,
          fiatFormatter: _fiatFormatter,
        );
      },
    );

    if (mounted) Navigator.of(context).pop(true);
  }

  String _humanError(String code) {
    final lc = code.toLowerCase();
    if (lc.contains('insufficient_funds')) return 'Solde insuffisant';
    if (lc.contains('market_quote_stale')) return 'Prix du marché expiré';
    if (lc.contains('market_quote_unavailable') ||
        lc.contains('price_unavailable') ||
        lc.contains('fx_unavailable')) return 'Prix indisponible';
    if (lc.contains('unsupported_asset')) return 'Asset non supporté';
    if (lc.contains('duplicate')) return 'Ordre déjà traité';
    if (lc.contains('account_not_found')) return 'Compte introuvable';
    return 'Erreur lors de l\'achat';
  }

  // ── Display helpers ──────────────────────────────────────────

  String get _displayAmount {
    if (_amountCtrl.text.isEmpty) return '0';
    final raw = _amountCtrl.text;
    final parts = raw.split(RegExp(r'[.,]'));
    final intPart = parts[0];
    final formatted = _formatIntegerPart(intPart);
    if (parts.length > 1) return '$formatted,${parts[1]}';
    if (raw.endsWith(',') || raw.endsWith('.')) return '$formatted,';
    return formatted;
  }

  String _formatIntegerPart(String digits) {
    if (digits.isEmpty) return '0';
    final n = int.tryParse(digits);
    if (n == null) return digits;
    return NumberFormat('#,###', 'fr_FR').format(n);
  }

  String _formatCryptoAmount(double amount) {
    if (amount < 0.0001) return amount.toStringAsExponential(2);
    String formatted;
    if (amount < 1) {
      formatted = amount.toStringAsFixed(8);
    } else {
      formatted = amount.toStringAsFixed(6);
    }
    if (formatted.contains('.')) {
      formatted = formatted.replaceAll(RegExp(r'0+$'), '');
      formatted = formatted.replaceAll(RegExp(r'\.$'), '');
    }
    return formatted;
  }

  String get _confirmLabel {
    switch (_confirmPhase) {
      case _ConfirmPhase.refreshingPrice:
        return 'Vérification du prix…';
      case _ConfirmPhase.executing:
        return 'Exécution…';
      case _ConfirmPhase.idle:
        return 'Confirmer';
    }
  }

  // ── Build ────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      resizeToAvoidBottomInset: true,
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
              child: _buildSourceAccount(),
            ),
            const SizedBox(height: 20),
            Expanded(
              child: GestureDetector(
                onTap: _openKeyboard,
                behavior: HitTestBehavior.opaque,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
                  child: Column(
                    children: [
                      _buildQuestionText(),
                      const SizedBox(height: 32),
                      _buildAmountDisplay(),
                      const SizedBox(height: 8),
                      _buildCryptoEquivalent(),
                      if (_previewError != null || _buyError != null) ...[
                        const SizedBox(height: 12),
                        _buildErrorBanner(),
                      ],
                      const Spacer(),
                    ],
                  ),
                ),
              ),
            ),
            _buildBottomBar(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    final brandColor =
        AppColors.cryptoAssetBrand[widget.assetSymbol] ?? AppColors.textSecondary;
    final resolvedLogo = widget.assetLogoUrl;

    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg, vertical: AppSpacing.sm,
      ),
      child: SizedBox(
        height: kToolbarHeight,
        child: Row(
          children: [
            _HeaderDisk(
              onTap: () => Navigator.of(context).pop(false),
              child: const Icon(Icons.close_rounded, size: 20, color: AppColors.textPrimary),
            ),
            const Spacer(),
            Text(
              'Acheter',
              style: AppTypography.titleMedium.copyWith(
                color: AppColors.textPrimary, fontWeight: FontWeight.w600,
              ),
            ),
            const Spacer(),
            Container(
              width: 36, height: 36,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: brandColor.withValues(alpha: 0.12),
              ),
              clipBehavior: Clip.antiAlias,
              child: resolvedLogo != null
                  ? Image.network(
                      resolvedLogo, fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Center(
                        child: Text(widget.assetSymbol.substring(0, 1),
                          style: AppTypography.titleSmall.copyWith(
                            color: brandColor, fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    )
                  : Center(
                      child: Text(widget.assetSymbol.substring(0, 1),
                        style: AppTypography.titleSmall.copyWith(
                          color: brandColor, fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuestionText() {
    return Text(
      'Combien souhaitez-vous acheter\nde ${widget.assetName} ?',
      textAlign: TextAlign.center,
      style: AppTypography.titleLarge.copyWith(
        color: AppColors.textPrimary,
        fontWeight: FontWeight.w700,
        height: 1.35,
      ),
    );
  }

  Widget _buildAmountDisplay() {
    return GestureDetector(
      onTap: _openKeyboard,
      behavior: HitTestBehavior.opaque,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Flexible(
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Text(
                    _displayAmount,
                    style: AppTypography.heroAmount.copyWith(
                      color: _isOverBalance
                          ? const Color(0xFFDC2626)
                          : AppColors.textPrimary,
                      fontSize: 48, fontWeight: FontWeight.w700,
                      letterSpacing: -1.0,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 6),
              Text(
                _currencySymbol,
                style: AppTypography.heroAmount.copyWith(
                  color: AppColors.textSecondary,
                  fontSize: 32, fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
          Positioned.fill(
            child: TextField(
              controller: _amountCtrl,
              focusNode: _focusNode,
              autofocus: true,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              inputFormatters: [
                FilteringTextInputFormatter.allow(RegExp(r'[\d,.]')),
                _SingleDecimalFormatter(),
              ],
              decoration: const InputDecoration(
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                disabledBorder: InputBorder.none,
                errorBorder: InputBorder.none,
                focusedErrorBorder: InputBorder.none,
                filled: false,
                contentPadding: EdgeInsets.zero,
                isDense: true,
                isCollapsed: true,
              ),
              style: const TextStyle(fontSize: 1, color: Colors.transparent),
              cursorColor: Colors.transparent,
              cursorWidth: 0,
              maxLines: 1,
              showCursor: false,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCryptoEquivalent() {
    if (_previewLoading && _preview == null) {
      return Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(
            width: 14, height: 14,
            child: CircularProgressIndicator(
              strokeWidth: 1.5,
              color: AppColors.textSecondary.withValues(alpha: 0.5),
            ),
          ),
          const SizedBox(width: 8),
          Text('Estimation...', style: AppTypography.bodyMedium.copyWith(
            color: AppColors.textSecondary,
          )),
        ],
      );
    }

    if (_preview != null && !_preview!.hasError) {
      final net = _formatCryptoAmount(_preview!.estimatedCryptoNet);
      final feeLabel = _preview!.feeAmount > 0
          ? ' (frais ${_formatCryptoAmount(_preview!.feeAmount)} ${_preview!.feeAsset})'
          : '';
      return Column(
        children: [
          Text(
            '≈ $net ${widget.assetSymbol}',
            style: AppTypography.bodyMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          if (feeLabel.isNotEmpty)
            Text(feeLabel,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.textSecondary.withValues(alpha: 0.7),
                fontSize: 11,
              ),
            ),
        ],
      );
    }

    if (_previewError != null) {
      return Text(
        'Prix indisponible',
        style: AppTypography.bodyMedium.copyWith(
          color: AppColors.textSecondary.withValues(alpha: 0.7),
        ),
      );
    }

    return Text(
      '0 ${widget.assetSymbol}',
      style: AppTypography.bodyMedium.copyWith(
        color: AppColors.textSecondary,
      ),
    );
  }

  Widget _buildErrorBanner() {
    final msg = _buyError ?? _previewError ?? '';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.errorBackground,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          const Icon(Icons.warning_amber_rounded, size: 18, color: AppColors.errorText),
          const SizedBox(width: 8),
          Expanded(
            child: Text(msg, style: AppTypography.bodySmall.copyWith(
              color: AppColors.errorText,
            )),
          ),
        ],
      ),
    );
  }

  Widget _buildSourceAccount() {
    final balanceLabel = _balanceLoaded
        ? _fiatFormatter.format(_eurBalance)
        : '—';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(14),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 36, height: 36,
            decoration: const BoxDecoration(
              shape: BoxShape.circle,
              color: Colors.blue,
            ),
            alignment: Alignment.center,
            child: const Icon(Icons.euro_rounded, size: 20, color: Colors.white),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text('Compte Euro', style: AppTypography.bodyMedium.copyWith(
              color: AppColors.textPrimary, fontWeight: FontWeight.w600,
            )),
          ),
          Text(balanceLabel, style: AppTypography.bodyMedium.copyWith(
            color: AppColors.textSecondary,
          )),
        ],
      ),
    );
  }

  Widget _buildBottomBar() {
    final enabled = _isValid;
    final isWorking = _confirmPhase != _ConfirmPhase.idle;

    return Container(
      padding: EdgeInsets.only(
        left: AppSpacing.lg, right: AppSpacing.lg,
        bottom: MediaQuery.of(context).viewPadding.bottom > 0 ? 8 : 16,
        top: 12,
      ),
      decoration: BoxDecoration(
        color: AppColors.pageBackground,
        border: Border(
          top: BorderSide(color: AppColors.textPrimary.withValues(alpha: 0.06)),
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 48, height: 48,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.cardBackground,
              boxShadow: [
                BoxShadow(
                  color: AppColors.textPrimary.withValues(alpha: 0.06),
                  blurRadius: 6, offset: const Offset(0, 2),
                ),
              ],
            ),
            alignment: Alignment.center,
            child: Icon(Icons.info_outline_rounded,
              size: 22, color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: SizedBox(
              height: 52,
              child: ElevatedButton(
                onPressed: (enabled || isWorking) && !isWorking
                    ? _onConfirm
                    : null,
                style: ElevatedButton.styleFrom(
                  backgroundColor: (enabled || isWorking)
                      ? AppColors.indigo
                      : AppColors.textSecondary.withValues(alpha: 0.15),
                  foregroundColor: Colors.white,
                  disabledBackgroundColor: isWorking
                      ? AppColors.indigo
                      : AppColors.textSecondary.withValues(alpha: 0.15),
                  disabledForegroundColor: isWorking
                      ? Colors.white
                      : AppColors.textSecondary.withValues(alpha: 0.4),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                  elevation: (enabled || isWorking) ? 4 : 0,
                  shadowColor: (enabled || isWorking)
                      ? AppColors.indigo.withValues(alpha: 0.35)
                      : Colors.transparent,
                ),
                child: isWorking
                    ? Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const SizedBox(
                            width: 18, height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Text(_confirmLabel,
                            style: AppTypography.bodyMedium.copyWith(
                              color: Colors.white, fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      )
                    : Text(_confirmLabel,
                        style: AppTypography.titleMedium.copyWith(
                          color: enabled
                              ? Colors.white
                              : AppColors.textSecondary.withValues(alpha: 0.5),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Success overlay ──────────────────────────────────────────────

class _BuySuccessOverlay extends StatefulWidget {
  const _BuySuccessOverlay({
    required this.assetSymbol,
    required this.amountCrypto,
    required this.amountFiat,
    required this.feeAmount,
    required this.feeAsset,
    required this.currencySymbol,
    required this.fiatFormatter,
  });

  final String assetSymbol;
  final double amountCrypto;
  final double amountFiat;
  final double? feeAmount;
  final String feeAsset;
  final String currencySymbol;
  final NumberFormat fiatFormatter;

  @override
  State<_BuySuccessOverlay> createState() => _BuySuccessOverlayState();
}

class _BuySuccessOverlayState extends State<_BuySuccessOverlay> {
  @override
  void initState() {
    super.initState();
    Future.delayed(const Duration(milliseconds: 1500), () {
      if (mounted) Navigator.of(context).pop();
    });
  }

  String _formatCrypto(double v) {
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

  @override
  Widget build(BuildContext context) {
    const emerald = Color(0xFF059669);
    final cryptoText = '+${_formatCrypto(widget.amountCrypto)} ${widget.assetSymbol}';
    final fiatText = '≈ ${widget.fiatFormatter.format(widget.amountFiat)}';

    return Material(
      color: Colors.transparent,
      child: Stack(
        children: [
          Positioned.fill(
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
              child: Container(color: Colors.black.withValues(alpha: 0.45)),
            ),
          ),
          Center(
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 40),
              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 36),
              decoration: BoxDecoration(
                color: AppColors.pageBackground,
                borderRadius: BorderRadius.circular(24),
                boxShadow: [
                  BoxShadow(
                    color: emerald.withValues(alpha: 0.15),
                    blurRadius: 40,
                    spreadRadius: 4,
                  ),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 56, height: 56,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: emerald.withValues(alpha: 0.12),
                    ),
                    alignment: Alignment.center,
                    child: const Icon(
                      Icons.check_rounded, size: 32, color: emerald,
                    ),
                  ),
                  const SizedBox(height: 20),
                  Text(
                    'Achat exécuté',
                    style: AppTypography.titleMedium.copyWith(
                      color: AppColors.textPrimary,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    cryptoText,
                    style: AppTypography.heroAmount.copyWith(
                      color: emerald,
                      fontSize: 28,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    fiatText,
                    style: AppTypography.bodyMedium.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                  if (widget.feeAmount != null && widget.feeAmount! > 0) ...[
                    const SizedBox(height: 12),
                    Text(
                      'Frais : ${_formatCrypto(widget.feeAmount!)} ${widget.feeAsset}',
                      style: AppTypography.bodySmall.copyWith(
                        color: AppColors.textSecondary.withValues(alpha: 0.7),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Private helpers ────────────────────────────────────────────

class _HeaderDisk extends StatelessWidget {
  const _HeaderDisk({required this.onTap, required this.child});
  final VoidCallback onTap;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        customBorder: const CircleBorder(),
        child: Container(
          width: 36, height: 36,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: AppColors.cardBackground,
            boxShadow: [
              BoxShadow(
                color: AppColors.textPrimary.withValues(alpha: 0.12),
                blurRadius: 8, offset: const Offset(0, 2),
              ),
            ],
          ),
          alignment: Alignment.center,
          child: child,
        ),
      ),
    );
  }
}

class _SingleDecimalFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue, TextEditingValue newValue,
  ) {
    final text = newValue.text;
    if (text.isEmpty) return newValue;

    var normalized = text.replaceAll('.', ',');
    final commaCount = ','.allMatches(normalized).length;
    if (commaCount > 1) return oldValue;

    if (normalized.contains(',')) {
      final parts = normalized.split(',');
      if (parts.length > 1 && parts[1].length > 2) return oldValue;
    }

    if (normalized.length > 1 &&
        normalized.startsWith('0') &&
        !normalized.startsWith('0,')) {
      normalized = normalized.replaceFirst(RegExp(r'^0+'), '');
      if (normalized.isEmpty || normalized.startsWith(',')) {
        normalized = '0$normalized';
      }
    }

    if (normalized == text) return newValue;
    return TextEditingValue(
      text: normalized,
      selection: TextSelection.collapsed(offset: normalized.length),
    );
  }
}
