import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_motion.dart';
import '../atoms/app_radius.dart';

/// Champ de saisie OTP segmenté.
///
/// Affiche [length] cases individuelles. Le callback [onCompleted] est appelé
/// lorsque toutes les cases sont remplies.
class AppOtpInput extends StatefulWidget {
  const AppOtpInput({
    super.key,
    this.length = 6,
    this.onChanged,
    this.onCompleted,
    this.hasError = false,
    this.errorMessage,
    this.showErrorMessage = true,
    this.locked = false,
    this.autofocus = true,
  });

  final int length;
  final ValueChanged<String>? onChanged;
  final ValueChanged<String>? onCompleted;

  /// Bordure rouge sur les cases (ex. code refusé).
  final bool hasError;

  /// Texte sous les cases ; affiché seulement si [showErrorMessage] est vrai.
  final String? errorMessage;

  final bool showErrorMessage;

  /// Pendant la vérification : masque d’opacité sur les cases, saisie figée.
  final bool locked;

  final bool autofocus;

  @override
  State<AppOtpInput> createState() => _AppOtpInputState();
}

class _AppOtpInputState extends State<AppOtpInput> {
  late final TextEditingController _ctrl;
  late final FocusNode _focusNode;

  @override
  void initState() {
    super.initState();
    _ctrl = TextEditingController();
    _focusNode = FocusNode();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(covariant AppOtpInput oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.locked && !oldWidget.locked) {
      _focusNode.unfocus();
    }
  }

  bool get _borderError =>
      widget.hasError ||
      (widget.errorMessage != null && widget.errorMessage!.isNotEmpty);

  bool get _showErrorText =>
      widget.showErrorMessage &&
      widget.errorMessage != null &&
      widget.errorMessage!.isNotEmpty;

  double get _otpWidth => widget.length * 44 + (widget.length - 1) * 8;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: GestureDetector(
            onTap: widget.locked ? null : () => _focusNode.requestFocus(),
            child: SizedBox(
              width: _otpWidth,
              height: 52,
              child: Stack(
                clipBehavior: Clip.none,
                children: [
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: List.generate(widget.length, (i) {
                      final filled = _ctrl.text.length > i;
                      final active = !widget.locked &&
                          _focusNode.hasFocus &&
                          _ctrl.text.length == i;
                      return Padding(
                        padding: EdgeInsets.only(left: i > 0 ? 8 : 0),
                        child: AnimatedContainer(
                          duration: AppMotion.fast,
                          curve: AppMotion.standard,
                          width: 44,
                          height: 52,
                          decoration: BoxDecoration(
                            color: AppColors.white,
                            borderRadius:
                                BorderRadius.circular(AppRadius.md),
                            border: Border.all(
                              color: _borderError
                                  ? AppColors.semanticDanger
                                  : active
                                      ? AppColors.indigo
                                      : filled
                                          ? AppColors.border
                                          : AppColors.placeholderBg,
                              width: active ? 1.5 : 1,
                            ),
                          ),
                          alignment: Alignment.center,
                          child: filled
                              ? Text(
                                  _ctrl.text[i],
                                  style: GoogleFonts.inter(
                                    fontSize: 22,
                                    fontWeight: FontWeight.w600,
                                    color: _borderError
                                        ? AppColors.semanticDanger
                                        : AppColors.textPrimary,
                                  ),
                                )
                              : active
                                  ? _Caret(
                                      color: _borderError
                                          ? AppColors.semanticDanger
                                          : AppColors.indigo,
                                    )
                                  : const SizedBox.shrink(),
                        ),
                      );
                    }),
                  ),
                  if (widget.locked)
                    Positioned.fill(
                      child: ClipRRect(
                        borderRadius:
                            BorderRadius.circular(AppRadius.md),
                        child: ColoredBox(
                          color:
                              Colors.white.withValues(alpha: 0.58),
                        ),
                      ),
                    ),
                  Positioned.fill(
                    child: Opacity(
                      opacity: 0,
                      child: TextField(
                        controller: _ctrl,
                        focusNode: _focusNode,
                        autofocus: widget.autofocus,
                        readOnly: widget.locked,
                        enableInteractiveSelection: !widget.locked,
                        keyboardType: TextInputType.number,
                        maxLength: widget.length,
                        inputFormatters: [
                          FilteringTextInputFormatter.digitsOnly,
                        ],
                        decoration: const InputDecoration(
                          counterText: '',
                          border: InputBorder.none,
                        ),
                        onChanged: (v) {
                          setState(() {});
                          widget.onChanged?.call(v);
                          if (!widget.locked &&
                              v.length == widget.length) {
                            widget.onCompleted?.call(v);
                          }
                        },
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        if (_showErrorText)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              widget.errorMessage!,
              style: GoogleFonts.inter(
                fontSize: 13,
                color: AppColors.semanticDanger,
              ),
            ),
          ),
      ],
    );
  }
}

class _Caret extends StatefulWidget {
  const _Caret({required this.color});

  final Color color;

  @override
  State<_Caret> createState() => _CaretState();
}

class _CaretState extends State<_Caret>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _ctrl,
      child: Container(
        width: 1.5,
        height: 22,
        color: widget.color,
      ),
    );
  }
}
