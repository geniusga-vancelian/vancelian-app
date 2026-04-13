import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:share_plus/share_plus.dart';

import '../../../../design_system/atoms/app_colors.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/atoms/app_typography.dart';
import '../../../../design_system/components/app_primary_button.dart';
import '../../../../design_system/components/bottom_sheet_container.dart';
import '../../../../design_system/components/sheet_title_bar.dart';
import '../../data/euro_statement_pdf_api.dart';

/// Flux relevé IBAN : génération PDF au chargement, puis partage / enregistrement via le système.
class EuroStatementBottomSheet {
  EuroStatementBottomSheet._();

  static Future<void> show(BuildContext context) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      isDismissible: true,
      enableDrag: true,
      builder: (ctx) => const _EuroStatementSheetBody(),
    );
  }
}

enum _SheetPhase { loading, success, error }

class _EuroStatementSheetBody extends StatefulWidget {
  const _EuroStatementSheetBody();

  @override
  State<_EuroStatementSheetBody> createState() => _EuroStatementSheetBodyState();
}

class _EuroStatementSheetBodyState extends State<_EuroStatementSheetBody> {
  final EuroStatementPdfApi _api = EuroStatementPdfApi();

  _SheetPhase _phase = _SheetPhase.loading;
  Uint8List? _pdfBytes;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _phase = _SheetPhase.loading;
      _errorMessage = null;
      _pdfBytes = null;
    });
    try {
      final bytes = await _api.fetchStatementPdf();
      if (!mounted) return;
      setState(() {
        _pdfBytes = bytes;
        _phase = _SheetPhase.success;
      });
    } on EuroStatementPdfException catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = e.message;
        _phase = _SheetPhase.error;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = e.toString();
        _phase = _SheetPhase.error;
      });
    }
  }

  /// iPad : sans [sharePositionOrigin], `shareXFiles` peut échouer sans UI (popover obligatoire).
  Rect _sharePositionOrigin(BuildContext anchorContext) {
    final box = anchorContext.findRenderObject() as RenderBox?;
    if (box != null && box.hasSize) {
      return box.localToGlobal(Offset.zero) & box.size;
    }
    final size = MediaQuery.sizeOf(anchorContext);
    return Rect.fromLTWH(0, size.height * 0.55, size.width, size.height * 0.45);
  }

  Future<void> _sharePdf(BuildContext anchorContext) async {
    final bytes = _pdfBytes;
    if (bytes == null) return;
    final name =
        'iban-releve-${DateFormat('yyyy-MM-dd').format(DateTime.now())}.pdf';
    final file = File('${Directory.systemTemp.path}/$name');
    // Avant tout await : ancrage popover iPad (évite use_build_context_synchronously).
    final shareOrigin = _sharePositionOrigin(anchorContext);
    try {
      await file.writeAsBytes(bytes, flush: true);
      await Share.shareXFiles(
        [XFile(file.path, mimeType: 'application/pdf', name: name)],
        subject: 'Relevé bancaire',
        sharePositionOrigin: shareOrigin,
      );
    } catch (e, st) {
      debugPrint('EuroStatementBottomSheet._sharePdf: $e\n$st');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Impossible d’ouvrir le partage : ${e.toString()}',
          ),
        ),
      );
    }
  }

  String get _title {
    switch (_phase) {
      case _SheetPhase.loading:
        return 'Création du relevé';
      case _SheetPhase.success:
        return 'Votre relevé est prêt';
      case _SheetPhase.error:
        return 'Impossible de générer le relevé';
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.paddingOf(context).bottom;

    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.viewInsetsOf(context).bottom,
      ),
      child: BottomSheetContainer(
        toolbar: SheetTitleBar(
          title: _title,
          leadingButton: SheetCircleButton.leading(
            onTap: () => Navigator.of(context).maybePop(),
          ),
        ),
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (_phase == _SheetPhase.loading) ...[
                  Text(
                    'Votre relevé bancaire est en cours de génération. Cela peut prendre quelques secondes.',
                    style: AppTypography.bodyMedium.copyWith(
                      color: AppColors.textSecondary,
                      height: 1.45,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: AppSpacing.xl),
                  const Center(
                    child: SizedBox(
                      width: 36,
                      height: 36,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.5,
                        color: AppColors.accent,
                      ),
                    ),
                  ),
                ],
                if (_phase == _SheetPhase.success) ...[
                  Text(
                    'Vous pouvez maintenant le télécharger.',
                    style: AppTypography.bodyMedium.copyWith(
                      color: AppColors.textSecondary,
                      height: 1.45,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: AppSpacing.xl),
                  Builder(
                    builder: (btnContext) => AppPrimaryButton(
                      label: 'Télécharger le relevé',
                      onPressed: () => _sharePdf(btnContext),
                      size: AppPrimaryButtonSize.large,
                    ),
                  ),
                ],
                if (_phase == _SheetPhase.error) ...[
                  Text(
                    _errorMessage ??
                        'Vérifiez votre connexion et réessayez.',
                    style: AppTypography.bodyMedium.copyWith(
                      color: AppColors.textSecondary,
                      height: 1.45,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: AppSpacing.xl),
                  AppPrimaryButton(
                    label: 'Réessayer',
                    onPressed: _load,
                    size: AppPrimaryButtonSize.large,
                  ),
                  const SizedBox(height: AppSpacing.md),
                  AppPrimaryButton(
                    label: 'Fermer',
                    variant: AppPrimaryButtonVariant.secondary,
                    onPressed: () => Navigator.of(context).maybePop(),
                    size: AppPrimaryButtonSize.medium,
                  ),
                ],
                SizedBox(height: bottomInset > 0 ? bottomInset : AppSpacing.md),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
