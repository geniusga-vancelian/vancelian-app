import 'dart:async';
import 'dart:ui';

import 'package:animations/animations.dart';
import 'package:circle_flags/circle_flags.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:permission_handler/permission_handler.dart';

import 'package:arquantix_news/features/app_entry/application/app_entry_bootstrap.dart';

import '../../../core/session_identity_context.dart';
import '../../../core/app_warmup_service.dart';
import '../../../core/startup/registration_surface_primer.dart';
import '../../../core/config.dart' as app_config;
import '../../security/passcode/data/session_service.dart';
import '../../../core/phone_e164.dart';
import '../../../design_system/atoms/app_colors.dart';
import '../../../design_system/atoms/app_spacing.dart';
import '../../../design_system/atoms/app_typography.dart';
import '../../../design_system/components/app_page_title.dart';
import '../../../design_system/components/app_phone_input.dart';
import '../../../design_system/components/app_primary_button.dart';
import '../../../design_system/components/app_top_nav_bar.dart';
import '../../../design_system/components/ds_permission_prompt.dart';
import '../../../design_system/components/ds_stepper_avatar.dart';
import '../../../design_system/components/ds_validation_result_body.dart';
import '../../../design_system/components/modale.dart';
import '../data/registration_api.dart';
import '../data/registration_form_hydration.dart';
import '../data/registration_models.dart';
import '../registration_phone_format_validation.dart';
import '../registration_phone_user_errors.dart';
import '../widgets/registration_address_step.dart'
    show
        kRegAddressSurfaceEditing,
        kRegAddressSurfaceNeedCountry,
        kRegAddressSurfaceSearchOnly,
        kRegAddressStepSurfaceKey;
import '../widgets/registration_flow_renderer.dart';
import '../widgets/registration_phone_sms_otp_panel.dart';
import '../../profile/application/security_preferences_coordinator.dart';
import '../../security/onboarding/push_notifications_onboarding_screen.dart';
import '../../security/onboarding/push_notification_permission_coordinator.dart';
import '../../security/passcode/data/passcode_service.dart';

const _inputComponentTypes = {
  'text_input', 'phone_input', 'select', 'country_picker',
  'date_picker', 'checkbox', 'multi_select',
  'address_autocomplete',
  'address_step',
};

/// Code métier [RegistrationApi] quand le backend refuse un nouveau ``sessions/start``.
const _kRegistrationAlreadyCompletedErrorCode = 'registration_already_completed';

const _phoneSubmitErrorCodes = {
  'invalid_phone_number',
  'unsupported_phone_country',
  'phone_country_mismatch',
  'phone_number_not_mobile',
};

class RegistrationFlowScreen extends StatefulWidget {
  const RegistrationFlowScreen({
    super.key,
    required this.jurisdiction,
    this.baseUrl,
    this.showDebugPanel = false,
    /// Si null, utilise [SessionIdentityContext.personId] (JWT) pour reprendre la session serveur.
    this.personId,
    /// Flux poussé comme seule route (ex. après PIN) : fermer ramène au shell, pas [Navigator.pop].
    this.rootPresentation = false,
  });

  final String jurisdiction;
  final String? baseUrl;
  final bool showDebugPanel;
  final String? personId;
  final bool rootPresentation;

  @override
  State<RegistrationFlowScreen> createState() =>
      _RegistrationFlowScreenState();
}

