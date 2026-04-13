import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:intl/date_symbol_data_local.dart';

import 'core/theme/app_theme.dart';
import 'features/design_system/presentation/screens/design_system_showcase_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting('fr_FR', null);
  runApp(const DesignSystemApp());
}

class DesignSystemApp extends StatelessWidget {
  const DesignSystemApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Arquantix — Design System',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      home: kIsWeb ? const _WebPhoneFrame() : const DesignSystemShowcaseScreen(),
    );
  }
}

class _WebPhoneFrame extends StatelessWidget {
  const _WebPhoneFrame();

  static const double _phoneWidth = 375;
  static const double _phoneHeight = 812;
  static const double _statusBarHeight = 44;
  static const double _cornerRadius = 40;
  static const double _bezelWidth = 12;

  @override
  Widget build(BuildContext context) {
    final screenSize = MediaQuery.sizeOf(context);
    final availableHeight = screenSize.height - 80;
    final scale = (availableHeight / (_phoneHeight + _bezelWidth * 2))
        .clamp(0.5, 1.2);
    final frameWidth = (_phoneWidth + _bezelWidth * 2) * scale;
    final frameHeight = (_phoneHeight + _bezelWidth * 2) * scale;

    return Scaffold(
      backgroundColor: const Color(0xFF18181B),
      body: Column(
        children: [
          _buildHeader(context),
          Expanded(
            child: Center(
              child: SizedBox(
                width: frameWidth,
                height: frameHeight,
                child: Container(
                  decoration: BoxDecoration(
                    color: const Color(0xFF1C1C1E),
                    borderRadius: BorderRadius.circular(_cornerRadius * scale),
                    border: Border.all(
                      color: const Color(0xFF3A3A3C),
                      width: 2,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.5),
                        blurRadius: 40,
                        spreadRadius: 5,
                      ),
                    ],
                  ),
                  padding: EdgeInsets.all(_bezelWidth * scale),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(
                      (_cornerRadius - _bezelWidth) * scale,
                    ),
                    child: MediaQuery(
                      data: MediaQuery.of(context).copyWith(
                        size: const Size(_phoneWidth, _phoneHeight),
                        padding: const EdgeInsets.only(top: _statusBarHeight),
                      ),
                      child: const DesignSystemShowcaseScreen(),
                    ),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Container(
      height: 64,
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Row(
        children: [
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF6155F5), Color(0xFF8B5CF6)],
              ),
              borderRadius: BorderRadius.circular(8),
            ),
            alignment: Alignment.center,
            child: const Text(
              'A',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w800,
                fontSize: 16,
              ),
            ),
          ),
          const SizedBox(width: 12),
          const Text(
            'Arquantix Design System',
            style: TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.3,
            ),
          ),
          const Spacer(),
          Text(
            'iPhone 13 Pro · 375×812',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.4),
              fontSize: 13,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
