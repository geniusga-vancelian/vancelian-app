import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../../core/currency_formatter.dart';
import '../../../../design_system/design_system.dart';
import '../../data/trigger_orders_api.dart';
import '../../domain/models/trigger_order.dart';

class CreateOrderBottomSheet extends StatefulWidget {
  final String asset;
  final double? currentPrice;

  const CreateOrderBottomSheet({
    super.key,
    required this.asset,
    this.currentPrice,
  });

  static Future<TriggerOrder?> show(
    BuildContext context, {
    required String asset,
    double? currentPrice,
  }) {
    return showModalBottomSheet<TriggerOrder>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.cardBackground,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      builder: (_) => CreateOrderBottomSheet(asset: asset, currentPrice: currentPrice),
    );
  }

  @override
  State<CreateOrderBottomSheet> createState() => _State();
}

class _State extends State<CreateOrderBottomSheet> {
  final _priceController = TextEditingController();
  final _amountController = TextEditingController();
  final _slippageController = TextEditingController();
  final _api = TriggerOrdersApi();

  String _side = 'buy';
  String _orderType = 'limit';
  bool _showSlippage = false;
  bool _loading = false;
  String? _hint;
  bool _buttonPressed = false;

  double? get _currentPrice => widget.currentPrice;

  static const _greenColor = Color(0xFF16A34A);
  static const _redColor = Color(0xFFDC2626);
  static const _buyColor = Color(0xFF16A34A);
  static const _sellColor = Color(0xFFDC2626);

  Color get _sideColor => _side == 'buy' ? _buyColor : _sellColor;

  String get _autoDirection {
    if (_side == 'buy' && _orderType == 'limit') return 'down';
    if (_side == 'buy' && _orderType == 'stop') return 'up';
    if (_side == 'sell' && _orderType == 'limit') return 'up';
    return 'down';
  }

  @override
  void initState() {
    super.initState();
    _priceController.addListener(_onInputChanged);
    _amountController.addListener(_onInputChanged);
  }

  @override
  void dispose() {
    _priceController.dispose();
    _amountController.dispose();
    _slippageController.dispose();
    super.dispose();
  }

  void _onInputChanged() {
    final price = _parseDouble(_priceController.text);
    if (price == null || _currentPrice == null) {
      if (_hint != null) setState(() => _hint = null);
      return;
    }
    String? h;
    final dir = _autoDirection;
    if (dir == 'down' && price >= _currentPrice!) {
      h = 'Le prix doit être inférieur au prix actuel';
    } else if (dir == 'up' && price <= _currentPrice!) {
      h = 'Le prix doit être supérieur au prix actuel';
    }
    if (h != _hint) setState(() => _hint = h);
  }

  double? _parseDouble(String text) {
    final raw = text.replaceAll(',', '.').replaceAll(' ', '');
    return double.tryParse(raw);
  }

  Future<void> _submit() async {
    final price = _parseDouble(_priceController.text);
    final amount = _parseDouble(_amountController.text);

    if (price == null || price <= 0) {
      setState(() => _hint = 'Entrez un prix valide');
      return;
    }
    if (amount == null || amount <= 0) {
      setState(() => _hint = 'Entrez un montant valide');
      return;
    }

    if (_currentPrice != null) {
      final dir = _autoDirection;
      if (dir == 'down' && price >= _currentPrice!) {
        setState(() => _hint = 'Le prix doit être inférieur au prix actuel');
        return;
      }
      if (dir == 'up' && price <= _currentPrice!) {
        setState(() => _hint = 'Le prix doit être supérieur au prix actuel');
        return;
      }
    }

    int? slippage;
    if (_showSlippage) {
      final raw = _parseDouble(_slippageController.text);
      if (raw != null && raw > 0) {
        slippage = (raw * 100).round();
      }
    }

    setState(() { _loading = true; _hint = null; });

    final order = await _api.createOrder(
      asset: widget.asset,
      side: _side,
      orderType: _orderType,
      triggerPrice: price,
      amount: amount,
      slippageBps: slippage,
    );

    if (!mounted) return;
    setState(() => _loading = false);

    if (order != null) {
      Navigator.of(context).pop(order);
      _showSuccessSnackbar(order);
    } else {
      setState(() => _hint = 'Erreur lors de la création');
    }
  }

