import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../../design_system/design_system.dart';
import '../../data/iban_details_api.dart';
import '../../domain/models/iban_details.dart';

class IbanScreen extends StatefulWidget {
  const IbanScreen({super.key});

  @override
  State<IbanScreen> createState() => _IbanScreenState();
}

class _IbanScreenState extends State<IbanScreen> {
  final IbanDetailsApi _api = IbanDetailsApi();
  final ScrollController _scrollController = ScrollController();
  bool _loading = true;
  String? _error;
  IbanDetails? _details;
  double _navTitleOpacity = 0;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    _load();
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    final offset = _scrollController.hasClients ? _scrollController.offset : 0.0;
    final next = ((offset - 24) / 40).clamp(0.0, 1.0);
    if ((next - _navTitleOpacity).abs() > 0.02) {
      setState(() => _navTitleOpacity = next);
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final details = await _api.fetchIbanDetails();
      if (!mounted) return;
      setState(() {
        _details = details;
        _loading = false;
        if (details == null) _error = 'Aucun compte Euro trouvé';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e.toString();
      });
    }
  }

  void _copyToClipboard(String value, String label) {
    Clipboard.setData(ClipboardData(text: value));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('$label copié'),
        duration: const Duration(seconds: 2),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  void _shareIban() {
    final d = _details;
    if (d == null) return;
    final buffer = StringBuffer();
    buffer.writeln('Coordonnées bancaires');
    buffer.writeln('Destinataire : ${d.accountHolderName}');
    if (d.iban != null) buffer.writeln('IBAN : ${_formatIban(d.iban!)}');
    if (d.bic != null) buffer.writeln('BIC : ${d.bic}');
    buffer.writeln('Devise : ${d.currency}');
    _copyToClipboard(buffer.toString(), 'Coordonnées bancaires');
  }

  static String _formatIban(String raw) {
    final clean = raw.replaceAll(RegExp(r'\s'), '');
    final buffer = StringBuffer();
    for (var i = 0; i < clean.length; i++) {
      if (i > 0 && i % 4 == 0) buffer.write(' ');
      buffer.write(clean[i]);
    }
    return buffer.toString();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.back,
        onBackTap: () => Navigator.of(context).pop(),
        title: 'Coordonnées bancaires',
        titleOpacity: _navTitleOpacity,
        centerTitle: false,
        titleTextStyle: AppTypography.paragraph.copyWith(
          color: AppColors.textPrimary,
        ),
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 48, color: Colors.grey[400]),
              const SizedBox(height: 16),
              Text(
                _error!,
                style: AppTypography.paragraph.copyWith(color: Colors.grey[600]),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }
    if (_details == null) return const SizedBox.shrink();
    return _buildContent();
  }

  Widget _buildContent() {
    final d = _details!;

    return SafeArea(
      child: CustomScrollView(
        controller: _scrollController,
        slivers: [
          const SliverToBoxAdapter(child: SizedBox(height: AppSpacing.md)),
          const SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.symmetric(horizontal: AppSpacing.xl),
              child: AppPageTitle('Coordonnées bancaires'),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.s4),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: AppSpacing.sm),
                  _buildCurrencySubtitle(d),
                  const SizedBox(height: AppSpacing.s6),
                  _buildActionButtonsRow(d),
                  const SizedBox(height: AppSpacing.s8),
                  _buildBankingDetailsCard(d),
                  const SizedBox(height: AppSpacing.sm),
                  _buildInfoCard(),
                  const SizedBox(height: AppSpacing.s8),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCurrencySubtitle(IbanDetails d) {
    return Row(
      children: [
        Container(
          width: 24,
          height: 24,
          decoration: BoxDecoration(
            color: const Color(0xFF003399),
            borderRadius: BorderRadius.circular(12),
          ),
          alignment: Alignment.center,
          child: const Text(
            '€',
            style: TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          'euros · ${d.currency}',
          style: AppTypography.itemSupporting.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildActionButtonsRow(IbanDetails d) {
    return Row(
      children: [
        AppPrimaryButton(
          label: 'Partager',
          variant: AppPrimaryButtonVariant.black,
          size: AppPrimaryButtonSize.medium,
          shrinkWrap: true,
          leading: const Icon(Icons.ios_share_rounded, size: 16, color: AppColors.white),
          onPressed: _shareIban,
        ),
        const SizedBox(width: AppSpacing.md),
        AppPrimaryButton(
          label: 'Copier IBAN',
          size: AppPrimaryButtonSize.medium,
          shrinkWrap: true,
          leading: const Icon(Icons.copy_rounded, size: 16, color: AppColors.white),
          onPressed: d.iban != null
              ? () => _copyToClipboard(d.iban!, 'IBAN')
              : null,
        ),
      ],
    );
  }

  Widget _buildBankingDetailsCard(IbanDetails d) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        const AppSectionTitle('Virements SEPA'),
        const SizedBox(height: AppSpacing.md),
        SettingsCard(
          children: [
            SettingsListItem(
              compact: true,
              title: 'Destinataire',
              trailing: SettingsActionButton(
                label: d.accountHolderName,
                actionType: SettingsActionType.copy,
                onTap: () =>
                    _copyToClipboard(d.accountHolderName, 'Destinataire'),
              ),
            ),
            SettingsListItem(
              compact: true,
              title: 'Devise',
              trailing: SettingsActionButton(
                label: d.currency,
                actionType: SettingsActionType.copy,
                onTap: () => _copyToClipboard(d.currency, 'Devise'),
              ),
            ),
            if (d.iban != null)
              SettingsListItem(
                compact: true,
                title: 'IBAN',
                trailing: SettingsActionButton(
                  label: _formatIban(d.iban!),
                  actionType: SettingsActionType.copy,
                  onTap: () => _copyToClipboard(d.iban!, 'IBAN'),
                ),
              ),
            if (d.bic != null)
              SettingsListItem(
                compact: true,
                title: 'BIC',
                trailing: SettingsActionButton(
                  label: d.bic!,
                  actionType: SettingsActionType.copy,
                  onTap: () => _copyToClipboard(d.bic!, 'BIC'),
                ),
              ),
          ],
        ),
      ],
    );
  }

  Widget _buildInfoCard() {
    return const SettingsCard(
      children: [
        SettingsListItem(
          leading: Icon(Icons.schedule_rounded, size: 22, color: AppColors.textSecondary),
          title: 'Délai de traitement',
          value: 'Jusqu\'à 3 jours',
        ),
        SettingsListItem(
          leading: Icon(Icons.language_rounded, size: 22, color: AppColors.textSecondary),
          title: 'Type de virement',
          value: 'SEPA',
        ),
        SettingsListItem(
          leading: Icon(Icons.euro_rounded, size: 22, color: AppColors.textSecondary),
          title: 'Devise',
          value: 'EUR',
        ),
      ],
    );
  }
}

