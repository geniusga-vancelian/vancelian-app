import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../design_system/design_system.dart';
import '../../../security/passcode/data/biometric_auth_service.dart';
import '../../../wallet/privy/privy_auth_provider.dart';
import '../../../wallet/privy/privy_dart_defines.dart';
import '../../data/mobile_contact_email_api.dart';
import 'edit_account_email_otp_screen.dart';

/// Écran d’édition de l’adresse e-mail du compte.
///
/// Parcours : biométrie → saisie → **pending** API → OTP Privy → **confirmed** en base.
class EditAccountEmailScreen extends StatefulWidget {
  const EditAccountEmailScreen({
    super.key,
    this.initialEmail,
  });

  final String? initialEmail;

  @override
  State<EditAccountEmailScreen> createState() => _EditAccountEmailScreenState();
}

class _EditAccountEmailScreenState extends State<EditAccountEmailScreen> {
  static final RegExp _emailRegex =
      RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$');

  static const MobileContactEmailApi _contactEmailApi = MobileContactEmailApi();

  late final TextEditingController _newEmailCtrl;
  late final TextEditingController _confirmEmailCtrl;
  late final PrivyAuthProvider _privy = createPrivyAuthProvider();

  bool _unlocked = false;
  bool _unlocking = false;
  bool _saving = false;
  String? _bannerError;
  String? _newEmailError;
  String? _confirmEmailError;

  @override
  void initState() {
    super.initState();
    _newEmailCtrl = TextEditingController();
    _confirmEmailCtrl = TextEditingController();
  }

  @override
  void dispose() {
    _newEmailCtrl.dispose();
    _confirmEmailCtrl.dispose();
    super.dispose();
  }

  String get _currentEmailDisplay {
    final v = (widget.initialEmail ?? '').trim();
    if (v.isEmpty) return 'Aucune adresse enregistrée';
    return v;
  }

  Future<void> _onUnlock() async {
    if (_unlocking) return;
    setState(() {
      _unlocking = true;
      _bannerError = null;
    });
    final bio = BiometricAuthService.instance;
    final supported = await bio.deviceSupportsBiometrics();
    if (!mounted) return;
    if (!supported) {
      setState(() {
        _unlocking = false;
        _bannerError =
            'Biométrie indisponible sur cet appareil. Pour des raisons de sécurité, '
            'la modification de l’e-mail est désactivée.';
      });
      return;
    }
    final ok = await bio.authenticate(
      reason:
          'Confirmez votre identité pour activer la modification de votre adresse e-mail.',
    );
    if (!mounted) return;
    setState(() {
      _unlocking = false;
      _unlocked = ok;
      _bannerError = null;
    });
  }

  bool _validate() {
    final email = _newEmailCtrl.text.trim();
    final confirm = _confirmEmailCtrl.text.trim();
    String? eErr;
    String? cErr;
    if (email.isEmpty) {
      eErr = 'Saisissez une adresse e-mail.';
    } else if (!_emailRegex.hasMatch(email)) {
      eErr = 'Adresse e-mail invalide.';
    }
    if (confirm.isEmpty) {
      cErr = 'Confirmez l’adresse e-mail.';
    } else if (confirm != email) {
      cErr = 'Les deux adresses doivent être identiques.';
    }
    setState(() {
      _newEmailError = eErr;
      _confirmEmailError = cErr;
    });
    return eErr == null && cErr == null;
  }

