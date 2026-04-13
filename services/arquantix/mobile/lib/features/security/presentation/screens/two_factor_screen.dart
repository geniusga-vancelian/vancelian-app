import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../../core/config.dart';
import '../../../../design_system/atoms/app_colors.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../data/two_factor_api.dart';

/// Écran générique 2FA : SMS / email OTP (6 chiffres) ou TOTP (même saisie).
///
/// Réutilisable pour verify_phone, verify_email, withdrawal, login, etc. via [purpose].
/// Le backend renvoie [maskedTarget] après [start] ; seuls sous-titre et icône dépendent du canal.
class TwoFactorScreen extends StatefulWidget {
  const TwoFactorScreen({
    super.key,
    required this.channel,
    required this.purpose,
    this.target,
    this.accessToken,
    this.personId,
    this.title,
    this.onVerified,
    this.api,
    this.skipAutoStart = false,
    this.initialChallengeId,
    this.initialMaskedTarget,
    this.initialResendAfterSeconds = 30,
    this.onResendRequested,
    this.registrationResendPrepare,
  });

  final TwoFactorChannel channel;
  final String purpose;

  /// E.164 ou email ; obligatoire pour sms/email, ignoré pour totp si non applicable.
  final String? target;

  final String? accessToken;

  /// Dev uniquement si `TWO_FACTOR_REQUIRE_AUTH=false` côté API.
  final String? personId;

  /// Surcharge du titre (défaut : « Code à 6 chiffres »).
  final String? title;

  /// Après succès [verify], avec l’id du challenge vérifié (avant le [Navigator.pop]).
  final Future<void> Function(String challengeId)? onVerified;

  /// Injecté pour les tests ; par défaut [TwoFactorApi] avec [Config.twoFactorStartUrl].
  final TwoFactorApi? api;

  /// N’appelle pas `POST /api/2fa/start` au montage (ex. OTP déjà démarré via registration `interaction/prepare`).
  final bool skipAutoStart;

  final String? initialChallengeId;
  final String? initialMaskedTarget;
  final int initialResendAfterSeconds;

  /// Renvoi SMS explicite (ex. `POST .../interaction/resend`) — met à jour challenge + jeton.
  final Future<Map<String, dynamic>?> Function()? onResendRequested;

  /// @deprecated Utiliser [onResendRequested].
  final Future<Map<String, dynamic>?> Function()? registrationResendPrepare;

  @override
  State<TwoFactorScreen> createState() => _TwoFactorScreenState();
}

class _TwoFactorScreenState extends State<TwoFactorScreen> {
  late final TwoFactorApi _api;
  final List<TextEditingController> _controllers =
      List.generate(6, (_) => TextEditingController());
  final List<FocusNode> _focusNodes = List.generate(6, (_) => FocusNode());

  String? _challengeId;
  String? _maskedTarget;
  int _resendAfterSeconds = 30;
  int _resendCountdown = 0;
  Timer? _resendTimer;

  bool _starting = true;
  bool _verifying = false;
  bool _resendInProgress = false;
  String? _inlineError;
  String? _otpauthUrl;