class _RegistrationFlowScreenState extends State<RegistrationFlowScreen>
    with WidgetsBindingObserver {
  late final RegistrationApi _api;

  bool _loading = true;
  bool _submitting = false;
  String? _errorMessage;

  /// Retour depuis Réglages iOS/Android après [openAppSettings] (notifications).
  bool _awaitingPushSettingsResume = false;

  RegistrationSessionState? _session;
  Map<String, dynamic> _formData = {};
  Map<String, String> _fieldErrors = {};
  final Map<String, TextEditingController> _controllers = {};
  final Map<String, FocusNode> _focusNodes = {};

  final ScrollController _scrollController = ScrollController();
  double _navTitleOpacity = 0;

  /// Auto-avance ~150 ms après sélection (liste single : emploi, secteur, revenus, patrimoine).
  Timer? _singleSelectAutoAdvanceTimer;

  static const _autoAdvanceSingleSelectSlugs = {
    'employment_status',
    'work_sector',
    'annual_income_range',
    'net_worth_range',
  };

  bool _debugExpanded = false;

  /// false = avant (comme push iOS), true = retour (comme pop).
  bool _navReverse = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _api = RegistrationApi(
      baseUrl: widget.baseUrl ?? app_config.Config.marketDataBaseUrl,
      accessTokenResolver: SessionService.instance.readAccessToken,
    );
    _scrollController.addListener(_onScroll);
    _startFlow();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      unawaited(AppWarmupService.instance.scheduleDuringIntro(context));
      // Second passage si l’overlay n’était pas prêt pendant le warmup global.
      unawaited(RegistrationSurfacePrimer.prime(context));
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _singleSelectAutoAdvanceTimer?.cancel();
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    for (final c in _controllers.values) {
      c.dispose();
    }
    for (final f in _focusNodes.values) {
      f.dispose();
    }
    super.dispose();
  }

  void _onScroll() {
    final offset =
        _scrollController.hasClients ? _scrollController.offset : 0.0;
    final next = ((offset - 24) / 40).clamp(0.0, 1.0);
    if ((next - _navTitleOpacity).abs() > 0.02) {
      setState(() => _navTitleOpacity = next);
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    super.didChangeAppLifecycleState(state);
    if (state == AppLifecycleState.resumed) {
      unawaited(_onRegistrationResumedCheckPushPermission());
    }
  }

  Future<void> _onRegistrationResumedCheckPushPermission() async {
    if (!_awaitingPushSettingsResume || _submitting) return;
    final screen = _session?.screen;
    if (screen == null ||
        !screen.isPermissionPromptScreen ||
        screen.permissionKind != 'push_notifications') {
      return;
    }
    final st = await Permission.notification.status;
    if (!mounted) return;
    if (!(st.isGranted || st.isLimited || st.isProvisional)) return;
    setState(() => _awaitingPushSettingsResume = false);
    await _submitPermissionChoice(true, skipOsPrompt: true);
  }

  // ─── Text controller management ─────────────────────────────────────────

  void _syncControllers(RegistrationSessionState state) {
    final screen = state.screen;
    if (screen == null) return;

    for (final comp in screen.components) {
      if (comp.componentType == 'address_autocomplete') {
        final bs = comp.props['binding_slugs'];
        final defaults = {
          'street': 'address_line_1',
          'postal': 'postal_code',
          'city': 'city',
        };
        for (final k in ['street', 'postal', 'city']) {
          String slug = defaults[k]!;
          if (bs is Map && bs[k] is String && (bs[k] as String).isNotEmpty) {
            slug = bs[k] as String;
          }
          final initialValue = (_formData[slug] as String?) ?? '';
          if (!_controllers.containsKey(slug)) {
            _controllers[slug] = TextEditingController(text: initialValue);
          }
          if (!_focusNodes.containsKey(slug)) {
            _focusNodes[slug] = FocusNode();
          }
        }
        continue;
      }
      if (comp.componentType == 'address_step') {
        final bs = comp.props['binding_slugs'];
        const keys = [
          'postal_code',
          'address_line_1',
          'address_line_2',
          'city',
        ];
        const defaults = {
          'postal_code': 'postal_code',
          'address_line_1': 'address_line_1',
          'address_line_2': 'address_line_2',
          'city': 'city',
        };
        for (final k in keys) {
          var slug = defaults[k]!;
          if (bs is Map && bs[k] is String && (bs[k] as String).isNotEmpty) {
            slug = bs[k] as String;
          }
          final initialValue = (_formData[slug] as String?) ?? '';
          if (!_controllers.containsKey(slug)) {
            _controllers[slug] = TextEditingController(text: initialValue);
          }
          if (!_focusNodes.containsKey(slug)) {
            _focusNodes[slug] = FocusNode();
          }
        }
        continue;
      }
      if (comp.bindingSlug == null) continue;
      final slug = comp.bindingSlug!;
      final needsController = comp.componentType == 'text_input' ||
          comp.componentType == 'phone_input';
      if (!needsController) continue;

      final initialValue = (_formData[slug] as String?) ?? '';

      if (!_controllers.containsKey(slug)) {
        _controllers[slug] = TextEditingController(text: initialValue);
      }
      if (!_focusNodes.containsKey(slug)) {
        _focusNodes[slug] = FocusNode();
      }
    }
  }

  // ─── API flow ───────────────────────────────────────────────────────────

  Future<void> _startFlow() async {
    setState(() {
      _loading = true;
      _errorMessage = null;
    });

    final result = await _api.startSession(
      jurisdiction: widget.jurisdiction,
      // Avec Bearer, le backend résout `person_id` depuis le JWT ; utile pour tests / override explicite.
      personId: widget.personId ?? SessionIdentityContext.instance.personId,
    );
    if (!mounted) return;

    if (result.isSuccess && result.data != null) {
      _navReverse = false;
      _applySessionData(result.data!);
    } else if (result.statusCode == 409 &&
        result.errorCode == _kRegistrationAlreadyCompletedErrorCode) {
      setState(() => _loading = false);
      await _showRegistrationAlreadyCompletedModal();
      if (!mounted) return;
      Navigator.of(context).pop();
      return;
    } else {
      _errorMessage = result.errorMessage ?? 'Failed to start session';
    }

    setState(() => _loading = false);
  }

  Future<void> _showRegistrationAlreadyCompletedModal() async {
    await Modale.show<void>(
      context,
      const ModaleParams(
        title: 'Inscription déjà terminée',
        description:
            'Votre compte a déjà été créé. Vous pouvez continuer à utiliser l’application.',
        primaryButton: ModaleButtonConfig(
          label: 'OK',
        ),
      ),
    );
  }

  String? _phoneFieldSlug(RegistrationScreen? screen) {
    if (screen == null) return null;
    for (final c in screen.components) {
      if (c.componentType == 'phone_input') return c.bindingSlug;
    }
    return null;
  }

  /// Aperçu modale confirmation : affichage uniquement (le backend valide au submit).
  String _formatConfirmPhonePreview(String nationalOrFull, String isoAlpha2) {
    final t = nationalOrFull.trim();
    if (t.isEmpty) return '';
    if (t.startsWith('+')) {
      return _formatConfirmPhoneLine(t, isoAlpha2);
    }
    final dial = phoneDialCodeForIso(isoAlpha2);
    final e164 = normalizePhoneFieldToE164(t, dial);
    if (e164.isEmpty) return dial;
    return _formatConfirmPhoneLine(e164, isoAlpha2);
  }

  /// Affiche le numéro type E.164 avec espaces (national groupé par 3).
  String _formatConfirmPhoneLine(String e164, String isoAlpha2) {
    final dial = phoneDialCodeForIso(isoAlpha2).replaceAll('+', '');
    var digits = e164.trim();
    if (digits.startsWith('+')) digits = digits.substring(1);
    digits = digits.replaceAll(RegExp(r'\D'), '');
    if (digits.isEmpty) return e164.trim();

    var national = digits;
    if (digits.startsWith(dial)) {
      national = digits.substring(dial.length);
    }
    // Trunk national `0` (ex. FR 06… → 6…) parfois présent après l’indicatif si concat erroné.
    if (national.startsWith('0') && national.length > 1) {
      national = national.substring(1);
    }
    final dialOut = '+$dial';
    if (national.isEmpty) return dialOut;

    final buf = StringBuffer();
    for (var i = 0; i < national.length; i++) {
      if (i > 0 && i % 3 == 0) buf.write(' ');
      buf.write(national[i]);
    }
    return '$dialOut ${buf.toString()}'.trim();
  }

  /// Textes modale téléphone depuis `screen.config` (clés `phone_confirm_modal_*_i18n`), sinon [fallback].
  String _resolvePhoneConfirmModalText(
    Map<String, dynamic>? config,
    String mapKey,
    String fallback,
  ) {
    final raw = config?[mapKey];
    if (raw is! Map) return fallback;
    final map = Map<String, dynamic>.from(raw);
    String pick(String code) {
      final v = map[code];
      return v is String ? v.trim() : '';
    }
    final lang = Localizations.localeOf(context).languageCode;
    for (final code in [lang, 'en', 'fr']) {
      final t = pick(code);
      if (t.isNotEmpty) return t;
    }
    return fallback;
  }

  /// Format client d’abord ; si OK et modale activée → confirmation ; sinon envoi direct.
  Future<void> _submitWithPhoneConfirmIfNeeded() async {
    final screen = _session?.screen;
    final slug = _phoneFieldSlug(screen);
    if (slug == null || screen?.screenType == 'interaction') {
      await _submitAndAdvance();
      return;
    }

    final raw = (_formData['${slug}_raw'] as String?)?.trim() ??
        (_formData[slug] as String?)?.trim() ??
        '';
    if (raw.isEmpty) {
      await _submitAndAdvance();
      return;
    }

    FocusScope.of(context).unfocus();
    final iso =
        ((_formData['${slug}_country_code'] as String?) ?? 'FR').toUpperCase();

    if (!isRegistrationPhoneFormatValid(raw, iso)) {
      if (!mounted) return;
      await _showPhoneValidationErrorModal('invalid_phone_number');
      return;
    }

    if (screen != null && !screen.phoneConfirmModalEnabled) {
      await _submitAndAdvance();
      return;
    }

    if (!mounted) return;
    final formatted = _formatConfirmPhonePreview(raw, iso);
    final cfg = screen?.config;
    await Modale.show<void>(
      context,
      ModaleParams(
        title: _resolvePhoneConfirmModalText(
          cfg,
          'phone_confirm_modal_title_i18n',
          'Is this number correct?',
        ),
        description: _resolvePhoneConfirmModalText(
          cfg,
          'phone_confirm_modal_description_i18n',
          "We'll send you a confirmation code there",
        ),
        content: Padding(
          padding: const EdgeInsets.only(top: AppSpacing.sm),
          child: Wrap(
            alignment: WrapAlignment.center,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 10,
            runSpacing: 8,
            children: [
              CircleFlag(iso.toLowerCase(), size: 32),
              Text(
                formatted,
                style: AppTypography.sectionTitle.copyWith(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.4,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
        ),
        primaryButton: ModaleButtonConfig(
          label: _resolvePhoneConfirmModalText(
            cfg,
            'phone_confirm_modal_confirm_label_i18n',
            'Confirm',
          ),
          onTapAsync: () async {
            if (mounted) await _submitAndAdvance();
          },
        ),
        secondaryButton: ModaleButtonConfig(
          label: _resolvePhoneConfirmModalText(
            cfg,
            'phone_confirm_modal_back_label_i18n',
            'Go back',
          ),
        ),
      ),
    );
  }

  Future<void> _showPhoneValidationErrorModal(
    String? code, {
    String? messageHint,
  }) async {
    await Modale.show<void>(
      context,
      ModaleParams(
        title: '',
        content: DsValidationResultBody(
          status: DsStepperAvatarStatus.error,
          progress: 100,
          headline: RegistrationPhoneUserErrors.titleForCode(code),
          messageTitle: RegistrationPhoneUserErrors.messageForCode(code),
          messageCaption: messageHint,
        ),
        primaryButton: ModaleButtonConfig(
          label: RegistrationPhoneUserErrors.primaryButtonLabelForCode(code),
        ),
      ),
    );
    if (!mounted) return;
    final slug = _phoneFieldSlug(_session?.screen);
    if (slug != null) {
      final fn = _focusNodes[slug];
      if (fn != null && fn.canRequestFocus) {
        fn.requestFocus();
      }
    }
  }

  Future<void> _submitAndAdvance() async {
    if (_session == null) return;
    _navReverse = false;
    setState(() {
      _submitting = true;
      _fieldErrors = {};
      _errorMessage = null;
    });

    final result = await _api.submitScreen(_session!.sessionId, _formData);
    if (!mounted) return;

    if (result.isSuccess && result.data != null) {
      _applySessionData(result.data!);
    } else if (result.isValidationError) {
      final phoneSlug = _phoneFieldSlug(_session?.screen);
      final code = result.errorCode;
      final field = result.fieldSlug;
      if (phoneSlug != null &&
          field == phoneSlug &&
          code != null &&
          _phoneSubmitErrorCodes.contains(code)) {
        await _showPhoneValidationErrorModal(
          code,
          messageHint: result.messageHint,
        );
      } else if (result.fieldErrors != null && result.fieldErrors!.isNotEmpty) {
        _fieldErrors = result.fieldErrors!;
        _errorMessage = null;
      } else {
        _errorMessage = result.errorMessage;
      }
    } else if (result.isBlocked) {
      _errorMessage = result.errorMessage ??
          'Veuillez compléter les informations requises avant de continuer.';
    } else {
      _errorMessage = result.errorMessage ?? 'Error';
    }

    setState(() => _submitting = false);
  }

  Future<void> _goNext() async {
    if (_session == null) return;
    _navReverse = false;
    setState(() {
      _submitting = true;
      _errorMessage = null;
    });

    final result = await _api.nextScreen(_session!.sessionId);
    if (!mounted) return;

    if (result.isSuccess && result.data != null) {
      _applySessionData(result.data!);
    } else {
      _errorMessage = result.errorMessage ?? 'Cannot advance';
    }

    setState(() => _submitting = false);
  }

  Future<void> _goPrev() async {
    if (_session == null) return;
    _navReverse = true;
    setState(() {
      _submitting = true;
      _errorMessage = null;
    });

    final result = await _api.prevScreen(_session!.sessionId);
    if (!mounted) return;

    if (result.isSuccess && result.data != null) {
      _applySessionData(result.data!);
    } else {
      _errorMessage = result.errorMessage ?? 'Cannot go back';
    }

    setState(() => _submitting = false);
  }

  /// Dernier écran : une seule action — persister (submit) puis compléter la session.
  /// [unfocus] évite que le premier tap ne serve seulement à fermer le clavier.
  Future<void> _onLastScreenPrimaryTap() async {
    FocusScope.of(context).unfocus();
    if (_session == null || _submitting) return;

    final hasFormFields = _session!.screen?.components
            .any((c) => _inputComponentTypes.contains(c.componentType)) ??
        false;

    if (hasFormFields) {
      await _submitWithPhoneConfirmIfNeeded();
    }
    if (!mounted) return;
    if (_fieldErrors.isNotEmpty || _errorMessage != null) return;
    await _completeSession();
  }

  Future<void> _completeSession() async {
    if (_session == null) return;
    final screenBeforeComplete = _session!.screen;
    setState(() {
      _submitting = true;
      _errorMessage = null;
    });

    final result = await _api.completeSession(_session!.sessionId);
    if (!mounted) return;

    if (result.isSuccess) {
      if (screenBeforeComplete?.showSuccessModalOnComplete == true) {
        final sm = screenBeforeComplete!.successModalConfig;
        final title = (sm?['title'] as String?)?.trim();
        final desc = (sm?['description'] as String?) ?? '';
        final primary = (sm?['primary_label'] as String?)?.trim();
        await Modale.show<void>(
          context,
          ModaleParams(
            title: (title != null && title.isNotEmpty)
                ? title
                : 'Profile updated successfully',
            description: desc,
            primaryButton: ModaleButtonConfig(
              label: (primary != null && primary.isNotEmpty)
                  ? primary
                  : 'Continue',
            ),
          ),
        );
      }
      if (!mounted) return;
      // PIN déjà créé dans cette session — pas de 3ᵉ saisie ; JWT = client signup (voir bootstrap home).
      await AppEntryBootstrap.pushRootReplacingAll(
        context,
        forcePostAuthUnlock: false,
        skipPasscodeUnlock: true,
        suppressNextMainShellPushReloginPrompt: true,
      );
      return;
    }
    _errorMessage = result.errorMessage ?? 'Cannot complete';
    setState(() => _submitting = false);
  }

  // ─── State application ──────────────────────────────────────────────────

  void _applySessionData(Map<String, dynamic> raw) {
    final state = RegistrationSessionState.fromJson(raw);
    _session = state;
    _fieldErrors = {};
    _errorMessage = null;

    _formData = hydrateRegistrationFormData(state);

    _syncControllers(state);

    if (_scrollController.hasClients) {
      _scrollController.jumpTo(0);
    }
    _navTitleOpacity = 0;
  }

  Future<void> _refreshSession() async {
    final sid = _session?.sessionId;
    if (sid == null) return;
    final r = await _api.getCurrentScreen(sid);
    if (!mounted) return;
    if (r.isSuccess && r.data != null) {
      _applySessionData(r.data!);
    }
  }

  void _onFieldChanged(MapEntry<String, dynamic> entry) {
    setState(() {
      _formData[entry.key] = entry.value;
      _fieldErrors.remove(entry.key);
      if (entry.key.endsWith('_country_code')) {
        final iso2Key =
            entry.key.replaceAll('_country_code', '_country_iso2');
        _formData[iso2Key] = entry.value;
        _fieldErrors.remove(iso2Key);
      }
    });
    _scheduleAutoAdvanceAfterSingleSelect(entry.key);
  }

  void _scheduleAutoAdvanceAfterSingleSelect(String slug) {
    if (!_autoAdvanceSingleSelectSlugs.contains(slug)) return;
    _singleSelectAutoAdvanceTimer?.cancel();
    _singleSelectAutoAdvanceTimer = Timer(const Duration(milliseconds: 150), () {
      if (!mounted) return;
      if (_submitting) return;
      final v = _formData[slug];
      if (v == null) return;
      if (v is String && v.trim().isEmpty) return;
      _submitWithPhoneConfirmIfNeeded();
    });
  }

  void _onPhoneNationalChanged(String slug, String value) {
    setState(() {
      _formData[slug] = value;
      _formData['${slug}_raw'] = value;
      _fieldErrors.remove(slug);
      _fieldErrors.remove('${slug}_raw');
    });
  }

  Future<void> _dismissRegistrationFlow() async {
    if (!mounted) return;
    if (widget.rootPresentation) {
      await AppEntryBootstrap.pushRootReplacingAll(
        context,
        forcePostAuthUnlock: false,
        skipPasscodeUnlock: true,
        suppressNextMainShellPushReloginPrompt: true,
      );
    } else {
      Navigator.of(context).pop();
    }
  }

  // ─── Build ──────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final session = _session;
    final isFirst = session?.isFirstScreen ?? true;
    final screenTitle = session?.screen?.title ?? '';
    final isPermission = session?.screen?.isPermissionPromptScreen == true;

    final scaffold = Scaffold(
      backgroundColor:
          isPermission ? AppColors.iosChromeBackground : AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType:
            isFirst ? AppTopNavBarLeading.close : AppTopNavBarLeading.back,
        onCloseTap: isFirst ? _dismissRegistrationFlow : null,
        onBackTap: isFirst ? null : (_submitting ? null : _goPrev),
        title: (!isPermission && screenTitle.isNotEmpty) ? screenTitle : null,
        titleOpacity: _navTitleOpacity,
        centerTitle: false,
        titleTextStyle: AppTypography.paragraph.copyWith(
          color: AppColors.textPrimary,
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(color: AppColors.indigo))
          : session == null
              ? _buildFatalError()
              : _buildFlowContent(),
    );

    if (widget.rootPresentation && isFirst) {
      return PopScope(
        canPop: false,
        onPopInvokedWithResult: (bool didPop, dynamic result) async {
          if (didPop) return;
          await _dismissRegistrationFlow();
        },
        child: scaffold,
      );
    }
    return scaffold;
  }

  Widget _buildFatalError() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline_rounded,
                size: 48, color: AppColors.semanticDanger),
            const SizedBox(height: 16),
            Text(
              _errorMessage ?? 'An error occurred',
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(
                  fontSize: 15, color: AppColors.textSecondary),
            ),
            const SizedBox(height: 24),
            AppPrimaryButton(
              label: 'Retry',
              onPressed: _startFlow,
              shrinkWrap: true,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFlowContent() {
    final session = _session!;
    final screen = session.screen;
    final transitionKey =
        '${screen?.id ?? session.sessionId}_${screen?.screenType ?? ""}';

    return PageTransitionSwitcher(
      duration: const Duration(milliseconds: 320),
      reverse: _navReverse,
      transitionBuilder: (
        Widget child,
        Animation<double> primaryAnimation,
        Animation<double> secondaryAnimation,
      ) {
        return SharedAxisTransition(
          animation: primaryAnimation,
          secondaryAnimation: secondaryAnimation,
          transitionType: SharedAxisTransitionType.horizontal,
          fillColor: AppColors.pageBackground,
          child: child,
        );
      },
      child: KeyedSubtree(
        key: ValueKey<String>(transitionKey),
        child: _buildFlowPage(session),
      ),
    );
  }

  Future<void> _submitPermissionChoice(
    bool enabled, {
    bool skipOsPrompt = false,
  }) async {
    final sess = _session;
    final screen = sess?.screen;
    if (sess == null || screen == null || !screen.isPermissionPromptScreen) {
      return;
    }
    final slug = screen.permissionDecisionSlug;
    if (slug == null || slug.isEmpty) {
      setState(() => _errorMessage = 'Configuration écran permission invalide.');
      return;
    }
    setState(() {
      _submitting = true;
      _errorMessage = null;
    });

    if (enabled &&
        screen.permissionKind == 'push_notifications' &&
        !skipOsPrompt) {
      final outcome = await PushNotificationPermissionCoordinator.request();
      if (!mounted) return;
      switch (outcome) {
        case PushNotificationPermissionOutcome.granted:
          break;
        case PushNotificationPermissionOutcome.navigatedToSettings:
          setState(() {
            _awaitingPushSettingsResume = true;
            _submitting = false;
          });
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text(
                'Dans Réglages, activez les notifications pour cette app puis revenez — l’inscription reprendra automatiquement.',
              ),
              behavior: SnackBarBehavior.floating,
              margin: EdgeInsets.all(16),
            ),
          );
          return;
        case PushNotificationPermissionOutcome.denied:
          setState(() => _submitting = false);
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text(
                'Autorisation non accordée. Réessayez ou activez les notifications dans les réglages système.',
              ),
              behavior: SnackBarBehavior.floating,
              margin: EdgeInsets.all(16),
            ),
          );
          return;
      }
    }

    final result = await _api.submitScreen(sess.sessionId, {slug: enabled});
    if (!mounted) return;
    if (result.isSuccess && result.data != null) {
      _applySessionData(result.data!);
    } else {
      setState(() {
        _errorMessage = result.errorMessage ?? 'Erreur';
      });
    }
    setState(() => _submitting = false);
  }

  Widget _buildPermissionPromptPage(RegistrationSessionState session) {
    final screen = session.screen!;
    final hero = screen.permissionKind == 'push_notifications'
        ? const DsPermissionHero(
            symbol: Icon(
              Icons.notifications_active_outlined,
              size: 64,
              color: AppColors.indigo,
            ),
            symbolSize: 72,
          )
        : const DsPermissionHero();

    return ColoredBox(
      color: AppColors.iosChromeBackground,
      child: CustomScrollView(
        controller: _scrollController,
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          SliverToBoxAdapter(
            child: DsPermissionPromptLayout(
              showStatusBar: false,
              minContentHeight: 100,
              title: screen.title,
              body: screen.subtitle ?? '',
              hero: hero,
              primaryButton: AppPrimaryButton(
                label: screen.buttonLabel ?? 'Continue',
                isLoading: _submitting,
                onPressed:
                    _submitting ? null : () => _submitPermissionChoice(true),
              ),
              secondaryButton: AppPrimaryButton(
                label: screen.permissionSecondaryButtonLabel,
                variant: AppPrimaryButtonVariant.secondary,
                onPressed:
                    _submitting ? null : () => _submitPermissionChoice(false),
              ),
            ),
          ),
          if (_errorMessage != null)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.pageEdge,
                ),
                child: Text(
                  _errorMessage!,
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    color: AppColors.errorText,
                  ),
                ),
              ),
            ),
          SliverToBoxAdapter(
            child: SizedBox(height: 16 + MediaQuery.paddingOf(context).bottom),
          ),
        ],
      ),
    );
  }

  Widget _buildFlowPage(RegistrationSessionState session) {
    final screen = session.screen;

    if (screen != null && screen.isPermissionPromptScreen) {
      return _buildPermissionPromptPage(session);
    }

    final isPhoneInteraction = screen != null &&
        screen.screenType == 'interaction' &&
        screen.interactionType == 'phone_verification_sms';

    final inputComponents = screen?.components
            .where((c) => _inputComponentTypes.contains(c.componentType))
            .toList() ??
        [];

    final screenProvidesPageHeading = screen != null &&
        (screen.title.trim().isNotEmpty ||
            (screen.subtitle?.trim().isNotEmpty ?? false));

    return Stack(
      children: [
        CustomScrollView(
          controller: _scrollController,
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.manual,
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            const SliverToBoxAdapter(
                child: SizedBox(height: AppSpacing.md)),

            if (screen != null && screen.title.isNotEmpty)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.pageEdge),
                  child: AppPageTitle(screen.title),
                ),
              ),

            if (screen?.subtitle != null &&
                screen!.subtitle!.isNotEmpty &&
                !isPhoneInteraction)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.only(
                    left: AppSpacing.pageEdge,
                    right: AppSpacing.pageEdge,
                    top: AppSpacing.sm,
                  ),
                  child: Text(
                    screen.subtitle!,
                    style: GoogleFonts.inter(
                      fontSize: 15,
                      fontWeight: FontWeight.w400,
                      height: 22 / 15,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ),
              ),

            SliverToBoxAdapter(
              child: SizedBox(
                height: isPhoneInteraction
                    ? AppSpacing.sm
                    : AppSpacing.pageDescriptionToFirstField,
              ),
            ),

            if (isPhoneInteraction)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.pageEdge,
                  ),
                  child: RegistrationPhoneSmsOtpPanel(
                    key: ValueKey(screen.id),
                    screen: screen,
                    sessionId: session.sessionId,
                    registrationApi: _api,
                    collectedData: session.collectedData,
                    onGoBack: _goPrev,
                    onCompleted: () async {
                      await _refreshSession();
                      if (!mounted) return;
                      await PasscodeService.instance.init();
                      final pushLocal = await PasscodeService.instance
                          .getPushOnboardingPromptState();
                      final lastPrompt = await PasscodeService.instance
                          .getLastAutomaticPushOnboardingPromptAt();
                      // Filet : le gate principal est [PostLoginLocalSecurityFlow] après OTP.
                      if (SecurityPreferencesCoordinator
                              .shouldOfferRegistrationPushOnboarding(
                            pushLocal,
                            lastAutomaticPromptAt: lastPrompt,
                          ) &&
                          mounted) {
                        await Navigator.of(context).push<void>(
                          MaterialPageRoute<void>(
                            fullscreenDialog: true,
                            builder: (_) => const PushNotificationsOnboardingScreen(
                              kind: PushNotificationsOnboardingKind.registration,
                            ),
                          ),
                        );
                      }
                      if (mounted) await _goNext();
                    },
                  ),
                ),
              ),

            if (inputComponents.isNotEmpty)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.pageEdge),
                  child: RegistrationFlowRenderer(
                    components: inputComponents,
                    formData: _formData,
                    controllers: _controllers,
                    focusNodes: _focusNodes,
                    onFieldChanged: _onFieldChanged,
                    onPhoneNationalChanged: _onPhoneNationalChanged,
                    errors: _fieldErrors,
                    registrationApi: _api,
                    screenProvidesPageHeading: screenProvidesPageHeading,
                    onFormPatch: (patch) {
                      setState(() => _formData.addAll(patch));
                    },
                  ),
                ),
              ),

            if (_errorMessage != null)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.pageEdge),
                  child: Container(
                    width: double.infinity,
                    margin: const EdgeInsets.only(top: AppSpacing.md),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppColors.errorBackground,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      _errorMessage!,
                      style: GoogleFonts.inter(
                        fontSize: 13,
                        color: AppColors.errorText,
                      ),
                    ),
                  ),
                ),
              ),

            if (widget.showDebugPanel)
              SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.only(
                      left: AppSpacing.pageEdge,
                    right: AppSpacing.pageEdge,
                    top: AppSpacing.xxl,
                  ),
                  child: _buildDebugPanel(session),
                ),
              ),

            // Bottom padding to clear the fixed CTA
            SliverToBoxAdapter(
              child: SizedBox(
                height: 100 + MediaQuery.paddingOf(context).bottom,
              ),
            ),
          ],
        ),

        // Fixed bottom CTA with blur
        Positioned(
          left: 0,
          right: 0,
          bottom: 0,
          child: _buildBottomCta(session),
        ),
      ],
    );
  }

  // ─── Bottom CTA with blur ─────────────────────────────────────────────

  Widget _buildBottomCta(RegistrationSessionState session) {
    if (session.screen?.isPermissionPromptScreen == true) {
      return const SizedBox.shrink();
    }
    final bottomInset = MediaQuery.paddingOf(context).bottom;

    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
        child: Container(
          width: double.infinity,
          padding: EdgeInsets.fromLTRB(
            AppSpacing.pageEdge,
            2,
            AppSpacing.pageEdge,
            AppSpacing.md + bottomInset,
          ),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                AppColors.pageBackground.withValues(alpha: 0.0),
                AppColors.pageBackground.withValues(alpha: 0.72),
                AppColors.pageBackground.withValues(alpha: 0.94),
              ],
            ),
          ),
          child: _buildCtaButton(session),
        ),
      ),
    );
  }

  bool get _allRequiredFilled {
    final screen = _session?.screen;
    if (screen == null) return true;
    if (screen.screenType == 'interaction') return true;
    if (screen.isPermissionPromptScreen) return true;

    for (final comp in screen.components) {
      if (!_inputComponentTypes.contains(comp.componentType)) continue;
      if (!comp.isRequired) continue;

      if (comp.componentType == 'address_autocomplete') {
        final bs = comp.props['binding_slugs'];
        final def = {
          'street': 'address_line_1',
          'postal': 'postal_code',
          'city': 'city',
          'country': 'country_of_residence',
        };
        for (final k in def.keys) {
          var slug = def[k]!;
          if (bs is Map && bs[k] is String && (bs[k] as String).isNotEmpty) {
            slug = bs[k] as String;
          }
          final value = _formData[slug];
          if (value == null) return false;
          if (value is String && value.trim().isEmpty) return false;
        }
        continue;
      }
      if (comp.componentType == 'address_step') {
        final surface = _formData[kRegAddressStepSurfaceKey]?.toString();
        final bs = comp.props['binding_slugs'];
        final line2Optional = comp.props['address_line_2_optional'] != false;
        final def = {
          'postal_code': 'postal_code',
          'address_line_1': 'address_line_1',
          'address_line_2': 'address_line_2',
          'city': 'city',
          'country_of_residence': 'country_of_residence',
        };
        String slugFor(String k) {
          var slug = def[k]!;
          if (bs is Map && bs[k] is String && (bs[k] as String).isNotEmpty) {
            slug = bs[k] as String;
          }
          return slug;
        }

        final countrySlug = slugFor('country_of_residence');
        final cv = _formData[countrySlug];
        if (cv == null || (cv is String && cv.trim().isEmpty)) return false;

        if (surface == kRegAddressSurfaceNeedCountry) {
          continue;
        }

        /// Ne valider rue / CP / ville que si surface = editing, ou sans recherche,
        /// ou si une ligne a déjà du contenu (clé surface absente après hydrate, etc.).
        final searchOn = comp.props['search_enabled'] != false;
        final anyAddrLine = ['address_line_1', 'postal_code', 'city'].any((k) {
          final v = _formData[slugFor(k)];
          return v is String && v.trim().isNotEmpty;
        });
        final mustCheckAddressLines = surface == kRegAddressSurfaceEditing ||
            !searchOn ||
            (surface != kRegAddressSurfaceSearchOnly && anyAddrLine);

        if (!mustCheckAddressLines) {
          continue;
        }

        for (final k in def.keys) {
          if (k == 'country_of_residence') continue;
          if (k == 'address_line_2' && line2Optional) continue;
          final slug = slugFor(k);
          final value = _formData[slug];
          if (value == null) return false;
          if (value is String && value.trim().isEmpty) return false;
        }
        continue;
      }

      final slug = comp.bindingSlug;
      if (slug == null) continue;

      final value = _formData[slug];
      if (value == null) return false;
      if (value is bool && !value) return false;
      if (value is String && value.trim().isEmpty) return false;
      if (value is List && value.isEmpty) return false;
    }
    return true;
  }

  Widget _buildCtaButton(RegistrationSessionState session) {
    final scr = session.screen;
    final isPhoneInteraction = scr != null &&
        scr.screenType == 'interaction' &&
        scr.interactionType == 'phone_verification_sms';
    if (isPhoneInteraction) {
      return const SizedBox.shrink();
    }

    final hasFormFields = session.screen?.components
            .any((c) => _inputComponentTypes.contains(c.componentType)) ??
        false;
    final label = session.screen?.buttonLabel;
    final enabled = !hasFormFields || _allRequiredFilled;

    if (session.isLastScreen) {
      return AppPrimaryButton(
        label: label ?? 'Complete',
        variant: enabled
            ? AppPrimaryButtonVariant.primary
            : AppPrimaryButtonVariant.disabled,
        isLoading: _submitting,
        onPressed: enabled ? () async => _onLastScreenPrimaryTap() : null,
      );
    }

    return AppPrimaryButton(
      label: label ?? 'Continue',
      variant: enabled
          ? AppPrimaryButtonVariant.primary
          : AppPrimaryButtonVariant.disabled,
      isLoading: _submitting,
      onPressed: enabled
          ? (hasFormFields ? _submitWithPhoneConfirmIfNeeded : _goNext)
          : null,
    );
  }

  // ─── Debug panel ────────────────────────────────────────────────────────

  Widget _buildDebugPanel(RegistrationSessionState session) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF1C1C1E),
        borderRadius: BorderRadius.circular(12),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          GestureDetector(
            onTap: () => setState(() => _debugExpanded = !_debugExpanded),
            behavior: HitTestBehavior.opaque,
            child: Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              child: Row(
                children: [
                  const Icon(Icons.bug_report_outlined,
                      size: 16, color: AppColors.semanticWarning),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Debug  •  ${session.sessionId.substring(0, 8)}…',
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: Colors.white70,
                      ),
                    ),
                  ),
                  Icon(
                    _debugExpanded
                        ? Icons.expand_less_rounded
                        : Icons.expand_more_rounded,
                    size: 18,
                    color: Colors.white54,
                  ),
                ],
              ),
            ),
          ),
          if (_debugExpanded) ...[
            const Divider(height: 1, color: Colors.white12),
            Padding(
              padding: const EdgeInsets.all(12),
              child: DefaultTextStyle(
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 11,
                  color: Colors.white60,
                  height: 1.5,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _debugRow('session_id', session.sessionId),
                    _debugRow('status', session.status),
                    _debugRow('flow_version', '${session.flowVersion}'),
                    _debugRow('progress', '${session.progressPercent}%'),
                    _debugRow(
                        'step', session.currentStep?.stepKey ?? 'none'),
                    _debugRow('step_status',
                        session.currentStepStatus ?? 'none'),
                    _debugRow(
                        'screen', session.screen?.screenKey ?? 'none'),
                    _debugRow('is_last', session.isLastScreen.toString()),
                    const SizedBox(height: 8),
                    Text('formData (current screen):',
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 11,
                          color: AppColors.semanticWarning,
                        )),
                    for (final e in _formData.entries)
                      Padding(
                        padding: const EdgeInsets.only(left: 8),
                        child: Text('${e.key}: ${e.value}'),
                      ),
                    if (_formData.isEmpty)
                      const Padding(
                        padding: EdgeInsets.only(left: 8),
                        child: Text('(empty)'),
                      ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _debugRow(String label, String value) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 100,
          child: Text(label,
              style: GoogleFonts.jetBrainsMono(
                  fontSize: 11, color: AppColors.semanticWarning)),
        ),
        Expanded(child: Text(value)),
      ],
    );
  }
}
