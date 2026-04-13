import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../../design_system/atoms/dashboard_header_gradient.dart';
import '../../../design_system/components/wave_dots_loading_indicator.dart';
import '../../../features/home/application/home_dashboard_preload.dart';
import '../../shell/presentation/screens/main_shell_screen.dart';

/// Après succès passcode / biométrie : précharge les données du dashboard tout en
/// affichant une animation de pastilles (vague), puis remplace par [MainShellScreen].
class PostPasscodeDashboardLoaderScreen extends StatefulWidget {
  const PostPasscodeDashboardLoaderScreen({super.key});

  @override
  State<PostPasscodeDashboardLoaderScreen> createState() =>
      _PostPasscodeDashboardLoaderScreenState();
}

class _PostPasscodeDashboardLoaderScreenState
    extends State<PostPasscodeDashboardLoaderScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _run());
  }

  Future<void> _run() async {
    try {
      await Future.wait<void>([
        HomeDashboardPreload.runAfterPasscodeUnlock().timeout(
          const Duration(seconds: 18),
          onTimeout: () {
            if (kDebugMode) {
              debugPrint('[PostPasscodeDashboardLoader] preload timeout');
            }
          },
        ),
        Future<void>.delayed(const Duration(milliseconds: 900)),
      ]);
    } catch (e) {
      if (kDebugMode) {
        debugPrint('[PostPasscodeDashboardLoader] preload error: $e');
      }
    }
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(
        builder: (_) => const MainShellScreen(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: DecoratedBox(
        decoration: DashboardHeaderGradient.decoration,
        child: SafeArea(
          child: Center(
            child: WaveDotsLoadingIndicator(),
          ),
        ),
      ),
    );
  }
}
