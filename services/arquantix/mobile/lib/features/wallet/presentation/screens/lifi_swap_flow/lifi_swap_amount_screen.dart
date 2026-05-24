import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../../core/config.dart' as app_config;
import '../../../../../design_system/design_system.dart';
import '../../../data/lifi_swap_api.dart';
import 'lifi_swap_confirmation_screen.dart';
import 'lifi_swap_flow_format.dart';

/// Étape 3 — saisie du montant + quote LI.FI live.
class LifiSwapAmountScreen extends StatefulWidget {
  const LifiSwapAmountScreen({
    super.key,
    required this.fromAsset,
    required this.fromAssetName,
    required this.fromChain,
    this.fromLogoUrl,
    required this.toAsset,
    required this.toAssetName,
    required this.toChain,
    required this.sourceBalance,
  });

  final String fromAsset;
  final String fromAssetName;
  final String fromChain;
  final String? fromLogoUrl;
  final String toAsset;
  final String toAssetName;
  final String toChain;
  final double sourceBalance;

  @override
  State<LifiSwapAmountScreen> createState() => _LifiSwapAmountScreenState();
}

class _LifiSwapAmountScreenState extends State<LifiSwapAmountScreen> {
  final _amountCtrl = TextEditingController();
  final _focusNode = FocusNode();
  final _api = const LifiSwapApi();

  double _parsedAmount = 0;
  LifiSwapQuote? _quote;
  bool _quoteLoading = false;
  String? _quoteError;
  Timer? _debounceTimer;

  bool get _isOverBalance =>
      _parsedAmount > widget.sourceBalance && widget.sourceBalance > 0;

  bool get _canContinue =>
      _parsedAmount > 0 && !_isOverBalance && _quote != null && !_quoteLoading;

