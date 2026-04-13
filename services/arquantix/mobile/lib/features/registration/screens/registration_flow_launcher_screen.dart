import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/config.dart' as app_config;
import '../../../core/profile_identity_coordinator.dart';
import '../../security/passcode/data/session_service.dart';
import '../../../design_system/atoms/app_colors.dart';
import '../../../design_system/components/app_primary_button.dart';
import '../../profile/data/mobile_app_profile.dart';
import '../data/registration_api.dart';
import '../widgets/registration_flow_step_info.dart';
import '../widgets/registration_progress_module.dart';
import '../widgets/registration_progress_module_builder.dart';
import 'registration_flow_screen.dart';

/// Hub parcours d’inscription : juridiction + étapes actives (API) et progression dérivée du profil.
class RegistrationFlowLauncherScreen extends StatefulWidget {
  const RegistrationFlowLauncherScreen({
    super.key,
    this.baseUrl,
  });

  final String? baseUrl;

  @override
  State<RegistrationFlowLauncherScreen> createState() =>
      _RegistrationFlowLauncherScreenState();
}

class _RegistrationFlowLauncherScreenState
    extends State<RegistrationFlowLauncherScreen> {
  late final RegistrationApi _api;

  bool _loading = true;
  String? _errorMessage;

  String? _jurisdictionCode;
  String? _jurisdictionName;
  String? _flowName;
  int? _flowVersion;
  String? _flowId;

  List<RegistrationFlowStepInfo> _flowSteps = [];
  MobileAppProfile? _profileSnapshot;

  String get _resolvedBaseUrl => widget.baseUrl ?? app_config.Config.marketDataBaseUrl;

  @override
  void initState() {
    super.initState();
    _api = RegistrationApi(
      baseUrl: _resolvedBaseUrl,
      accessTokenResolver: SessionService.instance.readAccessToken,
    );
    _fetchAll();
  }

  Future<void> _fetchAll() async {
    setState(() {
      _loading = true;
      _errorMessage = null;
    });

    if (await SessionService.instance.hasSessionCredentials()) {
      final profile = await ProfileIdentityCoordinator.instance.loadAccountProfile(
        forceRefresh: true,
        debugTag: 'RegistrationFlowLauncher',
      );
      if (mounted) {
        _profileSnapshot = profile;
      }
    } else {
      _profileSnapshot = ProfileIdentityCoordinator.instance.cachedProfile;
    }

    final result = await _api.getCurrentJurisdiction();
    if (!mounted) return;

    if (result.isSuccess && result.data != null) {
      final data = result.data!;
      _jurisdictionCode = data['jurisdiction_code'] as String?;
      _jurisdictionName = data['jurisdiction_name'] as String?;
      _flowName = data['active_flow_name'] as String?;
      _flowVersion = data['active_flow_version'] as int?;
      _flowId = data['active_flow_id'] as String?;

      if (_jurisdictionCode != null) {
        await _fetchFlowSteps();
      }
    } else {
      _errorMessage = result.errorMessage ?? 'Failed to load jurisdiction';
    }

    setState(() => _loading = false);
  }

  Future<void> _fetchFlowSteps() async {
    final flowResult = await _api.getActiveFlow(_jurisdictionCode!);
    if (!mounted) return;

    if (flowResult.isSuccess && flowResult.data != null) {
      _flowSteps =
          RegistrationFlowStepInfo.fromFlowJson(flowResult.data!);
    }
  }

  bool get _canLaunch =>
      _jurisdictionCode != null && _flowId != null && !_loading;

  void _launchFlow() {
    if (_jurisdictionCode == null) return;
    Navigator.of(context).push(
      MaterialPageRoute<bool>(
        builder: (_) => RegistrationFlowScreen(
          jurisdiction: _jurisdictionCode!,
          baseUrl: _resolvedBaseUrl,
          showDebugPanel: kDebugMode,
        ),
      ),
    ).then((completed) {
      if (completed == true && mounted) {
        _fetchAll();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppBar(
        backgroundColor: AppColors.pageBackground,
        elevation: 0,
        scrolledUnderElevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.close_rounded, size: 24),
          tooltip: 'Fermer',
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Text(
          'Parcours d’inscription',
          style: GoogleFonts.inter(
            fontSize: 17,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.43,
          ),
        ),
        centerTitle: true,
      ),
      body: _loading ? _buildLoading() : _buildContent(),
    );
  }

  Widget _buildLoading() {
    return const Center(
      child: CircularProgressIndicator(color: AppColors.indigo),
    );
  }

  Widget _buildContent() {
    if (_errorMessage != null && _jurisdictionCode == null) {
      return _buildFatalError();
    }

    final moduleData = RegistrationProgressModuleBuilder.build(
      profile: _profileSnapshot,
      flowSteps: _flowSteps,
      jurisdictionName: _jurisdictionName,
      flowName: _flowName,
      flowVersion: _flowVersion,
      canLaunch: _canLaunch,
      onNavigate: _launchFlow,
    );

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      child: Column(
        children: [
          RegistrationProgressModule(
            data: moduleData,
            onContinue: _launchFlow,
          ),
          if (_errorMessage != null) ...[
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
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
          ],
          if (_jurisdictionCode == null && _errorMessage == null) ...[
            const SizedBox(height: 16),
            _buildEmptyState(
              'Aucune juridiction configurée',
              'Configurez une juridiction courante depuis l’admin.',
            ),
          ] else if (_flowId == null &&
              _jurisdictionCode != null &&
              _errorMessage == null) ...[
            const SizedBox(height: 16),
            _buildEmptyState(
              'Aucun flux actif',
              'Aucun flux actif pour $_jurisdictionCode.',
            ),
          ],
          const SizedBox(height: 16),
          AppPrimaryButton(
            label: 'Rafraîchir',
            onPressed: _fetchAll,
            variant: AppPrimaryButtonVariant.gray,
          ),
          SizedBox(height: MediaQuery.of(context).padding.bottom + 8),
        ],
      ),
    );
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
              _errorMessage ?? 'Une erreur est survenue',
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(
                  fontSize: 15, color: AppColors.textSecondary),
            ),
            const SizedBox(height: 24),
            AppPrimaryButton(
              label: 'Réessayer',
              onPressed: _fetchAll,
              shrinkWrap: true,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(String title, String message) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.semanticWarningLight,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: AppColors.semanticWarning.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        children: [
          const Icon(Icons.info_outline_rounded,
              size: 24, color: AppColors.semanticWarning),
          const SizedBox(height: 8),
          Text(
            title,
            style: GoogleFonts.inter(
              fontSize: 15,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            message,
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(
              fontSize: 13,
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}

/// Compat tests / imports historiques.
typedef RegistrationTestLauncherScreen = RegistrationFlowLauncherScreen;
