import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../../../../design_system/atoms/app_colors.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/atoms/app_typography.dart';
import '../../../../design_system/layout/module_horizontal_margin.dart';
import '../../domain/vault_exclusive_offer_modules.dart';
import '../../domain/vault_visualization_url.dart';

/// Visite virtuelle Vault — alignée sur `VaultVirtualVisualizationModuleWeb` (titre, description, iframe).
class VaultVirtualVisualizationModule extends StatefulWidget {
  const VaultVirtualVisualizationModule({
    super.key,
    required this.data,
    required this.invalidEmbedMessage,
    required this.openInBrowserLabel,
    this.showModuleTitle = true,
  });

  final VaultVirtualVisualizationModuleData data;
  final String invalidEmbedMessage;
  final String openInBrowserLabel;
  final bool showModuleTitle;

  @override
  State<VaultVirtualVisualizationModule> createState() => _VaultVirtualVisualizationModuleState();
}

class _VaultVirtualVisualizationModuleState extends State<VaultVirtualVisualizationModule> {
  WebViewController? _controller;

  @override
  void initState() {
    super.initState();
    if (!kIsWeb && widget.data.canEmbed) {
      _controller = WebViewController()
        ..setJavaScriptMode(JavaScriptMode.unrestricted)
        ..loadRequest(Uri.parse(widget.data.normalizedUrl));
    }
  }

  Future<void> _launch(String raw) async {
    var s = raw.trim();
    if (s.isEmpty) return;
    if (!s.startsWith('http')) {
      s = normalizeVirtualVisualizationInput(s);
    }
    final u = Uri.tryParse(s);
    if (u == null) return;
    if (await canLaunchUrl(u)) {
      await launchUrl(u, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    final title = widget.data.moduleTitle.trim();
    final desc = widget.data.description.trim();
    final showTitle = title.isNotEmpty && widget.showModuleTitle;
    final hasDesc = desc.isNotEmpty;
    final screenH = MediaQuery.sizeOf(context).height;
    final frameH = (screenH * 0.85).clamp(480.0, 920.0);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (showTitle)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: kModuleHorizontalMargin),
            child: Text(
              title,
              textAlign: TextAlign.center,
              style: AppTypography.titleLarge.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        if (showTitle && hasDesc) const SizedBox(height: AppSpacing.s8),
        if (hasDesc)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: kModuleHorizontalMargin),
            child: Text(
              desc,
              textAlign: TextAlign.center,
              style: AppTypography.bodyMedium.copyWith(
                color: AppColors.textSecondary,
                height: 1.45,
              ),
            ),
          ),
        if (widget.data.canEmbed && !kIsWeb) ...[
          if (showTitle || hasDesc) const SizedBox(height: AppSpacing.s8),
          Container(
            decoration: BoxDecoration(
              border: Border(
                top: BorderSide(color: AppColors.gray.withValues(alpha: 0.35)),
                bottom: BorderSide(color: AppColors.gray.withValues(alpha: 0.35)),
              ),
              color: const Color(0xFFF5F5F5),
            ),
            height: frameH,
            child: _controller != null
                ? WebViewWidget(controller: _controller!)
                : const SizedBox.shrink(),
          ),
        ] else ...[
          if (widget.data.rawUrl.trim().isNotEmpty &&
              widget.data.normalizedUrl.isEmpty) ...[
            if (showTitle || hasDesc) const SizedBox(height: AppSpacing.lg),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: kModuleHorizontalMargin),
              child: Text(
                widget.invalidEmbedMessage,
                textAlign: TextAlign.center,
                style: AppTypography.bodySmall.copyWith(color: const Color(0xFF92400E)),
              ),
            ),
          ],
          if (widget.data.canEmbed && kIsWeb) ...[
            const SizedBox(height: AppSpacing.md),
            Center(
              child: TextButton(
                onPressed: () => _launch(widget.data.normalizedUrl),
                child: Text(widget.openInBrowserLabel),
              ),
            ),
          ],
          if (!widget.data.canEmbed && widget.data.rawUrl.trim().isNotEmpty) ...[
            const SizedBox(height: AppSpacing.md),
            Center(
              child: TextButton(
                onPressed: () => _launch(widget.data.rawUrl),
                child: Text(widget.openInBrowserLabel),
              ),
            ),
          ],
        ],
        if (widget.data.canEmbed && !kIsWeb) ...[
          const SizedBox(height: AppSpacing.sm),
          Center(
            child: TextButton(
              onPressed: () => _launch(widget.data.normalizedUrl),
              child: Text(widget.openInBrowserLabel),
            ),
          ),
        ],
      ],
    );
  }
}
