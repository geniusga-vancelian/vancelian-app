import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../../../core/privy_identity_bridge_service.dart';
import '../../../../core/secure_api_config.dart';
import '../../../../core/session_identity_context.dart';
import '../../../../design_system/design_system.dart';
import '../../../security/passcode/data/session_service.dart';
import '../../privy/privy_auth_provider.dart';
import '../../privy/privy_dart_defines.dart';

/// Écran **debug uniquement** : SDK Privy + dev-link + `/auth/privy/exchange` + session Vancelian.
///
/// E2E sans SQL manuel : **Link Privy to Person** (`POST /auth/privy/dev-link`) puis **Exchange**.
class PrivyWalletDevScreen extends StatefulWidget {
  const PrivyWalletDevScreen({super.key});

  @override
  State<PrivyWalletDevScreen> createState() => _PrivyWalletDevScreenState();
}

class _PrivyWalletDevScreenState extends State<PrivyWalletDevScreen> {
  final _emailCtrl = TextEditingController();
  final _codeCtrl = TextEditingController();
  final _personIdCtrl = TextEditingController();
  late final PrivyAuthProvider _privy = createPrivyAuthProvider();

  bool _busy = false;
  String _lineStatus = '';
  String? _lastApiCode;
  String? _lastApiMessage;

  String _privyAuthLabel = '—';
  String _privyDidPreview = '—';
  String? _walletPreview;
  String? _vancelianPreview;
  String? _loadedJwtSubject;
  String? _loadedPeClientId;

  @override
  void dispose() {
    _emailCtrl.dispose();
    _codeCtrl.dispose();
    _personIdCtrl.dispose();
    super.dispose();
  }

  Future<void> _refreshPrivySummary() async {
    try {
      final label = await _privy.describePrivyAuthStateLabel();
      final did = await _privy.getLinkedPrivyUserId();
      if (!mounted) return;
      setState(() {
        _privyAuthLabel = label;
        _privyDidPreview = (did == null || did.isEmpty) ? '— (non connecté)' : did;
      });
    } catch (_) {
      if (mounted) {
        setState(() {
          _privyAuthLabel = 'Erreur lecture SDK';
        });
      }
    }
  }

