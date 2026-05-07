import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

import '../../../../../core/currency_preference.dart';
import '../../../../../design_system/design_system.dart';
import '../../../data/bundle_api.dart';
import 'bundle_invest_flow_controller.dart';
import 'bundle_confirmation_screen.dart';

/// STEP 2 — Amount entry for bundle investment.
class BundleAmountEntryScreen extends StatefulWidget {
  const BundleAmountEntryScreen({
    super.key,
    required this.bundle,
    required this.sourceAccount,
    /// Montant initial (optionnel) — ex. deep-link depuis l'assistant.
    this.prefillAmount,
  });

  final BundleItem bundle;
  final BundleSourceAccount sourceAccount;
  final double? prefillAmount;

  @override
  State<BundleAmountEntryScreen> createState() =>
      _BundleAmountEntryScreenState();
}

class _BundleAmountEntryScreenState extends State<BundleAmountEntryScreen> {
  final TextEditingController _amountCtrl = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  final BundleApi _bundleApi = const BundleApi();

  double _parsedAmount = 0;
  Timer? _debounce;
  BundleInvestPreviewResult? _preview;
  bool _previewLoading = false;
  String? _previewError;

  static final _fiatFormatterEur = NumberFormat.currency(
    locale: 'fr_FR',
    symbol: '€',
    decimalDigits: 2,
  );
  static final _fiatFormatterUsd = NumberFormat.currency(
    locale: 'en_US',
    symbol: '\$',
    decimalDigits: 2,
  );

  NumberFormat get _fiatFormatter =>
      CurrencyPreference.instance.currency == ReferenceCurrency.usd
          ? _fiatFormatterUsd
          : _fiatFormatterEur;

  String get _currencySymbol =>
      widget.sourceAccount.isFiat
          ? CurrencyPreference.instance.currency.symbol
          : widget.sourceAccount.currency;

  String get _fundingAsset =>
      widget.sourceAccount.isFiat ? 'EUR' : widget.sourceAccount.currency;

  double get _sourceBalance => widget.sourceAccount.balance;

  bool get _isOverBalance =>
      _parsedAmount > _sourceBalance && _sourceBalance > 0;

  bool get _canContinue =>
      _parsedAmount > 0 && !_isOverBalance && _preview?.isInvalid != true;