  void _showSuccessSnackbar(TriggerOrder order) {
    final messenger = ScaffoldMessenger.maybeOf(context);
    if (messenger == null) return;
    messenger.showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle_rounded, color: Colors.white, size: 20),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                '${order.typeLabel} ${widget.asset} @ ${CurrencyFormatter.priceUsd(order.triggerPrice)}',
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w500),
              ),
            ),
          ],
        ),
        backgroundColor: _sideColor,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        margin: const EdgeInsets.all(16),
        duration: const Duration(seconds: 3),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    return Padding(
      padding: EdgeInsets.only(
        left: AppSpacing.xl,
        right: AppSpacing.xl,
        top: AppSpacing.md,
        bottom: bottomInset + AppSpacing.xl,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _buildHandle(),
            const SizedBox(height: AppSpacing.lg),
            _buildHeader(),
            const SizedBox(height: AppSpacing.xl),
            _buildSideSegment(),
            const SizedBox(height: AppSpacing.md),
            _buildOrderTypeSegment(),
            const SizedBox(height: AppSpacing.lg),
            _buildLabel('Prix cible (USD)'),
            const SizedBox(height: AppSpacing.xs),
            _buildPriceInput(),
            const SizedBox(height: AppSpacing.md),
            _buildLabel(_side == 'buy' ? 'Montant (EUR)' : 'Quantité (${widget.asset})'),
            const SizedBox(height: AppSpacing.xs),
            _buildAmountInput(),
            if (_hint != null) ...[
              const SizedBox(height: AppSpacing.sm),
              _buildHint(),
            ],
            const SizedBox(height: AppSpacing.md),
            _buildSlippageToggle(),
            if (_showSlippage) ...[
              const SizedBox(height: AppSpacing.sm),
              _buildSlippageInput(),
            ],
            const SizedBox(height: AppSpacing.lg),
            _buildOrderSummary(),
            const SizedBox(height: AppSpacing.lg),
            _buildSubmitButton(),
          ],
        ),
      ),
    );
  }

  Widget _buildHandle() {
    return Center(
      child: Container(
        width: 36,
        height: 4,
        decoration: BoxDecoration(
          color: AppColors.textSecondary.withValues(alpha: 0.25),
          borderRadius: BorderRadius.circular(2),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            color: AppColors.cryptoBrandColor(widget.asset).withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(14),
          ),
          child: Center(
            child: Text(
              widget.asset.substring(0, math.min(2, widget.asset.length)),
              style: AppTypography.labelLarge.copyWith(
                fontWeight: FontWeight.w800,
                color: AppColors.cryptoBrandColor(widget.asset),
              ),
            ),
          ),
        ),
        const SizedBox(width: AppSpacing.md),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Ordre ${widget.asset}',
                style: AppTypography.sectionTitle.copyWith(fontWeight: FontWeight.w700),
              ),
              if (_currentPrice != null)
                Text(
                  'Prix actuel : ${CurrencyFormatter.priceUsd(_currentPrice!)}',
                  style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSideSegment() {
    return Container(
      height: 44,
      decoration: BoxDecoration(
        color: AppColors.pageBackground,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          _sideTab(label: 'Acheter', value: 'buy', color: _buyColor),
          _sideTab(label: 'Vendre', value: 'sell', color: _sellColor),
        ],
      ),
    );
  }

  Widget _sideTab({required String label, required String value, required Color color}) {
    final selected = _side == value;
    return Expanded(
      child: GestureDetector(
        onTap: () {
          setState(() => _side = value);
          _onInputChanged();
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          margin: const EdgeInsets.all(3),
          decoration: BoxDecoration(
            color: selected ? color : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
            boxShadow: selected
                ? [BoxShadow(color: Colors.black.withValues(alpha: 0.08), blurRadius: 4, offset: const Offset(0, 1))]
                : null,
          ),
          child: Center(
            child: Text(
              label,
              style: AppTypography.labelLarge.copyWith(
                fontWeight: selected ? FontWeight.w700 : FontWeight.w400,
                color: selected ? Colors.white : AppColors.textSecondary,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildOrderTypeSegment() {
    return Container(
      height: 40,
      decoration: BoxDecoration(
        color: AppColors.pageBackground,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          _typeTab(label: 'Limit', value: 'limit'),
          _typeTab(label: 'Stop', value: 'stop'),
        ],
      ),
    );
  }

  Widget _typeTab({required String label, required String value}) {
    final selected = _orderType == value;
    return Expanded(
      child: GestureDetector(
        onTap: () {
          setState(() => _orderType = value);
          _onInputChanged();
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          margin: const EdgeInsets.all(3),
          decoration: BoxDecoration(
            color: selected ? AppColors.cardBackground : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
            boxShadow: selected
                ? [BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 4, offset: const Offset(0, 1))]
                : null,
          ),
          child: Center(
            child: Text(
              label,
              style: AppTypography.labelMedium.copyWith(
                fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
                color: selected ? _sideColor : AppColors.textSecondary,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildLabel(String text) {
    return Text(
      text,
      style: AppTypography.labelSmall.copyWith(
        color: AppColors.textSecondary,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.5,
      ),
    );
  }

  Widget _buildPriceInput() {
    final price = _parseDouble(_priceController.text);
    String? distLabel;
    if (price != null && _currentPrice != null && _currentPrice! > 0) {
      final pct = ((price - _currentPrice!) / _currentPrice!) * 100;
      if (pct.abs() > 0.005) {
        distLabel = '${pct >= 0 ? "+" : ""}${pct.toStringAsFixed(2)} %';
      }
    }

    return Container(
      decoration: BoxDecoration(
        color: AppColors.pageBackground,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: _hint != null ? _redColor.withValues(alpha: 0.4) : AppColors.border,
        ),
      ),
      child: Row(
        children: [
          const SizedBox(width: AppSpacing.lg),
          Text(CurrencyFormatter.usdSymbol, style: AppTypography.sectionTitle.copyWith(color: AppColors.textSecondary)),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: TextField(
              controller: _priceController,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[\d.,\s]'))],
              style: AppTypography.sectionTitle.copyWith(fontWeight: FontWeight.w600),
              decoration: InputDecoration(
                hintText: _currentPrice != null ? CurrencyFormatter.priceUsdRaw(_currentPrice!) : '0.00',
                hintStyle: AppTypography.sectionTitle.copyWith(
                  color: AppColors.textSecondary.withValues(alpha: 0.4),
                  fontWeight: FontWeight.w400,
                ),
                border: InputBorder.none,
                contentPadding: const EdgeInsets.symmetric(vertical: 14),
              ),
              autofocus: true,
            ),
          ),
          if (distLabel != null)
            Padding(
              padding: const EdgeInsets.only(right: AppSpacing.sm),
              child: Text(
                distLabel,
                style: AppTypography.labelMedium.copyWith(
                  color: _sideColor,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildAmountInput() {
    final prefix = _side == 'buy' ? '€' : widget.asset;
    return Container(
      decoration: BoxDecoration(
        color: AppColors.pageBackground,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          const SizedBox(width: AppSpacing.lg),
          Text(prefix, style: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary, fontWeight: FontWeight.w600)),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: TextField(
              controller: _amountController,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[\d.,]'))],
              style: AppTypography.sectionTitle.copyWith(fontWeight: FontWeight.w600),
              decoration: InputDecoration(
                hintText: _side == 'buy' ? '100.00' : '0.5',
                hintStyle: AppTypography.sectionTitle.copyWith(
                  color: AppColors.textSecondary.withValues(alpha: 0.4),
                  fontWeight: FontWeight.w400,
                ),
                border: InputBorder.none,
                contentPadding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSlippageToggle() {
    return GestureDetector(
      onTap: () => setState(() => _showSlippage = !_showSlippage),
      child: Row(
        children: [
          Icon(
            _showSlippage ? Icons.check_box_rounded : Icons.check_box_outline_blank_rounded,
            size: 20,
            color: _showSlippage ? _sideColor : AppColors.textSecondary,
          ),
          const SizedBox(width: AppSpacing.sm),
          Text(
            'Protection slippage',
            style: AppTypography.bodySmall.copyWith(
              color: _showSlippage ? AppColors.textPrimary : AppColors.textSecondary,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSlippageInput() {
    return Container(
      height: 48,
      decoration: BoxDecoration(
        color: AppColors.pageBackground,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          const SizedBox(width: AppSpacing.lg),
          Text('Max slippage', style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary)),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: TextField(
              controller: _slippageController,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[\d.,]'))],
              style: AppTypography.bodyMedium.copyWith(fontWeight: FontWeight.w600),
              textAlign: TextAlign.right,
              decoration: const InputDecoration(
                hintText: '0.50',
                border: InputBorder.none,
                contentPadding: EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(right: AppSpacing.lg),
            child: Text('%', style: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary)),
          ),
        ],
      ),
    );
  }

  Widget _buildHint() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF7ED),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline_rounded, size: 16, color: Color(0xFFEA580C)),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              _hint!,
              style: AppTypography.bodySmall.copyWith(color: const Color(0xFFEA580C)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOrderSummary() {
    final dir = _autoDirection;
    final source = (_side == 'buy') ? 'ASK' : 'BID';
    final typeLabel = '${_side.toUpperCase()} ${_orderType.toUpperCase()}';
    final dirLabel = dir == 'up' ? 'au-dessus' : 'en-dessous';

    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: _sideColor.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _sideColor.withValues(alpha: 0.12)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.info_outline_rounded, size: 14, color: _sideColor),
              const SizedBox(width: 6),
              Text(
                typeLabel,
                style: AppTypography.labelMedium.copyWith(
                  color: _sideColor,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            'L\'ordre sera exécuté quand le prix $source passe $dirLabel du prix cible.',
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.textSecondary,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSubmitButton() {
    final price = _parseDouble(_priceController.text);
    final amount = _parseDouble(_amountController.text);
    final isValid = price != null && price > 0 && amount != null && amount > 0 && _hint == null;

    return GestureDetector(
      onTapDown: (_) => setState(() => _buttonPressed = true),
      onTapUp: (_) => setState(() => _buttonPressed = false),
      onTapCancel: () => setState(() => _buttonPressed = false),
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 200),
        opacity: isValid || _loading ? 1.0 : 0.5,
        child: AnimatedScale(
          scale: _buttonPressed ? 0.97 : 1.0,
          duration: const Duration(milliseconds: 100),
          curve: Curves.easeOut,
          child: FilledButton(
            onPressed: _loading ? null : _submit,
            style: FilledButton.styleFrom(
              backgroundColor: _sideColor,
              foregroundColor: Colors.white,
              minimumSize: const Size.fromHeight(52),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            ),
            child: _loading
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                  )
                : Text(
                    _side == 'buy'
                        ? 'Placer l\'ordre d\'achat'
                        : 'Placer l\'ordre de vente',
                    style: AppTypography.labelLarge.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
          ),
        ),
      ),
    );
  }
}
