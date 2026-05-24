import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../../core/config.dart';
import '../../../../core/privy_identity_bridge_service.dart';
import '../../../../core/secure_api_config.dart';
import '../../../../design_system/design_system.dart';
import '../../../../features/security/passcode/data/session_service.dart';
import '../../../wallet/data/privy_wallet_api.dart';
import '../../../wallet/presentation/privy_wallet_create_entry.dart';
import '../../../wallet/presentation/screens/privy_wallet_deposit_detail_screen.dart';
import '../../../wallet/presentation/screens/privy_wallet_deposits_screen.dart';
import '../../../wallet/privy/privy_dart_defines.dart';

/// Page de dépôt par transfert crypto (depuis Déposer › Transfert crypto).
/// Affiche l’adresse du wallet non custodial Privy, soldes et dépôts reçus.
class DepositCryptoScreen extends StatefulWidget {
  const DepositCryptoScreen({super.key});

  @override
  State<DepositCryptoScreen> createState() => _DepositCryptoScreenState();
}

class _DepositCryptoScreenState extends State<DepositCryptoScreen> {
  static const _privyApi = PrivyWalletApi();
  static const _recentDepositsLimit = 5;

  bool _loading = true;
  Object? _error;
  List<PersonCryptoWalletRow> _wallets = const [];
  List<PrivyWalletBalanceItem> _balances = const [];
  List<PrivyWalletDepositItem> _recentDeposits = const [];
  bool _hasSessionCredentials = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      if (!SecureApiConfig.hasAuthBackend) {
        setState(() {
          _wallets = const [];
          _balances = const [];
          _recentDeposits = const [];
          _loading = false;
          _hasSessionCredentials = false;
        });
        return;
      }
      final hasSession = await SessionService.instance.hasSessionCredentials();
      _hasSessionCredentials = hasSession;
      if (!hasSession) {
        setState(() {
          _wallets = const [];
          _balances = const [];
          _recentDeposits = const [];
          _loading = false;
        });
        return;
      }

      var list = const <PersonCryptoWalletRow>[];
      Object? walletLoadError;
      try {
        list = await PrivyIdentityBridgeService.instance
            .fetchAuthenticatedPersonCryptoWallets();
      } catch (e) {
        walletLoadError = e;
      }

      List<PrivyWalletBalanceItem> balances = const [];
      List<PrivyWalletDepositItem> deposits = const [];
      Object? ledgerLoadError;
      try {
        final balancesData = await _privyApi.fetchBalances();
        balances = balancesData.balances;
      } catch (e) {
        ledgerLoadError = e;
      }
      try {
        deposits = await _privyApi.fetchDeposits(limit: _recentDepositsLimit);
      } catch (e) {
        if (ledgerLoadError == null) ledgerLoadError = e;
      }