  @override
  void initState() {
    super.initState();
    _amountCtrl.addListener(_onAmountChanged);
    if (widget.prefillAmount != null && widget.prefillAmount! > 0) {
      final a = widget.prefillAmount!;
      final s = a < 1 ? a.toStringAsFixed(8) : a.toStringAsFixed(2);
      _amountCtrl.text = s.replaceAll(RegExp(r'\.?0+$'), '');
      _parsedAmount = double.tryParse(_amountCtrl.text.replaceAll(',', '.')) ?? a;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _schedulePreview(_parsedAmount);
      });
    }
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
    _debounce?.cancel();
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
      _schedulePreview(parsed);
    }
  }

  void _schedulePreview(double amount) {
    _debounce?.cancel();
    if (amount <= 0) {
      setState(() {
        _preview = null;
        _previewLoading = false;
        _previewError = null;
      });
      return;
    }
    setState(() => _previewLoading = true);
    _debounce = Timer(const Duration(milliseconds: 600), () {
      _fetchPreview(amount);
    });
  }

  Future<void> _fetchPreview(double amount) async {
    if (!mounted) return;
    try {
      final result = await _bundleApi.previewBundleInvestment(
        portfolioId: widget.bundle.portfolioId,
        fundingAsset: _fundingAsset,
        fundingAmount: amount,
      );
      if (!mounted) return;
      setState(() {
        _preview = result;
        _previewLoading = false;
        _previewError = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _preview = null;
        _previewLoading = false;
        _previewError = 'Preview indisponible';
      });
    }
  }

  void _goToConfirmation() {
    if (!_canContinue) return;
    _focusNode.unfocus();
    Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => BundleConfirmationScreen(
          bundle: widget.bundle,
          sourceAccount: widget.sourceAccount,
          amount: _parsedAmount,
          preview: _preview,
        ),
      ),
    ).then((result) {
      if (result == true && mounted) {
        Navigator.of(context).pop(true);
      }
    });
  }

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
              child: _buildSourcePill(),
            ),
            const SizedBox(height: 20),
            Expanded(
              child: GestureDetector(
                onTap: _openKeyboard,
                behavior: HitTestBehavior.opaque,
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.lg),
                  child: Column(
                    children: [
                      _buildQuestionText(),
                      const SizedBox(height: 32),
                      _buildAmountDisplay(),
                      const SizedBox(height: 8),
                      _buildEntryAssetNote(),
                      if (_isOverBalance) ...[
                        const SizedBox(height: 12),
                        _buildErrorBanner(
                          'Solde insuffisant (${widget.sourceAccount.isFiat ? _fiatFormatter.format(_sourceBalance) : '${_sourceBalance.toStringAsFixed(2)} ${widget.sourceAccount.currency}'})',
                        ),
                      ],
                      if (_parsedAmount > 0 && !_isOverBalance) ...[
                        const SizedBox(height: 16),
                        _buildPreviewSection(),
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
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.sm,
      ),
      child: SizedBox(
        height: kToolbarHeight,
        child: Row(
          children: [
            BundleFlowHeaderDisk(
              onTap: () => Navigator.of(context).pop(),
              child: const Icon(Icons.arrow_back_rounded,
                  size: 20, color: AppColors.textPrimary),
            ),
            const Spacer(),
            Text(
              'Montant',
              style: AppTypography.titleMedium.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w600,
              ),
            ),
            const Spacer(),
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.indigo.withValues(alpha: 0.12),
              ),
              alignment: Alignment.center,
              child: const Icon(
                Icons.auto_awesome_mosaic_rounded,
                size: 18,
                color: AppColors.indigo,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSourcePill() {
    final src = widget.sourceAccount;
    final balanceLabel = src.isFiat
        ? _fiatFormatter.format(src.balance)
        : '${src.balance.toStringAsFixed(2)} ${src.currency}';

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
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: src.iconBackgroundColor,
            ),
            alignment: Alignment.center,
            child: Icon(src.icon, size: 20, color: Colors.white),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              src.label,
              style: AppTypography.bodyMedium.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Text(
            balanceLabel,
            style: AppTypography.bodyMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuestionText() {
    return Text(
      'Combien souhaitez-vous investir\ndans ${widget.bundle.name} ?',
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
                      fontSize: 48,
                      fontWeight: FontWeight.w700,
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
                  fontSize: 32,
                  fontWeight: FontWeight.w500,
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

  Widget _buildEntryAssetNote() {
    if (_preview != null && _preview!.isUsable && widget.sourceAccount.isFiat) {
      final entryAmount = _preview!.entryAssetAmountDouble;
      final entryAsset = _preview!.entryAssetUsed ?? widget.bundle.entryAssetDefault;
      return Text(
        '≈ ${entryAmount.toStringAsFixed(2)} $entryAsset après conversion',
        style: AppTypography.bodySmall.copyWith(
          color: AppColors.textSecondary,
        ),
      );
    }
    if (widget.sourceAccount.isFiat) {
      return Text(
        'Converti via ${widget.bundle.entryAssetDefault} puis alloué',
        style: AppTypography.bodySmall.copyWith(
          color: AppColors.textSecondary,
        ),
      );
    }
    return Text(
      'Alloué depuis votre wallet ${widget.sourceAccount.currency}',
      style: AppTypography.bodySmall.copyWith(
        color: AppColors.textSecondary,
      ),
    );
  }

  Widget _buildPreviewSection() {
    if (_previewLoading) {
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
            'Estimation en cours…',
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      );
    }

    if (_previewError != null) {
      return _buildInfoBanner(
        icon: Icons.cloud_off_rounded,
        text: _previewError!,
        color: AppColors.textSecondary,
      );
    }

    if (_preview == null) return const SizedBox.shrink();

    if (_preview!.isInvalid) {
      final reason = _preview!.warnings.isNotEmpty
          ? _preview!.warnings.first
          : 'Investissement non disponible';
      return _buildInfoBanner(
        icon: Icons.warning_amber_rounded,
        text: reason,
        color: AppColors.errorText,
        bgColor: AppColors.errorBackground,
      );
    }

    if (_preview!.isPartial) {
      return _buildInfoBanner(
        icon: Icons.info_outline_rounded,
        text: 'Allocation partielle — certains assets indisponibles',
        color: AppColors.indigo,
        bgColor: AppColors.indigo.withValues(alpha: 0.06),
      );
    }

    final remaining = _preview!.remainingDouble;
    if (remaining > 0.01) {
      final entryAsset = _preview!.entryAssetUsed ?? '';
      return _buildInfoBanner(
        icon: Icons.info_outline_rounded,
        text: 'Reliquat estimé : ${remaining.toStringAsFixed(2)} $entryAsset',
        color: AppColors.indigo,
        bgColor: AppColors.indigo.withValues(alpha: 0.06),
      );
    }

    return const SizedBox.shrink();
  }

  Widget _buildInfoBanner({
    required IconData icon,
    required String text,
    required Color color,
    Color? bgColor,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: bgColor ?? color.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: AppTypography.bodySmall.copyWith(
                color: color,
                height: 1.3,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorBanner(String message) {
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
              message,
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
    return Container(
      padding: EdgeInsets.only(
        left: AppSpacing.lg,
        right: AppSpacing.lg,
        bottom: MediaQuery.of(context).viewPadding.bottom > 0 ? 8 : 16,
        top: 12,
      ),
      decoration: BoxDecoration(
        color: AppColors.pageBackground,
        border: Border(
          top: BorderSide(
              color: AppColors.textPrimary.withValues(alpha: 0.06)),
        ),
      ),
      child: SizedBox(
        height: 52,
        width: double.infinity,
        child: ElevatedButton(
          onPressed: _canContinue ? _goToConfirmation : null,
          style: ElevatedButton.styleFrom(
            backgroundColor: _canContinue
                ? AppColors.indigo
                : AppColors.textSecondary.withValues(alpha: 0.15),
            foregroundColor: Colors.white,
            disabledBackgroundColor:
                AppColors.textSecondary.withValues(alpha: 0.15),
            disabledForegroundColor:
                AppColors.textSecondary.withValues(alpha: 0.4),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
            ),
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
