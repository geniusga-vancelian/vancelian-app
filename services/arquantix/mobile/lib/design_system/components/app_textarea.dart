import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_motion.dart';
import '../atoms/app_radius.dart';

/// Champ de texte multi-lignes avec label, description et erreur.
class AppTextarea extends StatefulWidget {
  const AppTextarea({
    super.key,
    this.label,
    this.placeholder,
    this.controller,
    this.focusNode,
    this.onChanged,
    this.description,
    this.error,
    this.minLines = 3,
    this.maxLines = 6,
    this.maxLength,
    this.enabled = true,
  });

  final String? label;
  final String? placeholder;
  final TextEditingController? controller;
  final FocusNode? focusNode;
  final ValueChanged<String>? onChanged;
  final String? description;
  final String? error;
  final int minLines;
  final int maxLines;
  final int? maxLength;
  final bool enabled;

  @override
  State<AppTextarea> createState() => _AppTextareaState();
}

class _AppTextareaState extends State<AppTextarea> {
  late TextEditingController _ctrl;
  FocusNode? _internalFocusNode;
  bool _hasFocus = false;

  FocusNode get _focusNode =>
      widget.focusNode ?? (_internalFocusNode ??= FocusNode());

  static const _labelColor = Color(0xFF8E8E93);
  static const _errorColor = Color(0xFFFF2D55);

  @override
  void initState() {
    super.initState();
    _ctrl = widget.controller ?? TextEditingController();
    _focusNode.addListener(_onFocusChange);
  }

  @override
  void dispose() {
    if (widget.controller == null) _ctrl.dispose();
    _focusNode.removeListener(_onFocusChange);
    _internalFocusNode?.dispose();
    super.dispose();
  }

  void _onFocusChange() {
    if (_focusNode.hasFocus != _hasFocus) {
      setState(() => _hasFocus = _focusNode.hasFocus);
    }
  }

  bool get _hasError => widget.error != null && widget.error!.isNotEmpty;

  Color get _borderColor {
    if (_hasError) return _errorColor;
    if (_hasFocus) return AppColors.indigo;
    return AppColors.white;
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (widget.label != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 6, left: 4),
            child: Text(
              widget.label!,
              style: GoogleFonts.inter(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: _hasError ? _errorColor : _labelColor,
              ),
            ),
          ),
        AnimatedContainer(
          duration: AppMotion.fast,
          curve: AppMotion.standard,
          decoration: BoxDecoration(
            color: AppColors.white,
            borderRadius: BorderRadius.circular(AppRadius.lg),
            border: Border.all(color: _borderColor, width: 1.5),
          ),
          child: Theme(
            data: Theme.of(context).copyWith(
              textSelectionTheme: TextSelectionThemeData(
                selectionColor: AppColors.indigo.withValues(alpha: 0.15),
                cursorColor: AppColors.indigo,
                selectionHandleColor: AppColors.indigo,
              ),
            ),
            child: TextField(
              controller: _ctrl,
              focusNode: _focusNode,
              enabled: widget.enabled,
              cursorColor: AppColors.indigo,
              minLines: widget.minLines,
              maxLines: widget.maxLines,
              maxLength: widget.maxLength,
              onChanged: widget.onChanged,
              style: GoogleFonts.inter(
                fontSize: 15,
                fontWeight: FontWeight.w400,
                height: 22 / 15,
                color: AppColors.textPrimary,
              ),
              decoration: InputDecoration(
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                isDense: true,
                filled: false,
                contentPadding: const EdgeInsets.all(16),
                hintText: widget.placeholder,
                hintStyle: GoogleFonts.inter(
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                  height: 22 / 17,
                  letterSpacing: -0.43,
                  color: _labelColor,
                ),
                counterText: '',
              ),
            ),
          ),
        ),
        if (widget.description != null && !_hasError)
          Padding(
            padding: const EdgeInsets.only(top: 4, left: 4),
            child: Text(
              widget.description!,
              style: GoogleFonts.inter(
                fontSize: 13,
                color: const Color(0xFF808080),
              ),
            ),
          ),
        if (_hasError)
          Padding(
            padding: const EdgeInsets.only(top: 4, left: 4),
            child: Text(
              widget.error!,
              style: GoogleFonts.inter(
                fontSize: 13,
                color: _errorColor,
              ),
            ),
          ),
      ],
    );
  }
}
