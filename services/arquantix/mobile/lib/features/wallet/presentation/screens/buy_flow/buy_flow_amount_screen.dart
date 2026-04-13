import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

import '../../../../../core/config.dart' as app_config;
import '../../../../../core/currency_preference.dart';
import '../../../../../design_system/design_system.dart';
import '../../../data/exchange_api.dart';
import 'buy_flow_controller.dart';
import 'buy_flow_confirmation_screen.dart';

/// STEP 2 — Amount entry.
///
/// The user enters how much they want to invest (fiat amount).
/// A live backend preview shows the estimated crypto received.
/// Tapping "Continuer" navigates to the confirmation screen (step 3).
///
/// Header mirrors the confirmation page layout:
/// CryptoExchangeWidget → headline → editable amount → crypto equivalent.
class BuyFlowAmountScreen extends StatefulWidget {
  const BuyFlowAmountScreen({
    super.key,
    required this.assetSymbol,
    required this.assetName,
    this.assetLogoUrl,
    required this.sourceAccount,
  });

  final String assetSymbol;
  final String assetName;
  final String? assetLogoUrl;
  final BuyFlowSourceAccount sourceAccount;

  @override
  State<BuyFlowAmountScreen> createState() => _BuyFlowAmountScreenState();
}

class _BuyFlowAmountScreenState extends State<BuyFlowAmountScreen> {
  final TextEditingController _amountCtrl = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  final ExchangeApi _exchangeApi = const ExchangeApi();

  double _parsedAmount = 0;
  BuyPreviewResult? _preview;
  bool _previewLoading = false;
  String? _previewError;
  Timer? _debounceTimer;

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

  double get _sourceBalance => widget.sourceAccount.balance;

  bool get _isOverBalance => _parsedAmount > _sourceBalance && _sourceBalance > 0;

  bool get _canContinue =>
      _parsedAmount > 0 &&
      !_isOverBalance &&
      _preview != null &&
      !_preview!.hasError &&
      !_previewLoading;

  @override
  void initState() {
    super.initState();
    _amountCtrl.addListener(_onAmountChanged);
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

  void _onAmountChanged() {
    final raw = _amountCtrl.text.replaceAll(',', '.').replaceAll(' ', '');
    final parsed = double.tryParse(raw) ?? 0;
    if (parsed != _parsedAmount) {
      setState(() {
        _parsedAmount = parsed;
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
          _previewError = result.error;
          _preview = null;
        } else {
          _preview = result;
          _previewError = null;
        }
        _previewLoading = false;
      });
    } catch (e) {
      if (!mounted || _parsedAmount != amount) return;
      setState(() {
        _previewError = 'Impossible de charger l\'estimation';
        _preview = null;
        _previewLoading = false;
      });
    }
  }

