import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../../core/currency_formatter.dart';
import '../../../../design_system/design_system.dart';
import '../../data/price_alerts_api.dart';
import '../../domain/models/price_alert.dart';

double _roundToCleanLevel(double v) {
  if (v >= 100000) return (v / 1000).round() * 1000.0;
  if (v >= 10000) return (v / 500).round() * 500.0;
  if (v >= 1000) return (v / 100).round() * 100.0;
  if (v >= 100) return (v / 10).round() * 10.0;
  if (v >= 10) return (v / 1).round() * 1.0;
  return double.parse(v.toStringAsFixed(2));
}

class CreateAlertBottomSheet extends StatefulWidget {
  final String asset;
  final double? currentPrice;

  const CreateAlertBottomSheet({
    super.key,
    required this.asset,
    this.currentPrice,
  });

  static Future<PriceAlert?> show(
    BuildContext context, {
    required String asset,
    double? currentPrice,
  }) {
    return showModalBottomSheet<PriceAlert>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.cardBackground,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      builder: (_) => CreateAlertBottomSheet(asset: asset, currentPrice: currentPrice),
    );
  }

  @override
  State<CreateAlertBottomSheet> createState() => _State();
}

class _State extends State<CreateAlertBottomSheet> with SingleTickerProviderStateMixin {
  final _controller = TextEditingController();
  final _focusNode = FocusNode();
  final _api = PriceAlertsApi();

  String _direction = 'up';
  String _triggerMode = 'once';
  bool _loading = false;
  String? _hint;
  bool _buttonPressed = false;

  double? get _currentPrice => widget.currentPrice;

  static const _greenColor = Color(0xFF16A34A);
  static const _redColor = Color(0xFFDC2626);

  Color get _dirColor => _direction == 'up' ? _greenColor : _redColor;

  double? get _aboveSuggestion =>
      _currentPrice != null ? _roundToCleanLevel(_currentPrice! * 1.02) : null;
  double? get _belowSuggestion =>
      _currentPrice != null ? _roundToCleanLevel(_currentPrice! * 0.98) : null;