  @override
  void initState() {
    super.initState();
    _amountCtrl.addListener(_onAmountChanged);
    WidgetsBinding.instance.addPostFrameCallback((_) => _openKeyboard());
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
      setState(() => _parsedAmount = parsed);
      _scheduleQuote();
    }
  }

  void _scheduleQuote() {
    _debounceTimer?.cancel();
    if (_parsedAmount <= 0) {
      setState(() {
        _quote = null;
        _quoteError = null;
        _quoteLoading = false;
      });
      return;
    }
    setState(() => _quoteLoading = true);
    _debounceTimer = Timer(const Duration(milliseconds: 500), _fetchQuote);
  }

  Future<void> _fetchQuote() async {
    final amount = _parsedAmount;
    if (amount <= 0) return;
    try {
      final quote = await _api.requestQuote(
        fromAsset: widget.fromAsset,
        toAsset: widget.toAsset,
        amount: amount.toString(),
        fromChain: widget.fromChain,
        toChain: widget.toChain,
      );
      if (!mounted || _parsedAmount != amount) return;
      setState(() {
        _quote = quote;
        _quoteError = null;
        _quoteLoading = false;
      });
    } catch (e) {
      if (!mounted || _parsedAmount != amount) return;
      setState(() {
        _quoteError = e is LifiSwapApiException ? e.message : 'Estimation impossible';
        _quote = null;
        _quoteLoading = false;
      });
    }
  }

  void _goToConfirmation() {
    if (!_canContinue || _quote == null) return;
    _focusNode.unfocus();
    Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => LifiSwapConfirmationScreen(
          fromAsset: widget.fromAsset,
          fromAssetName: widget.fromAssetName,
          fromChain: widget.fromChain,
          fromLogoUrl: widget.fromLogoUrl,
          toAsset: widget.toAsset,
          toAssetName: widget.toAssetName,
          toChain: widget.toChain,
          amountFrom: _parsedAmount,
          quote: _quote!,
        ),
      ),
    ).then((didSwap) {
      if (didSwap == true && mounted) {
        Navigator.of(context).pop(true);
      }
    });
  }

  String get _displayAmount {
    if (_amountCtrl.text.isEmpty) return '0';
    final raw = _amountCtrl.text;
    final parts = raw.split(RegExp(r'[.,]'));
    final intPart = parts[0];
    if (parts.length > 1) return '$intPart,${parts[1]}';
    if (raw.endsWith(',') || raw.endsWith('.')) return '$intPart,';
    return intPart;
  }

  String? get _resolvedFromLogo {
    if (widget.fromLogoUrl != null && widget.fromLogoUrl!.isNotEmpty) {
      return widget.fromLogoUrl;
    }
    final slug = widget.fromAsset.trim().toLowerCase();
    if (slug.isEmpty) return null;
    return app_config.Config.resolveLogoUrl('/media/crypto_logos/$slug.png');
  }

  String? get _resolvedToLogo {
    final slug = widget.toAsset.trim().toLowerCase();
    if (slug.isEmpty) return null;
    return app_config.Config.resolveLogoUrl('/media/crypto_logos/$slug.png');
  }

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
                      CryptoExchangeWidget(
                        fromTicker: widget.fromAsset,
                        toTicker: widget.toAsset,
                        fromLogoUrl: _resolvedFromLogo,
                        toLogoUrl: _resolvedToLogo,
                      ),
                      const SizedBox(height: 20),
                      Text(
                        'Vous êtes sur le point de convertir',
                        textAlign: TextAlign.center,
                        style: AppTypography.titleLarge.copyWith(
                          color: AppColors.textPrimary,
                          fontWeight: FontWeight.w700,
                          height: 1.35,
                        ),
                      ),
                      const SizedBox(height: 8),
                      _buildAmountDisplay(),
                      const SizedBox(height: AppSpacing.xs),
                      _buildTargetEquivalent(),
                      if (widget.sourceBalance > 0) ...[
                        const SizedBox(height: 8),
                        Text(
                          'Solde disponible : ${LifiSwapFlowFormat.formatCryptoAmount(widget.sourceBalance)} ${widget.fromAsset}',
                          style: AppTypography.meta.copyWith(color: AppColors.textSecondary),
                        ),
                      ],
                      if (_quoteError != null) ...[
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
              'Swap',
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

  Widget _buildAmountDisplay() {
    return GestureDetector(
      onTap: _openKeyboard,
      behavior: HitTestBehavior.opaque,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Text(
            '$_displayAmount ${widget.fromAsset}',
            style: GoogleFonts.inter(
              fontSize: 34,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.136,
              color: _isOverBalance
                  ? const Color(0xFFDC2626)
                  : AppColors.textPrimary,
            ),
          ),
          Positioned.fill(
            child: TextField(
              controller: _amountCtrl,
              focusNode: _focusNode,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              inputFormatters: [
                FilteringTextInputFormatter.allow(RegExp(r'[\d,.]')),
              ],
              decoration: const InputDecoration(
                border: InputBorder.none,
                contentPadding: EdgeInsets.zero,
              ),
              style: const TextStyle(fontSize: 1, color: Colors.transparent),
              cursorColor: Colors.transparent,
              cursorWidth: 0,
              showCursor: false,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTargetEquivalent() {
    if (_quoteLoading && _quote == null) {
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
              color: AppColors.textPrimary,
            ),
          ),
        ],
      );
    }

    if (_quote != null) {
      return Text(
        '≈ ${LifiSwapFlowFormat.formatCryptoString(_quote!.estimatedReceive)} ${widget.toAsset}',
        style: GoogleFonts.inter(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: AppColors.textPrimary,
        ),
      );
    }

    return Text(
      '≈ 0 ${widget.toAsset}',
      style: GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w600,
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
          const Icon(Icons.warning_amber_rounded, size: 18, color: AppColors.errorText),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              _quoteError ?? '',
              style: AppTypography.bodySmall.copyWith(color: AppColors.errorText),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBottomBar() {
    return Padding(
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
            disabledBackgroundColor: AppColors.textSecondary.withValues(alpha: 0.15),
            shape: const StadiumBorder(),
          ),
          child: Text(
            'Continuer',
            style: AppTypography.titleMedium.copyWith(
              fontWeight: FontWeight.w600,
              color: _canContinue ? Colors.white : AppColors.textSecondary.withValues(alpha: 0.5),
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
          child: const Icon(Icons.arrow_back_rounded, size: 20, color: AppColors.textPrimary),
        ),
      ),
    );
  }
}