  void _goToConfirmation() {
    if (!_canContinue || _preview == null) return;
    _focusNode.unfocus();
    Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => BuyFlowConfirmationScreen(
          assetSymbol: widget.assetSymbol,
          assetName: widget.assetName,
          assetLogoUrl: widget.assetLogoUrl,
          sourceAccount: widget.sourceAccount,
          amountFiat: _parsedAmount,
          preview: _preview!,
        ),
      ),
    ).then((didBuy) {
      if (didBuy == true && mounted) {
        Navigator.of(context).pop(true);
      }
    });
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

  // ── Logo resolution ──────────────────────────────────────────

  String? get _resolvedTargetLogo {
    if (widget.assetLogoUrl != null && widget.assetLogoUrl!.isNotEmpty) {
      return widget.assetLogoUrl;
    }
    final slug = widget.assetSymbol.trim().toLowerCase();
    if (slug.isEmpty) return null;
    return app_config.Config.resolveLogoUrl('/media/crypto_logos/$slug.png');
  }

  String? get _resolvedSourceLogo {
    if (widget.sourceAccount.logoUrl != null &&
        widget.sourceAccount.logoUrl!.isNotEmpty) {
      return widget.sourceAccount.logoUrl;
    }
    final slug = widget.sourceAccount.currency.trim().toLowerCase();
    if (slug.isEmpty || slug == 'eur') return null;
    return app_config.Config.resolveLogoUrl('/media/crypto_logos/$slug.png');
  }

  // ── Build ──────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      resizeToAvoidBottomInset: true,
      body: SafeArea(
        child: Column(
          children: [
            _buildNavBar(),
            Expanded(
              child: GestureDetector(
                onTap: _openKeyboard,
                behavior: HitTestBehavior.opaque,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
                  child: Column(
                    children: [
                      const SizedBox(height: 24),
                      _buildExchangeDirection(),
                      const SizedBox(height: 20),
                      _buildHeadline(),
                      const SizedBox(height: 8),
                      _buildAmountDisplay(),
                      const SizedBox(height: AppSpacing.xs),
                      _buildCryptoEquivalent(),
                      if (_previewError != null) ...[
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

  Widget _buildNavBar() {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.sm,
      ),
      child: SizedBox(
        height: kToolbarHeight,
        child: Row(
          children: [
            _BackDisk(onTap: () => Navigator.of(context).pop()),
            const Spacer(),
            Text(
              'Montant',
              style: AppTypography.titleMedium.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w600,
              ),
            ),
            const Spacer(),
            const SizedBox(width: 36),
          ],
        ),
      ),
    );
  }

  Widget _buildExchangeDirection() {
    return CryptoExchangeWidget(
      fromTicker: widget.sourceAccount.currency,
      toTicker: widget.assetSymbol,
      fromLogoUrl: _resolvedSourceLogo,
      toLogoUrl: _resolvedTargetLogo,
      fromIcon: widget.sourceAccount.icon,
    );
  }

  Widget _buildHeadline() {
    return Text(
      'Vous êtes sur le point d\'acheter',
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
                    '$_displayAmount $_currencySymbol',
                    style: GoogleFonts.inter(
                      fontSize: 34,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.136,
                      height: 41 / 34,
                      color: _isOverBalance
                          ? const Color(0xFFDC2626)
                          : AppColors.textPrimary,
                    ),
                  ),
                ),
              ),
            ],
          ),
          Positioned.fill(
            child: TextField(
              controller: _amountCtrl,
              focusNode: _focusNode,
              autofocus: true,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
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
            width: 14,
            height: 14,
            child: CircularProgressIndicator(
              strokeWidth: 1.5,
              color: AppColors.textSecondary.withValues(alpha: 0.5),
            ),
          ),
          const SizedBox(width: 8),
          Text(
            'Estimation...',
            style: GoogleFonts.inter(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              height: 16 / 14,
              color: AppColors.textPrimary,
            ),
          ),
        ],
      );
    }

    if (_preview != null && !_preview!.hasError) {
      final net = _formatCryptoAmount(_preview!.estimatedCryptoNet);
      return Text(
        '≈ $net ${widget.assetSymbol}',
        style: GoogleFonts.inter(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          height: 16 / 14,
          color: AppColors.textPrimary,
        ),
      );
    }

    if (_previewError != null) {
      return Text(
        'Prix indisponible',
        style: GoogleFonts.inter(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          height: 16 / 14,
          color: AppColors.gray,
        ),
      );
    }

    return Text(
      '≈ 0 ${widget.assetSymbol}',
      style: GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        height: 16 / 14,
        color: AppColors.gray,
      ),
    );
  }

  Widget _buildErrorBanner() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.errorBackground,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          const Icon(Icons.warning_amber_rounded,
              size: 18, color: AppColors.errorText),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              _previewError ?? '',
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.errorText,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBottomBar() {
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            AppColors.pageBackground.withValues(alpha: 0.0),
            AppColors.pageBackground.withValues(alpha: 0.3),
            AppColors.pageBackground.withValues(alpha: 1.0),
          ],
          stops: const [0.0, 0.15, 1.0],
        ),
      ),
      child: Padding(
        padding: EdgeInsets.only(
          left: AppSpacing.lg,
          right: AppSpacing.lg,
          bottom: MediaQuery.of(context).viewPadding.bottom > 0 ? 8 : 16,
          top: 20,
        ),
        child: SizedBox(
          height: 52,
          width: double.infinity,
          child: FilledButton(
            onPressed: _canContinue ? _goToConfirmation : null,
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.indigo,
              foregroundColor: Colors.white,
              disabledBackgroundColor:
                  AppColors.textSecondary.withValues(alpha: 0.15),
              disabledForegroundColor:
                  AppColors.textSecondary.withValues(alpha: 0.4),
              shape: const StadiumBorder(),
              elevation: _canContinue ? 4 : 0,
              shadowColor: _canContinue
                  ? AppColors.indigo.withValues(alpha: 0.35)
                  : Colors.transparent,
            ),
            child: Text(
              'Continuer',
              style: AppTypography.titleMedium.copyWith(
                color: _canContinue
                    ? Colors.white
                    : AppColors.textSecondary.withValues(alpha: 0.5),
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _BackDisk extends StatelessWidget {
  const _BackDisk({required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        customBorder: const CircleBorder(),
        child: Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: AppColors.cardBackground,
            boxShadow: [
              BoxShadow(
                color: AppColors.textPrimary.withValues(alpha: 0.06),
                blurRadius: 4,
                offset: const Offset(0, 1),
              ),
            ],
          ),
          alignment: Alignment.center,
          child: const Icon(Icons.arrow_back_rounded,
              size: 20, color: AppColors.textPrimary),
        ),
      ),
    );
  }
}

class _SingleDecimalFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
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