  Future<void> _run(String tag, Future<void> Function() body) async {
    setState(() {
      _busy = true;
      _lineStatus = '$tag…';
      _lastApiCode = null;
      _lastApiMessage = null;
    });
    try {
      await body();
      if (mounted) {
        setState(() => _lineStatus = '$tag : OK');
      }
    } on PrivyExchangeException catch (e) {
      if (mounted) {
        setState(() {
          _lastApiCode = e.code;
          _lastApiMessage = e.message;
          _lineStatus = '$tag : ${e.code}';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${e.code}: ${e.message}')),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _lastApiCode = 'client';
          _lastApiMessage = '$e';
          _lineStatus = '$tag : $e';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _refreshVancelianStatus() async {
    final t = await SessionService.instance.readAccessToken();
    if (!mounted) return;
    if (t == null || t.isEmpty) {
      setState(() {
        _vancelianPreview =
            'Aucun JWT stocké (SecureStorage / SessionService vide).';
      });
      return;
    }
    final sub = SessionService.extractJwtSubject(t);
    final pid = SessionIdentityContext.instance.personId;
    final len = t.length;
    final tail = len > 8 ? t.substring(len - 8) : '****';
    setState(() {
      _vancelianPreview =
          'sub=$sub | person_id=$pid | jwt …$tail (len=$len)\n'
          '(tronqué volontairement — jamais de jeton complet en log.)';
    });
  }

  Future<void> _refreshWalletPreview() async {
    await _run('Wallet Privy', () async {
      final w = await _privy.getPrimaryWallet();
      if (!mounted) return;
      setState(() {
        _walletPreview = w == null
            ? 'Aucun embedded ETH wallet (créer ou attendre sync).'
            : '${w.address} | ${w.chainType} | chainId=${w.chainId}';
      });
    });
    await _refreshPrivySummary();
  }

  Future<void> _loadCurrentVancelianPerson() async {
    await _run('devCurrentPerson', () async {
      final r = await PrivyIdentityBridgeService.instance.devCurrentPerson();
      if (!mounted) return;
      setState(() {
        _personIdCtrl.text = r.personId;
        _loadedJwtSubject = r.jwtSubject;
        _loadedPeClientId = r.peClientId;
      });
    });
  }

  Future<void> _linkPrivyToPersonBody() async {
    final pid = _personIdCtrl.text.trim();
    final pUid = await _privy.getLinkedPrivyUserId();
    if (pid.isEmpty) {
      throw PrivyAuthProviderException(
        'Renseigner person UUID (ou Load current person).',
      );
    }
    if (pUid == null || pUid.isEmpty) {
      throw PrivyAuthProviderException(
        'Privy user id absent — login Privy d’abord.',
      );
    }
    await PrivyIdentityBridgeService.instance.devLinkPrivyToPerson(
      personId: pid,
      privyUserId: pUid,
      email: _emailCtrl.text.trim().isEmpty ? null : _emailCtrl.text.trim(),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!kDebugMode) {
      return const Scaffold(
        body: Center(
          child: Text('Écran réservé au mode debug.'),
        ),
      );
    }

    final configured = PrivyDartDefines.isConfigured;

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppBar(
        title: const Text('Privy E2E (dev)'),
        backgroundColor: AppColors.pageBackground,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          children: [
            Text(
              configured
                  ? 'SDK + API auth : ${PrivyIdentityBridgeService.privyExchangeUrl.split('/auth').first}'
                  : 'Définir PRIVY_APP_ID et PRIVY_APP_CLIENT_ID en --dart-define.',
              style: AppTypography.bodyRegular,
            ),
            const SizedBox(height: AppSpacing.md),
            Text('Privy — login', style: AppTypography.sectionTitle),
            TextField(
              controller: _emailCtrl,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(
                labelText: 'Email (OTP Privy)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            TextField(
              controller: _codeCtrl,
              decoration: const InputDecoration(
                labelText: 'Code OTP Privy',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            AppPrimaryButton(
              label: '1. Envoyer code email Privy',
              onPressed: !_busy && configured
                  ? () => _run('sendCode', () async {
                        await _privy.sendPrivyEmailCode(_emailCtrl.text);
                        await _refreshPrivySummary();
                      })
                  : null,
            ),
            const SizedBox(height: AppSpacing.sm),
            AppPrimaryButton(
              label: '2. Login with Privy (valider OTP)',
              onPressed: !_busy && configured
                  ? () => _run('login', () async {
                        await _privy.completePrivyEmailLogin(
                          email: _emailCtrl.text,
                          code: _codeCtrl.text,
                        );
                        await _refreshPrivySummary();
                      })
                  : null,
            ),
            const SizedBox(height: AppSpacing.sm),
            AppPrimaryButton(
              label: '3. Create / Get embedded wallet',
              onPressed: !_busy && configured
                  ? () => _run('createWallet', () async {
                        await _privy.createEmbeddedWalletIfNeeded();
                        await _refreshWalletPreview();
                      })
                  : null,
            ),
            const SizedBox(height: AppSpacing.xl),
            Text('Vancelian — person cible', style: AppTypography.sectionTitle),
            TextField(
              controller: _personIdCtrl,
              decoration: const InputDecoration(
                labelText: 'person_id (UUID)',
                border: OutlineInputBorder(),
                hintText: 'Coller UUID ou charger depuis session',
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            AppPrimaryButton(
              label: 'Load current Vancelian person',
              onPressed: !_busy && SecureApiConfig.hasAuthBackend
                  ? _loadCurrentVancelianPerson
                  : null,
            ),
            if (_loadedJwtSubject != null) ...[
              const SizedBox(height: AppSpacing.xs),
              Text(
                'Session chargée : jwt_subject=$_loadedJwtSubject, pe_client_id=$_loadedPeClientId',
                style: AppTypography.bodySmRegular.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
            const SizedBox(height: AppSpacing.sm),
            AppPrimaryButton(
              label: 'Link Privy to Person (dev-link)',
              onPressed: !_busy && configured && SecureApiConfig.hasAuthBackend
                  ? () => _run('devLink', () async {
                        await _linkPrivyToPersonBody();
                        await _refreshPrivySummary();
                      })
                  : null,
            ),
            const SizedBox(height: AppSpacing.sm),
            AppPrimaryButton(
              label: 'Exchange Privy token → Vancelian JWT',
              onPressed: !_busy && configured
                  ? () => _run('exchange', () async {
                        final token = await _privy.getAccessToken();
                        if (token == null || token.isEmpty) {
                          throw PrivyAuthProviderException(
                            'Access token Privy absent.',
                          );
                        }
                        final w = await _privy.getPrimaryWallet();
                        await PrivyIdentityBridgeService.instance
                            .exchangePrivyToken(
                          privyAccessToken: token,
                          wallets: w != null
                              ? <Map<String, dynamic>>[w.toExchangeJson()]
                              : null,
                        );
                        await _refreshVancelianStatus();
                        await _refreshPrivySummary();
                      })
                  : null,
            ),
            const SizedBox(height: AppSpacing.sm),
            AppPrimaryButton(
              label: 'Show Vancelian session status',
              onPressed: !_busy ? () => _run('session', _refreshVancelianStatus) : null,
            ),
            const SizedBox(height: AppSpacing.sm),
            AppPrimaryButton(
              label: 'Show wallet address',
              onPressed: !_busy && configured ? _refreshWalletPreview : null,
            ),
            const SizedBox(height: AppSpacing.sm),
            AppPrimaryButton(
              label: 'Refresh Privy SDK status',
              onPressed: !_busy && configured
                  ? () => _run('privyStatus', _refreshPrivySummary)
                  : null,
            ),
            TextButton(
              onPressed: !_busy && configured
                  ? () => _run('logoutPrivy', () async {
                        await _privy.logout();
                        await _refreshPrivySummary();
                      })
                  : null,
              child: const Text('Logout Privy (SDK seul)'),
            ),
            const SizedBox(height: AppSpacing.xl),
            Text('Dernière action', style: AppTypography.sectionTitle),
            Text(
              _lineStatus,
              style: AppTypography.bodySmRegular.copyWith(color: AppColors.textSecondary),
            ),
            if (_lastApiCode != null) ...[
              const SizedBox(height: AppSpacing.sm),
              Text('API detail.code', style: AppTypography.sectionTitle),
              SelectableText(
                '${_lastApiCode!}\n${_lastApiMessage ?? ''}',
                style: AppTypography.bodyRegular,
              ),
            ],
            const SizedBox(height: AppSpacing.md),
            Text('Privy SDK', style: AppTypography.sectionTitle),
            SelectableText(
              'auth_state=$_privyAuthLabel\nprivy_user_id / DID=\n$_privyDidPreview',
              style: AppTypography.bodyRegular,
            ),
            const SizedBox(height: AppSpacing.md),
            Text('Wallet', style: AppTypography.sectionTitle),
            Text(
              _walletPreview ?? '— (bouton « Show wallet address »)',
              style: AppTypography.bodyRegular,
            ),
            const SizedBox(height: AppSpacing.md),
            Text('Session Vancelian', style: AppTypography.sectionTitle),
            Text(
              _vancelianPreview ?? '—',
              style: AppTypography.bodyRegular,
            ),
          ],
        ),
      ),
    );
  }
}