  @override
  void initState() {
    super.initState();
    _controller.addListener(_onPriceChanged);
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _onPriceChanged() {
    final price = _parsePrice();
    if (price == null || _currentPrice == null) {
      if (_hint != null) setState(() => _hint = null);
      return;
    }
    String? h;
    if (_direction == 'up' && price <= _currentPrice!) {
      h = 'Le prix doit être supérieur au prix actuel';
    } else if (_direction == 'down' && price >= _currentPrice!) {
      h = 'Le prix doit être inférieur au prix actuel';
    } else if (price == _currentPrice) {
      h = 'Le prix doit être différent du prix actuel';
    }
    if (h != _hint) setState(() => _hint = h);
  }

  double? _parsePrice() {
    final raw = _controller.text.replaceAll(',', '.').replaceAll(' ', '');
    return double.tryParse(raw);
  }

  void _applyPrice(double target) {
    _controller.text = CurrencyFormatter.priceRaw(target);
    _controller.selection =
        TextSelection.collapsed(offset: _controller.text.length);
  }

  void _applyPercent(double pct) {
    if (_currentPrice == null) return;
    _applyPrice(_currentPrice! * (1 + pct));
  }

  Future<void> _submit() async {
    final price = _parsePrice();
    if (price == null || price <= 0) {
      setState(() => _hint = 'Entrez un prix valide');
      return;
    }
    if (_currentPrice != null) {
      if (_direction == 'up' && price <= _currentPrice!) {
        setState(() => _hint = 'Le prix doit être supérieur au prix actuel');
        return;
      }
      if (_direction == 'down' && price >= _currentPrice!) {
        setState(() => _hint = 'Le prix doit être inférieur au prix actuel');
        return;
      }
    }

    setState(() {
      _loading = true;
      _hint = null;
    });

    final alert = await _api.createAlert(
      asset: widget.asset,
      targetPrice: price,
      direction: _direction,
      triggerMode: _triggerMode,
    );

    if (!mounted) return;
    setState(() => _loading = false);

    if (alert != null) {
      Navigator.of(context).pop(alert);
      _showSuccessSnackbar(alert);
    } else {
      setState(() => _hint = 'Erreur lors de la création');
    }
  }

  void _showSuccessSnackbar(PriceAlert alert) {
    final messenger = ScaffoldMessenger.maybeOf(context);
    if (messenger == null) return;
    final op = alert.isUp ? '>' : '<';
    messenger.showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle_rounded, color: Colors.white, size: 20),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Alerte créée · ${alert.asset} $op ${CurrencyFormatter.price(alert.targetPrice)}',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ),
        backgroundColor: _dirColor,
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
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildHandle(),
          const SizedBox(height: AppSpacing.lg),
          _buildHeader(),
          const SizedBox(height: AppSpacing.xl),
          _buildDirectionSegment(),
          const SizedBox(height: AppSpacing.lg),
          _buildPriceInput(),
          if (_currentPrice != null) ...[
            const SizedBox(height: AppSpacing.sm),
            _buildQuickButtons(),
          ],
          if (_hint != null) ...[
            const SizedBox(height: AppSpacing.sm),
            _buildHint(),
          ],
          if (_currentPrice != null && _controller.text.isEmpty) ...[
            const SizedBox(height: AppSpacing.md),
            _buildSuggestions(),
          ],
          const SizedBox(height: AppSpacing.lg),
          _buildFrequencySegment(),
          const SizedBox(height: AppSpacing.xl),
          _buildSubmitButton(),
        ],
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
                'Alerte ${widget.asset}',
                style: AppTypography.sectionTitle.copyWith(fontWeight: FontWeight.w700),
              ),
              if (_currentPrice != null)
                Text(
                  'Prix actuel : ${CurrencyFormatter.price(_currentPrice!)}',
                  style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildDirectionSegment() {
    return Container(
      height: 44,
      decoration: BoxDecoration(
        color: AppColors.pageBackground,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          _segmentTab(
            label: 'Au-dessus',
            icon: Icons.arrow_upward_rounded,
            value: 'up',
            color: _greenColor,
          ),
          _segmentTab(
            label: 'En-dessous',
            icon: Icons.arrow_downward_rounded,
            value: 'down',
            color: _redColor,
          ),
        ],
      ),
    );
  }

  Widget _segmentTab({
    required String label,
    required IconData icon,
    required String value,
    required Color color,
  }) {
    final selected = _direction == value;
    return Expanded(
      child: GestureDetector(
        onTap: () {
          setState(() => _direction = value);
          _onPriceChanged();
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          margin: const EdgeInsets.all(3),
          decoration: BoxDecoration(
            color: selected ? AppColors.cardBackground : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
            boxShadow: selected
                ? [BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 4, offset: const Offset(0, 1))]
                : null,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 16, color: selected ? color : AppColors.textSecondary),
              const SizedBox(width: 6),
              Text(
                label,
                style: AppTypography.labelLarge.copyWith(
                  fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
                  color: selected ? color : AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPriceInput() {
    final price = _parsePrice();
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
          color: _hint != null
              ? _redColor.withValues(alpha: 0.4)
              : AppColors.border,
          width: 1,
        ),
      ),
      child: Row(
        children: [
          const SizedBox(width: AppSpacing.lg),
          Text(CurrencyFormatter.symbol, style: AppTypography.sectionTitle.copyWith(color: AppColors.textSecondary)),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: TextField(
              controller: _controller,
              focusNode: _focusNode,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[\d.,\s]'))],
              style: AppTypography.sectionTitle.copyWith(fontWeight: FontWeight.w600),
              decoration: InputDecoration(
                hintText: _currentPrice != null ? CurrencyFormatter.priceRaw(_currentPrice!) : '0.00',
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
              padding: const EdgeInsets.only(right: 4),
              child: Text(
                distLabel,
                style: AppTypography.labelMedium.copyWith(
                  color: _dirColor,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          if (_controller.text.isNotEmpty)
            IconButton(
              icon: Icon(Icons.close_rounded, size: 18, color: AppColors.textSecondary.withValues(alpha: 0.5)),
              onPressed: () {
                _controller.clear();
                setState(() => _hint = null);
              },
            ),
        ],
      ),
    );
  }

  Widget _buildQuickButtons() {
    final isUp = _direction == 'up';
    final percents = isUp ? [0.01, 0.02, 0.05] : [-0.01, -0.02, -0.05];
    final labels = isUp ? ['+1 %', '+2 %', '+5 %'] : ['-1 %', '-2 %', '-5 %'];

    return Row(
      children: List.generate(percents.length, (i) {
        return Expanded(
          child: Padding(
            padding: EdgeInsets.only(right: i < percents.length - 1 ? AppSpacing.sm : 0),
            child: _QuickPercentButton(
              label: labels[i],
              color: _dirColor,
              onTap: () => _applyPercent(percents[i]),
            ),
          ),
        );
      }),
    );
  }

  Widget _buildSuggestions() {
    final above = _aboveSuggestion;
    final below = _belowSuggestion;
    if (above == null || below == null) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Suggestions',
          style: AppTypography.labelSmall.copyWith(
            color: AppColors.textSecondary,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: AppSpacing.xs),
        Row(
          children: [
            Expanded(
              child: _SuggestionChip(
                icon: Icons.arrow_upward_rounded,
                label: CurrencyFormatter.priceRaw(above),
                color: _greenColor,
                onTap: () {
                  setState(() => _direction = 'up');
                  _applyPrice(above);
                },
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: _SuggestionChip(
                icon: Icons.arrow_downward_rounded,
                label: CurrencyFormatter.priceRaw(below),
                color: _redColor,
                onTap: () {
                  setState(() => _direction = 'down');
                  _applyPrice(below);
                },
              ),
            ),
          ],
        ),
      ],
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

  Widget _buildFrequencySegment() {
    return Container(
      height: 40,
      decoration: BoxDecoration(
        color: AppColors.pageBackground,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          _freqTab(label: 'Une seule fois', value: 'once'),
          _freqTab(label: 'Toujours', value: 'recurring'),
        ],
      ),
    );
  }

  Widget _freqTab({required String label, required String value}) {
    final selected = _triggerMode == value;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _triggerMode = value),
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
                color: selected ? AppColors.textPrimary : AppColors.textSecondary,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSubmitButton() {
    final price = _parsePrice();
    final isValid = price != null && price > 0 && _hint == null;

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
              backgroundColor: _dirColor,
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
                : Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        _direction == 'up' ? Icons.arrow_upward_rounded : Icons.arrow_downward_rounded,
                        size: 18,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        price != null
                            ? 'Alerter si ${_direction == "up" ? ">" : "<"} ${CurrencyFormatter.price(price)}'
                            : 'Créer l\'alerte',
                        style: AppTypography.labelLarge.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
          ),
        ),
      ),
    );
  }
}

class _QuickPercentButton extends StatefulWidget {
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _QuickPercentButton({
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  State<_QuickPercentButton> createState() => _QuickPercentButtonState();
}

class _QuickPercentButtonState extends State<_QuickPercentButton> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => setState(() => _pressed = true),
      onTapUp: (_) {
        setState(() => _pressed = false);
        widget.onTap();
      },
      onTapCancel: () => setState(() => _pressed = false),
      child: AnimatedScale(
        scale: _pressed ? 0.93 : 1.0,
        duration: const Duration(milliseconds: 80),
        curve: Curves.easeOut,
        child: Container(
          height: 34,
          decoration: BoxDecoration(
            color: widget.color.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: widget.color.withValues(alpha: 0.2)),
          ),
          child: Center(
            child: Text(
              widget.label,
              style: AppTypography.labelMedium.copyWith(
                color: widget.color,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _SuggestionChip extends StatefulWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _SuggestionChip({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  State<_SuggestionChip> createState() => _SuggestionChipState();
}

class _SuggestionChipState extends State<_SuggestionChip> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => setState(() => _pressed = true),
      onTapUp: (_) {
        setState(() => _pressed = false);
        widget.onTap();
      },
      onTapCancel: () => setState(() => _pressed = false),
      child: AnimatedScale(
        scale: _pressed ? 0.95 : 1.0,
        duration: const Duration(milliseconds: 80),
        curve: Curves.easeOut,
        child: Container(
          height: 40,
          decoration: BoxDecoration(
            color: widget.color.withValues(alpha: 0.06),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: widget.color.withValues(alpha: 0.15)),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(widget.icon, size: 14, color: widget.color),
              const SizedBox(width: 6),
              Text(
                '${widget.label} ${CurrencyFormatter.symbol}',
                style: AppTypography.labelMedium.copyWith(
                  color: widget.color,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