  Future<void> _onContinue() async {
    if (!_unlocked || _saving) return;
    if (!_validate()) return;

    if (!PrivyDartDefines.isConfigured) {
      setState(() {
        _bannerError =
            'Privy n’est pas configuré dans cette build (PRIVY_APP_ID). '
            'Impossible d’envoyer le code de vérification.';
      });
      return;
    }

    final email = _newEmailCtrl.text.trim();
    setState(() {
      _saving = true;
      _bannerError = null;
    });

    try {
      await _contactEmailApi.requestChange(email: email);
      await _privy.sendPrivyEmailCode(email);
      if (!mounted) return;
      setState(() => _saving = false);

      final confirmed = await Navigator.of(context).push<bool>(
            MaterialPageRoute<bool>(
              builder: (_) => EditAccountEmailOtpScreen(
                email: email,
                skipInitialSend: true,
              ),
            ),
          ) ??
          false;

      if (!mounted) return;
      if (confirmed) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Votre adresse e-mail a été confirmée et enregistrée.',
            ),
            backgroundColor: AppColors.semanticPositive,
          ),
        );
        Navigator.of(context).pop(true);
      }
    } on MobileContactEmailApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _bannerError = e.message;
      });
    } on PrivyAuthProviderException catch (e) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _bannerError = 'Envoi du code impossible : ${e.message}';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _bannerError = 'Erreur : $e';
      });
    }
  }

  Widget? _buildBannerError() {
    if (_bannerError == null) return null;
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.lg),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: AppColors.semanticDangerLight,
          borderRadius: BorderRadius.circular(AppRadius.lg),
          border: Border.all(
            color: AppColors.semanticDanger.withValues(alpha: 0.35),
          ),
        ),
        child: Text(
          _bannerError!,
          style: AppTypography.bodySmRegular
              .copyWith(color: AppColors.textPrimary),
        ),
      ),
    );
  }

  Widget _buildUnlockBody() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Adresse actuelle',
          style: AppTypography.itemPrimary.copyWith(color: AppColors.textPrimary),
        ),
        const SizedBox(height: AppSpacing.sm),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(AppRadius.lg),
          ),
          child: Text(
            _currentEmailDisplay,
            style:
                AppTypography.bodyRegular.copyWith(color: AppColors.textPrimary),
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        if (_buildBannerError() != null) _buildBannerError()!,
        Text(
          'Pour des raisons de sécurité, la modification de votre adresse '
          'e-mail nécessite une vérification biométrique (Face ID, Touch ID '
          'ou empreinte).',
          style: GoogleFonts.inter(
            fontSize: 15,
            fontWeight: FontWeight.w400,
            height: 22 / 15,
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildEditBody() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Adresse actuelle',
          style: AppTypography.itemPrimary.copyWith(color: AppColors.textPrimary),
        ),
        const SizedBox(height: AppSpacing.sm),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(AppRadius.lg),
          ),
          child: Text(
            _currentEmailDisplay,
            style:
                AppTypography.bodyRegular.copyWith(color: AppColors.textPrimary),
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        if (_buildBannerError() != null) _buildBannerError()!,
        Text(
          'Nouvelle adresse',
          style: AppTypography.itemPrimary.copyWith(color: AppColors.textPrimary),
        ),
        const SizedBox(height: AppSpacing.sm),
        AppTextInput(
          label: 'Nouvelle adresse e-mail',
          controller: _newEmailCtrl,
          keyboardType: TextInputType.emailAddress,
          textInputAction: TextInputAction.next,
          showEmailIcon: true,
          showClearButton: true,
          error: _newEmailError,
        ),
        const SizedBox(height: AppSpacing.md),
        AppTextInput(
          label: 'Confirmer la nouvelle adresse',
          controller: _confirmEmailCtrl,
          keyboardType: TextInputType.emailAddress,
          textInputAction: TextInputAction.done,
          showEmailIcon: true,
          showClearButton: true,
          error: _confirmEmailError,
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(
          'Un code à six chiffres sera envoyé à cette adresse e-mail. '
          'Ce n’est qu’après l’étape de validation du code que votre '
          'nouvelle adresse e-mail sera enregistrée.',
          style: GoogleFonts.inter(
            fontSize: 15,
            fontWeight: FontWeight.w400,
            height: 22 / 15,
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final bottomSafe = MediaQuery.paddingOf(context).bottom;

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      resizeToAvoidBottomInset: true,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.back,
        onBackTap: () => Navigator.of(context).maybePop(),
        backgroundColor: AppColors.pageBackground,
        useDashboardStyle: true,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: AppSpacing.md),
              const AppPageTitle('Modifier l’e-mail'),
              const SizedBox(height: AppSpacing.pageDescriptionToFirstField),
              Expanded(
                child: SingleChildScrollView(
                  keyboardDismissBehavior:
                      ScrollViewKeyboardDismissBehavior.onDrag,
                  child: _unlocked ? _buildEditBody() : _buildUnlockBody(),
                ),
              ),
              AppPrimaryButton(
                label: _unlocked
                    ? (_saving
                        ? 'Envoi en cours…'
                        : 'Envoyer le code de vérification')
                    : (_unlocking
                        ? 'Vérification en cours…'
                        : 'Déverrouiller pour modifier'),
                size: AppPrimaryButtonSize.large,
                isLoading: _unlocked ? _saving : _unlocking,
                onPressed: _unlocked
                    ? (_saving ? null : _onContinue)
                    : (_unlocking ? null : _onUnlock),
              ),
              SizedBox(height: bottomSafe > 0 ? bottomSafe : AppSpacing.md),
            ],
          ),
        ),
      ),
    );
  }
}