  @override
  void initState() {
    super.initState();
    _api = widget.api ??
        TwoFactorApi(
          startUrl: Config.twoFactorStartUrl,
          verifyUrl: Config.twoFactorVerifyUrl,
          accessToken: widget.accessToken,
        );
    if (widget.skipAutoStart &&
        widget.initialChallengeId != null &&
        widget.initialChallengeId!.isNotEmpty) {
      _starting = false;
      _challengeId = widget.initialChallengeId;
      _maskedTarget = widget.initialMaskedTarget;
      _resendAfterSeconds = widget.initialResendAfterSeconds;
      _resendCountdown = _resendAfterSeconds;
      _resendTimer?.cancel();
      _resendTimer = Timer.periodic(const Duration(seconds: 1), (_) {
        if (!mounted) return;
        setState(() {
          if (_resendCountdown > 0) {
            _resendCountdown -= 1;
          }
        });
      });
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _focusNodes.first.requestFocus();
      });
    } else {
      WidgetsBinding.instance.addPostFrameCallback((_) => _startChallenge());
    }
  }

  @override
  void dispose() {
    _resendTimer?.cancel();
    for (final c in _controllers) {
      c.dispose();
    }
    for (final f in _focusNodes) {
      f.dispose();
    }
    super.dispose();
  }

  IconData get _channelIcon {
    switch (widget.channel) {
      case TwoFactorChannel.sms:
        return Icons.sms_outlined;
      case TwoFactorChannel.email:
        return Icons.mail_outline;
      case TwoFactorChannel.totp:
        return Icons.shield_outlined;
    }
  }

  Future<void> _onResendPressed() async {
    final fn = widget.onResendRequested ?? widget.registrationResendPrepare;
    if (fn != null) {
      await _runExternalResend(fn);
      return;
    }
    await _startChallenge();
  }

  Future<void> _runExternalResend(
    Future<Map<String, dynamic>?> Function() fetch,
  ) async {
    if (_resendCountdown > 0 || _challengeId == null) return;
    setState(() {
      _resendInProgress = true;
      _inlineError = null;
    });
    final m = await fetch();
    if (!mounted) return;
    if (m == null) {
      setState(() {
        _resendInProgress = false;
        _inlineError =
            'Impossible d’envoyer un nouveau code. Réessayez dans un instant.';
      });
      return;
    }
    final err = m['_error'] as String?;
    if (err != null && err.isNotEmpty) {
      setState(() {
        _resendInProgress = false;
        _inlineError = err;
      });
      return;
    }
    final token = m['otp_token'] as String?;
    final id = m['challenge_id'] as String?;
    final masked = m['target_masked'] as String?;
    if (token != null && token.isNotEmpty) {
      _api = TwoFactorApi(
        startUrl: Config.twoFactorStartUrl,
        verifyUrl: Config.twoFactorVerifyUrl,
        accessToken: token,
      );
    }
    final secs = (m['resend_after_seconds'] as num?)?.toInt() ?? _resendAfterSeconds;
    _resendAfterSeconds = secs;
    _resendCountdown = secs;
    _resendTimer?.cancel();
    _resendTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() {
        if (_resendCountdown > 0) {
          _resendCountdown -= 1;
        }
      });
    });
    for (final c in _controllers) {
      c.clear();
    }
    setState(() {
      _resendInProgress = false;
      if (id != null && id.isNotEmpty) _challengeId = id;
      if (masked != null && masked.isNotEmpty) _maskedTarget = masked;
    });
    if (mounted) {
      _focusNodes.first.requestFocus();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Nouveau code envoyé'),
          behavior: SnackBarBehavior.floating,
          margin: const EdgeInsets.all(AppSpacing.md),
        ),
      );
    }
  }

  Future<void> _startChallenge() async {
    setState(() {
      _starting = true;
      _inlineError = null;
    });
    final r = await _api.start(
      channel: widget.channel,
      purpose: widget.purpose,
      target: widget.target,
      personId: widget.personId,
    );
    if (!mounted) return;
    if (!r.isSuccess || r.data == null) {
      setState(() {
        _starting = false;
        _inlineError = twoFactorUserMessage(
          statusCode: r.statusCode,
          errorCode: r.errorCode,
          serverMessage: r.errorMessage,
        );
      });
      return;
    }
    final d = r.data!;
    _resendAfterSeconds = d.resendAfterSeconds;
    _resendCountdown = _resendAfterSeconds;
    _resendTimer?.cancel();
    _resendTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() {
        if (_resendCountdown > 0) {
          _resendCountdown -= 1;
        }
      });
    });
    for (final c in _controllers) {
      c.clear();
    }
    setState(() {
      _starting = false;
      _challengeId = d.challengeId;
      _maskedTarget = d.maskedTarget;
      _otpauthUrl = d.otpauthUrl;
    });
    _focusNodes.first.requestFocus();
  }

  void _onDigitChanged(int index, String value) {
    final digit = value.replaceAll(RegExp(r'\D'), '');
    if (digit.isEmpty) {
      _controllers[index].text = '';
      return;
    }
    final ch = digit.substring(digit.length - 1);
    _controllers[index].text = ch;
    if (index < 5) {
      _focusNodes[index + 1].requestFocus();
    } else {
      _focusNodes[index].unfocus();
      _trySubmit();
    }
    setState(() {});
  }

  Future<void> _trySubmit() async {
    final id = _challengeId;
    if (id == null || _verifying) return;
    final code = _controllers.map((c) => c.text).join();
    if (code.length != 6) return;

    setState(() {
      _verifying = true;
      _inlineError = null;
    });
    final r = await _api.verify(
      challengeId: id,
      code: code,
      personId: widget.personId,
    );
    if (!mounted) return;
    setState(() => _verifying = false);

    if (r.isSuccess) {
      final cb = widget.onVerified;
      if (cb != null && id != null) {
        await cb(id);
      }
      if (mounted) {
        Navigator.of(context).maybePop(true);
      }
      return;
    }

    final msg = twoFactorUserMessage(
      statusCode: r.statusCode,
      errorCode: r.errorCode,
      serverMessage: r.errorMessage,
    );
    setState(() => _inlineError = msg);
    for (final c in _controllers) {
      c.clear();
    }
    _focusNodes.first.requestFocus();
  }

  @override
  Widget build(BuildContext context) {
    final title = widget.title ??
        (widget.channel == TwoFactorChannel.totp
            ? 'Code à 6 chiffres (application d’authentification)'
            : 'Code à 6 chiffres');
    final subtitle = _maskedTarget ?? '';

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppBar(
        backgroundColor: AppColors.pageBackground,
        elevation: 0,
        foregroundColor: AppColors.textPrimary,
        title: Text(
          title,
          style: const TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
          ),
        ),
      ),
      body: SafeArea(
        child: _starting
            ? const Center(child: CircularProgressIndicator.adaptive())
            : SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const SizedBox(height: AppSpacing.xl),
                    Icon(_channelIcon, size: 48, color: AppColors.blue),
                    const SizedBox(height: AppSpacing.md),
                    Text(
                      subtitle,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontSize: 15,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    if (_otpauthUrl != null && _otpauthUrl!.isNotEmpty) ...[
                      const SizedBox(height: AppSpacing.sm),
                      SelectableText(
                        _otpauthUrl!,
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                    const SizedBox(height: AppSpacing.xl),
                    FocusTraversalGroup(
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: List.generate(6, (i) {
                          return SizedBox(
                            width: 44,
                            child: TextField(
                                controller: _controllers[i],
                                focusNode: _focusNodes[i],
                                textAlign: TextAlign.center,
                                keyboardType: TextInputType.number,
                                maxLength: 1,
                                style: const TextStyle(
                                  fontSize: 22,
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.textPrimary,
                                ),
                                decoration: InputDecoration(
                                  counterText: '',
                                  filled: true,
                                  fillColor: AppColors.chatInputBg,
                                  border: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(8),
                                    borderSide: BorderSide.none,
                                  ),
                                ),
                                inputFormatters: [
                                  FilteringTextInputFormatter.digitsOnly,
                                ],
                                onChanged: (v) => _onDigitChanged(i, v),
                            ),
                          );
                        }),
                      ),
                    ),
                    if (_inlineError != null) ...[
                      const SizedBox(height: AppSpacing.md),
                      Text(
                        _inlineError!,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          color: AppColors.red,
                          fontSize: 14,
                        ),
                      ),
                    ],
                    const SizedBox(height: AppSpacing.xl),
                    if (_verifying)
                      const Center(child: CircularProgressIndicator.adaptive())
                    else if (_resendInProgress)
                      const Padding(
                        padding: EdgeInsets.symmetric(vertical: AppSpacing.sm),
                        child: Center(
                          child: SizedBox(
                            width: 28,
                            height: 28,
                            child: CircularProgressIndicator.adaptive(strokeWidth: 2.5),
                          ),
                        ),
                      )
                    else
                      TextButton(
                        onPressed: _resendCountdown > 0 || _challengeId == null
                            ? null
                            : _onResendPressed,
                        child: Text(
                          _resendCountdown > 0
                              ? 'Renvoyer le code (${_resendCountdown}s)'
                              : 'Renvoyer le code',
                          style: TextStyle(
                            color: _resendCountdown > 0
                                ? AppColors.textMuted
                                : AppColors.blue,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
      ),
    );
  }
}