      if (mounted) {
        setState(() {
          _wallets = list;
          _balances = balances;
          _recentDeposits = deposits;
          _error = walletLoadError ?? (list.isEmpty && balances.isEmpty ? ledgerLoadError : null);
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e;
          _loading = false;
        });
      }
    }
  }

  String _formatWalletLoadError(Object? err) {
    const intro = 'Impossible de charger les informations du portefeuille.';
    if (err is PrivyExchangeException) {
      return '$intro HTTP ${err.statusCode}\n• code: ${err.code}\n• ${err.message}';
    }
    return '$intro $err';
  }

  PersonCryptoWalletRow? get _primaryWallet {
    for (final w in _wallets) {
      if (w.isPrimary) return w;
    }
    return _wallets.isNotEmpty ? _wallets.first : null;
  }

  Future<void> _copy(String value) async {
    await Clipboard.setData(ClipboardData(text: value));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Adresse copiée dans le presse-papiers.')),
    );
  }

  bool get _privyBuildReady =>
      PrivyDartDefines.isConfigured && PrivyDartDefines.isOAuthRedirectConfigured;

  Future<void> _showPrivyConfigurationRequiredDialog() async {
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Configuration Privy manquante'),
        content: const SingleChildScrollView(
          child: Text(
            'Le SDK Privy dans l’app est compilé sans identifiants : il faut fournir au build :\n\n'
            '• PRIVY_APP_ID\n'
            '• PRIVY_APP_CLIENT_ID\n'
            '• Le scheme OAuth natif (souvent PRIVY_OAUTH_SCHEME=vancelian)\n\n'
            'En local : copiez services/arquantix/mobile/.env.flutter.example vers '
            '.env.flutter, remplissez les champs, puis lancez l’app avec '
            './run-ios.sh ou ./run-android.sh (ils injectent les --dart-define).\n\n'
            'La création du wallet passe par Privy (code à 6 chiffres par e-mail, '
            'ou OAuth Google/Apple depuis les écrans de développement). '
            'L’e-mail doit être renseigné dans Mon compte.',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  Future<void> _onCreateWalletSecurely() async {
    if (!mounted) return;

    if (!SecureApiConfig.hasAuthBackend) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'API d’authentification non configurée (AUTH_API_BASE_URL).',
          ),
        ),
      );
      return;
    }

    if (!_privyBuildReady) {
      await _showPrivyConfigurationRequiredDialog();
      return;
    }

    final created = await openPrivyWalletEmailCreationFlow(context);

    if (!mounted) return;

    if (created) {
      await _load();
      if (mounted && _primaryWallet != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Wallet créé — votre adresse de dépôt est affichée ci-dessous.'),
            backgroundColor: AppColors.semanticPositive,
          ),
        );
      }
    }
  }

  void _openAllDeposits() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => const PrivyWalletDepositsScreen(),
      ),
    );
  }

  void _openDepositDetail(PrivyWalletDepositItem item) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => PrivyWalletDepositDetailScreen(depositId: item.id),
      ),
    );
  }

  List<Widget> _buildLoggedOutBanner() => [
        Text(
          'Session requise',
          style: AppTypography.itemPrimary.copyWith(color: AppColors.textPrimary),
        ),
        const SizedBox(height: AppSpacing.md),
        Text(
          'Connectez-vous à l’application pour afficher votre wallet de dépôt crypto ou en créer un.',
          style: AppTypography.bodyRegular.copyWith(color: AppColors.textSecondary),
        ),
      ];

  List<Widget> _buildNoWalletYetSection() => [
        Text(
          'Wallet crypto absent',
          style: AppTypography.itemPrimary.copyWith(color: AppColors.textPrimary),
        ),
        const SizedBox(height: AppSpacing.md),
        Text(
          'Vous n’avez pas encore de portefeuille crypto sécurisé lié à votre compte '
          '(non custodial Privy). Créez-le pour recevoir vos dépôts par transfert sur la blockchain.',
          style: AppTypography.bodyRegular.copyWith(color: AppColors.textSecondary),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(
          'Étapes : (1) vous confirmez l’e-mail profil — (2) code à 6 chiffres '
          'reçu par e-mail (Privy) — (3) liaison à votre session Vancelian. '
          'L’e-mail doit être renseigné dans Mon compte.',
          style: AppTypography.bodySmRegular.copyWith(color: AppColors.textMuted),
        ),
        if (!_privyBuildReady) ...[
          const SizedBox(height: AppSpacing.lg),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: AppColors.semanticWarningLight,
              borderRadius: BorderRadius.circular(AppRadius.lg),
              border: Border.all(color: AppColors.semanticWarning.withValues(alpha: 0.35)),
            ),
            child: Text(
              'Cette build ne contient notamment pas PRIVY_APP_ID / PRIVY_APP_CLIENT_ID '
              '(fichier .env.flutter ou --dart-define). Sans cela, Privy ne peut pas envoyer le code e-mail.',
              style: AppTypography.bodySmRegular.copyWith(color: AppColors.textPrimary),
            ),
          ),
        ],
        const SizedBox(height: AppSpacing.xl),
        AppPrimaryButton(
          label: 'Créer un wallet',
          onPressed: () => _onCreateWalletSecurely(),
        ),
      ];

  List<Widget> _buildBalancesSection() {
    if (_balances.isEmpty) {
      return [
        Text(
          'Soldes wallet',
          style: AppTypography.itemPrimary.copyWith(color: AppColors.textPrimary),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          'Aucun solde détecté pour le moment. Dès qu’un dépôt est confirmé, '
          'votre solde apparaîtra ici.',
          style: AppTypography.bodySmRegular.copyWith(color: AppColors.textMuted),
        ),
        const SizedBox(height: AppSpacing.xl),
      ];
    }

    return [
      Text(
        'Soldes wallet',
        style: AppTypography.itemPrimary.copyWith(color: AppColors.textPrimary),
      ),
      const SizedBox(height: AppSpacing.md),
      ..._balances.map(
        (b) => Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.sm),
          child: _BalanceCard(balance: b),
        ),
      ),
      const SizedBox(height: AppSpacing.lg),
    ];
  }

  List<Widget> _buildRecentDepositsSection() {
    return [
      Row(
        children: [
          Expanded(
            child: Text(
              'Dépôts récents',
              style: AppTypography.itemPrimary.copyWith(color: AppColors.textPrimary),
            ),
          ),
          TextButton(
            onPressed: _openAllDeposits,
            child: const Text('Voir tout'),
          ),
        ],
      ),
      const SizedBox(height: AppSpacing.sm),
      if (_recentDeposits.isEmpty)
        Text(
          'Aucun dépôt reçu pour l’instant.',
          style: AppTypography.bodySmRegular.copyWith(color: AppColors.textMuted),
        )
      else
        ..._recentDeposits.map(
          (d) => Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: _RecentDepositTile(
              deposit: d,
              onTap: () => _openDepositDetail(d),
            ),
          ),
        ),
      const SizedBox(height: AppSpacing.xl),
    ];
  }

  List<Widget> _buildDepositAddressSection(PersonCryptoWalletRow w) => [
        ..._buildBalancesSection(),
        ..._buildRecentDepositsSection(),
        Text(
          'Envoyez uniquement des actifs compatibles avec ce réseau ('
          '${w.chainType}${w.chainId != null ? ' — chain_id ${w.chainId}' : ''}). '
          'Les envois sur un mauvais réseau peuvent être perdus.',
          style: AppTypography.bodySmRegular.copyWith(color: AppColors.semanticWarning),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(
          'Votre adresse de dépôt',
          style: AppTypography.itemPrimary.copyWith(color: AppColors.textPrimary),
        ),
        const SizedBox(height: AppSpacing.sm),
        SelectionArea(
          child: Text(
            w.address,
            style: AppTypography.itemSecondary.copyWith(
              color: AppColors.textPrimary,
              fontFamily: 'monospace',
              fontSize: 14,
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        AppPrimaryButton(
          label: 'Copier l’adresse',
          onPressed: () => _copy(w.address),
        ),
        if (_wallets.length > 1) ...[
          const SizedBox(height: AppSpacing.xl),
          Text(
            'Autres adresses',
            style: AppTypography.itemPrimary.copyWith(color: AppColors.textPrimary),
          ),
          const SizedBox(height: AppSpacing.sm),
          ..._wallets.where((x) => x.id != w.id).map(
                (o) => Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.md),
                  child: ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(
                      '${o.walletType} · ${o.chainType}',
                      style: AppTypography.bodySmRegular,
                    ),
                    subtitle: Text(
                      o.address,
                      style: AppTypography.labelRegular.copyWith(
                        fontFamily: 'monospace',
                      ),
                    ),
                    trailing: IconButton(
                      icon: const Icon(Icons.copy_rounded),
                      onPressed: () => _copy(o.address),
                    ),
                  ),
                ),
              ),
        ],
      ];

  @override
  Widget build(BuildContext context) {
    final w = _primaryWallet;

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppBar(
        title: const Text('Transfert crypto'),
        titleTextStyle: AppTypography.sectionTitle,
        backgroundColor: AppColors.cardBackground,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _load,
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(AppSpacing.xl),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Dépôt par transfert crypto',
                  style: AppTypography.sectionTitle.copyWith(color: AppColors.textPrimary),
                ),
                const SizedBox(height: AppSpacing.md),
                if (_loading)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: AppSpacing.xxl),
                    child: Center(
                      child: CircularProgressIndicator(color: AppColors.indigo),
                    ),
                  )
                else if (_error != null)
                  Padding(
                    padding: const EdgeInsets.only(top: AppSpacing.lg),
                    child: Text(
                      _formatWalletLoadError(_error),
                      style:
                          AppTypography.bodyRegular.copyWith(color: AppColors.semanticDanger),
                    ),
                  )
                else if (!_hasSessionCredentials) ...[
                  ..._buildLoggedOutBanner(),
                ] else if (w == null && _balances.isEmpty && _recentDeposits.isEmpty) ...[
                  ..._buildNoWalletYetSection(),
                ] else if (w == null) ...[
                  ..._buildBalancesSection(),
                  ..._buildRecentDepositsSection(),
                  if (_wallets.isEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: AppSpacing.md),
                      child: Text(
                        'Adresse wallet indisponible — tirez pour actualiser ou recréez le lien Privy.',
                        style: AppTypography.bodySmRegular.copyWith(
                          color: AppColors.textMuted,
                        ),
                      ),
                    ),
                ] else ...[
                  ..._buildDepositAddressSection(w),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _BalanceCard extends StatelessWidget {
  const _BalanceCard({required this.balance});

  final PrivyWalletBalanceItem balance;

  @override
  Widget build(BuildContext context) {
    final logoUrl = Config.resolveLogoUrl(
      '/media/crypto_logos/${balance.asset.toLowerCase()}.png',
    );

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 18,
            backgroundImage: logoUrl != null ? NetworkImage(logoUrl) : null,
            onBackgroundImageError: logoUrl != null ? (_, __) {} : null,
            child: logoUrl == null
                ? Text(
                    balance.asset.isNotEmpty ? balance.asset[0] : '?',
                    style: AppTypography.labelRegular,
                  )
                : null,
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  balance.name,
                  style: AppTypography.itemPrimary.copyWith(color: AppColors.textPrimary),
                ),
                Text(
                  balance.asset,
                  style: AppTypography.bodySmRegular.copyWith(color: AppColors.textMuted),
                ),
              ],
            ),
          ),
          Text(
            '${balance.balance} ${balance.asset}',
            style: AppTypography.itemSecondary.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _RecentDepositTile extends StatelessWidget {
  const _RecentDepositTile({required this.deposit, required this.onTap});

  final PrivyWalletDepositItem deposit;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final hh = deposit.createdAt.hour.toString().padLeft(2, '0');
    final mm = deposit.createdAt.minute.toString().padLeft(2, '0');

    return Material(
      color: AppColors.cardBackground,
      borderRadius: BorderRadius.circular(AppRadius.lg),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.lg,
            vertical: AppSpacing.md,
          ),
          child: Row(
            children: [
              const CircleAvatar(
                radius: 18,
                backgroundColor: AppColors.semanticPositiveLight,
                child: Icon(Icons.arrow_downward_rounded, size: 18, color: AppColors.semanticPositive),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      deposit.title,
                      style: AppTypography.itemPrimary.copyWith(color: AppColors.textPrimary),
                    ),
                    Text(
                      '$hh:$mm',
                      style: AppTypography.bodySmRegular.copyWith(color: AppColors.textMuted),
                    ),
                  ],
                ),
              ),
              Text(
                '+${deposit.amount} ${deposit.asset}',
                style: AppTypography.itemSecondary.copyWith(
                  color: AppColors.semanticPositive,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
