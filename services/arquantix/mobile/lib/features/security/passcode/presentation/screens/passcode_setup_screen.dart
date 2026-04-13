import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'package:arquantix_news/features/app_entry/application/app_entry_bootstrap.dart';
import 'package:arquantix_news/features/registration/screens/registration_flow_screen.dart';
import 'package:arquantix_news/features/security/onboarding/biometric_login_onboarding_screen.dart';
import 'package:arquantix_news/features/security/passcode/data/session_api.dart';
import 'package:arquantix_news/features/security/passcode/data/session_service.dart';
import 'package:arquantix_news/design_system/atoms/app_colors.dart';
import 'package:arquantix_news/design_system/atoms/app_spacing.dart';
import 'package:arquantix_news/design_system/atoms/app_typography.dart';
import '../../data/passcode_service.dart';
import '../widgets/pin_keypad.dart';

/// Comportement après enregistrement réussi du PIN.
enum PasscodeSetupOnSuccess {
  /// Ferme avec `Navigator.pop(true)` (flows modaux / design system).
  popTrue,

  /// Remplace la pile par le flux PIN / shell ([AppEntryBootstrap]).
  continueToAppSecureGate,
}

/// Création / changement du PIN 6 chiffres (double saisie).
/// Layout aligné sur [PasscodeUnlockScreen] (titre HeadingSecondary, pad, espace bas type « oublié »).
class PasscodeSetupScreen extends StatefulWidget {
  const PasscodeSetupScreen({
    super.key,
    this.onSuccessCompletion = PasscodeSetupOnSuccess.popTrue,
  });

  final PasscodeSetupOnSuccess onSuccessCompletion;

  @override
  State<PasscodeSetupScreen> createState() => _PasscodeSetupScreenState();
}

class _PasscodeSetupScreenState extends State<PasscodeSetupScreen> {
  String _first = '';
  String _confirm = '';
  bool _confirmPhase = false;
  String? _error;

  /// Hauteur réservée pour une ligne de message (identique à [PasscodeUnlockScreen]).
  static double get _messageSlotHeight {
    final s = AppTypography.itemSupporting;
    final fs = s.fontSize ?? 13;
    final lh = s.height ?? 1;
    return fs * lh;
  }

  String get _pageTitle => _confirmPhase
      ? 'Confirmez votre code à 6 chiffres'
      : 'Choisissez un code à 6 chiffres pour votre connexion';

  void _onDigit(String d) {
    setState(() {
      _error = null;
      final target = _confirmPhase ? _confirm : _first;
      if (target.length >= PasscodeService.pinLength) return;
      if (_confirmPhase) {
        _confirm = target + d;
      } else {
        _first = target + d;
      }
    });
    _maybeAdvance();
  }

  void _onBackspace() {
    setState(() {
      _error = null;
      if (_confirmPhase) {
        if (_confirm.isEmpty) {
          _confirmPhase = false;
        } else {
          _confirm = _confirm.substring(0, _confirm.length - 1);
        }
      } else if (_first.isNotEmpty) {
        _first = _first.substring(0, _first.length - 1);
      }
    });
  }

  Future<void> _maybeAdvance() async {
    if (!_confirmPhase && _first.length == PasscodeService.pinLength) {
      await Future<void>.delayed(Duration.zero);
      if (!mounted) return;
      setState(() => _confirmPhase = true);
    } else if (_confirmPhase && _confirm.length == PasscodeService.pinLength) {
      if (_confirm != _first) {
        setState(() {
          _error = 'Les codes ne correspondent pas. Recommencez.';
          _first = '';
          _confirm = '';
          _confirmPhase = false;
        });
        return;
      }
      try {
        await PasscodeService.instance.setPasscode(_first);
        await PasscodeService.instance.setBiometricUnlockEnabled(false);
        final tok = await SessionService.instance.readAccessToken();
        if (tok != null && tok.isNotEmpty) {
          // ACK serveur : fire-and-forget — retry interne dans [SessionApi.ackLocalPasscodeRegistered],
          // ne pas retarder la navigation (réseau / backoff).
          await SessionApi().ackLocalPasscodeRegistered(accessToken: tok);
        }
        if (!mounted) return;
        switch (widget.onSuccessCompletion) {
          case PasscodeSetupOnSuccess.popTrue:
            Navigator.of(context).pop(true);
          case PasscodeSetupOnSuccess.continueToAppSecureGate:
            final pending =
                await SessionService.instance.consumePendingEuRegistrationAfterPasscode();
            if (!mounted) return;
            if (pending) {
              await Navigator.of(context).push<void>(
                MaterialPageRoute<void>(
                  fullscreenDialog: true,
                  builder: (_) => const BiometricLoginOnboardingScreen(),
                ),
              );
              if (!mounted) return;
              await Navigator.of(context).pushAndRemoveUntil(
                MaterialPageRoute<void>(
                  builder: (_) => const RegistrationFlowScreen(
                    jurisdiction: 'EU',
                    rootPresentation: true,
                  ),
                ),
                (_) => false,
              );
            } else {
              await AppEntryBootstrap.pushRootReplacingAll(
                context,
                forcePostAuthUnlock: true,
              );
            }
        }
      } catch (e) {
        setState(() => _error = '$e');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final filled = _confirmPhase ? _confirm.length : _first.length;
    final errorStyle = AppTypography.itemSupporting.copyWith(
      color: AppColors.semanticNegative,
    );

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppBar(
        backgroundColor: AppColors.pageBackground,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        automaticallyImplyLeading: false,
        title: const SizedBox.shrink(),
      ),
      body: SafeArea(
        top: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(
                      AppSpacing.pageEdge,
                      AppSpacing.sm,
                      AppSpacing.pageEdge,
                      AppSpacing.sm,
                    ),
                    child: Text(
                      _pageTitle,
                      textAlign: TextAlign.center,
                      style: AppTypography.headerSecondary.copyWith(
                        color: AppColors.textPrimary,
                      ),
                    ),
                  ),
                  Expanded(
                    child: Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          PinDotsRow(filled: filled),
                          const SizedBox(height: AppSpacing.md),
                          SizedBox(
                            height: _messageSlotHeight,
                            width: double.infinity,
                            child: Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: AppSpacing.lg,
                              ),
                              child: Center(
                                child: _error != null && _error!.isNotEmpty
                                    ? Text(
                                        _error!,
                                        textAlign: TextAlign.center,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: errorStyle,
                                      )
                                    : const SizedBox.shrink(),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.md),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  NumericPinKeypad(
                    onDigit: _onDigit,
                    onBackspace: _onBackspace,
                  ),
                  const SizedBox(height: AppSpacing.s8),
                  // Réserve le même espace vertical que le bouton sur [PasscodeUnlockScreen].
                  ExcludeSemantics(
                    child: Visibility(
                      visible: false,
                      maintainSize: true,
                      maintainAnimation: true,
                      maintainState: true,
                      child: Center(
                        child: TextButton(
                          onPressed: () {},
                          style: TextButton.styleFrom(
                            padding: const EdgeInsets.symmetric(
                              horizontal: AppSpacing.lg,
                              vertical: AppSpacing.sm,
                            ),
                          ),
                          child: Text(
                            'Code d’accès oublié ?',
                            style: GoogleFonts.inter(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: AppColors.indigo,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
