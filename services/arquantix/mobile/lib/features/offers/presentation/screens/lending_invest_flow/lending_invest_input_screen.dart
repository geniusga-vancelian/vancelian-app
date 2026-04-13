import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

import '../../../../../design_system/design_system.dart';
import '../../../../wallet/presentation/screens/bundle_invest_flow/bundle_invest_flow_controller.dart';
import '../../../domain/models/offer_project.dart';
import 'lending_invest_preview_screen.dart';

/// STEP 2 — Amount entry for exclusive offer investment.
class LendingInvestInputScreen extends StatefulWidget {
  const LendingInvestInputScreen({
    super.key,
    required this.project,
    required this.sourceAccount,
  });

  final OfferProject project;
  final BundleSourceAccount sourceAccount;

  @override
  State<LendingInvestInputScreen> createState() =>
      _LendingInvestInputScreenState();
}

class _LendingInvestInputScreenState extends State<LendingInvestInputScreen> {
  final _amountCtrl = TextEditingController();
  final _focusNode = FocusNode();
  double _parsedAmount = 0;

  static final _eurFormatter = NumberFormat.currency(
    locale: 'fr_FR',
    symbol: '€',
    decimalDigits: 2,
  );

  String get _poolAsset => widget.project.lendingAsset ?? 'USDC';

  String get _fundingAsset =>
      widget.sourceAccount.isFiat ? 'EUR' : widget.sourceAccount.currency;

  String get _currencySymbol =>
      widget.sourceAccount.isFiat ? '€' : widget.sourceAccount.currency;

  double get _sourceBalance => widget.sourceAccount.balance;

  bool get _isOverBalance =>
      _parsedAmount > _sourceBalance && _sourceBalance > 0;

  bool get _requiresConversion =>
      _fundingAsset.toUpperCase() != _poolAsset.toUpperCase();

  bool get _canContinue => _parsedAmount > 0 && !_isOverBalance;

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
    _amountCtrl.removeListener(_onAmountChanged);
    _amountCtrl.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _onAmountChanged() {
    final raw = _amountCtrl.text.replaceAll(',', '.').replaceAll(' ', '');
    setState(() => _parsedAmount = double.tryParse(raw) ?? 0);
  }

  void _goToPreview() {
    if (!_canContinue) return;
    _focusNode.unfocus();
    Navigator.of(context)
        .push<bool>(
          MaterialPageRoute<bool>(
            builder: (_) => LendingInvestPreviewScreen(
              project: widget.project,
              fundingAsset: _fundingAsset,
              fundingAmount: _parsedAmount,
              sourceAccount: widget.sourceAccount,
            ),
          ),
        )
        .then((result) {
      if (result == true && mounted) Navigator.of(context).pop(true);
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
                  padding:
                      const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
                  child: Column(
                    children: [
                      _buildQuestionText(),
                      const SizedBox(height: 32),
                      _buildAmountDisplay(),
                      const SizedBox(height: 8),
                      _buildEntryAssetNote(),
                      if (_isOverBalance) ...[
                        const SizedBox(height: 12),
                        _buildErrorBanner(),
                      ],
                      if (_parsedAmount > 0 &&
                          !_isOverBalance &&
                          _requiresConversion) ...[
                        const SizedBox(height: 16),
                        _buildConversionInfo(),
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
          horizontal: AppSpacing.lg, vertical: AppSpacing.sm),
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
            Text('Montant',
                style: AppTypography.titleMedium
                    .copyWith(fontWeight: FontWeight.w600)),
            const Spacer(),
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.indigo.withValues(alpha: 0.12),
              ),
              alignment: Alignment.center,
              child: Icon(Icons.savings_rounded,
                  size: 18, color: AppColors.indigo),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSourcePill() {
    final src = widget.sourceAccount;
    final balanceLabel = src.isFiat
        ? _eurFormatter.format(src.balance)
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
            child: src.logoUrl != null
                ? ClipOval(
                    child: Image.network(src.logoUrl!, width: 36, height: 36,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) =>
                            Icon(src.icon, size: 20, color: Colors.white)),
                  )
                : Icon(src.icon, size: 20, color: Colors.white),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              src.label,
              style: AppTypography.bodyMedium.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Text(
            balanceLabel,
            style: AppTypography.bodyMedium
                .copyWith(color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }

  Widget _buildQuestionText() {
    return Text(
      'Combien souhaitez-vous investir\ndans ${widget.project.title} ?',
      textAlign: TextAlign.center,
      style: AppTypography.titleLarge.copyWith(
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
              ],
              decoration: const InputDecoration(
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                filled: false,
                contentPadding: EdgeInsets.zero,
                isDense: true,
                isCollapsed: true,
              ),
              style:
                  const TextStyle(fontSize: 1, color: Colors.transparent),
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
    if (_requiresConversion) {
      return Text(
        'Converti en $_poolAsset puis alloué à l\'offre',
        style: AppTypography.bodySmall
            .copyWith(color: AppColors.textSecondary),
      );
    }
    return Text(
      'Alloué directement depuis votre wallet $_fundingAsset',
      style: AppTypography.bodySmall
          .copyWith(color: AppColors.textSecondary),
    );
  }

  Widget _buildErrorBanner() {
    final balanceLabel = widget.sourceAccount.isFiat
        ? _eurFormatter.format(_sourceBalance)
        : '${_sourceBalance.toStringAsFixed(2)} ${widget.sourceAccount.currency}';

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
              'Solde insuffisant ($balanceLabel)',
              style: AppTypography.bodySmall
                  .copyWith(color: AppColors.errorText),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConversionInfo() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.indigo.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Icon(Icons.swap_horiz_rounded,
              size: 16, color: AppColors.indigo.withValues(alpha: 0.7)),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Conversion $_fundingAsset → $_poolAsset automatique',
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.indigo,
                height: 1.3,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBottomBar() {
    final bottomPadding = MediaQuery.of(context).viewPadding.bottom;
    return Container(
      padding: EdgeInsets.fromLTRB(
        AppSpacing.lg,
        12,
        AppSpacing.lg,
        bottomPadding > 0 ? 8 : 16,
      ),
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
          ),
        ),
      ),
      child: SizedBox(
        height: 52,
        width: double.infinity,
        child: ElevatedButton(
          onPressed: _canContinue ? _goToPreview : null,
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.indigo,
            foregroundColor: Colors.white,
            disabledBackgroundColor:
                AppColors.textSecondary.withValues(alpha: 0.15),
            disabledForegroundColor:
                AppColors.textSecondary.withValues(alpha: 0.4),
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16)),
            elevation: _canContinue ? 4 : 0,
            shadowColor: AppColors.indigo.withValues(alpha: 0.35),
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
