import 'package:flutter/material.dart';

import '../../passcode/data/device_id_service.dart';
import '../../passcode/data/session_service.dart';
import '../application/passkey_service.dart';
import '../data/passkey_api.dart';
import '../data/passkey_platform_provider_factory.dart';
import '../domain/passkey_exceptions.dart';
import 'passkey_setup_screen.dart';

/// Liste et révocation des passkeys (utilisateur connecté).
class PasskeyManagementScreen extends StatefulWidget {
  const PasskeyManagementScreen({super.key});

  @override
  State<PasskeyManagementScreen> createState() => _PasskeyManagementScreenState();
}

class _PasskeyManagementScreenState extends State<PasskeyManagementScreen> {
  final PasskeyService _service = PasskeyService(
    api: PasskeyApi(),
    provider: createPasskeyProvider(),
    getDeviceId: () => DeviceIdService.instance.getOrCreate(),
    getFingerprintHeader: () => DeviceIdService.instance.buildFingerprintHeaderJson(),
  );

  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _items = [];

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
    final token = await SessionService.instance.readAccessToken();
    if (token == null || token.isEmpty) {
      setState(() {
        _loading = false;
        _error = 'Non connecté.';
        _items = [];
      });
      return;
    }
    try {
      final list = await _service.listPasskeys(token);
      setState(() {
        _items = list;
        _loading = false;
      });
    } on PasskeyApiException catch (e) {
      setState(() {
        _loading = false;
        _error = 'Chargement impossible (${e.statusCode}).';
        _items = [];
      });
    }
  }

  Future<void> _revoke(String credentialId) async {
    final token = await SessionService.instance.readAccessToken();
    if (token == null) return;
    try {
      await _service.revokePasskey(accessToken: token, credentialId: credentialId);
      await _load();
    } on PasskeyApiException {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Révocation échouée')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Passkeys'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () async {
              await Navigator.of(context).push<void>(
                MaterialPageRoute<void>(builder: (_) => const PasskeySetupScreen()),
              );
              await _load();
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    children: [
                      Padding(
                        padding: const EdgeInsets.all(24),
                        child: Text(_error!),
                      ),
                    ],
                  )
                : _items.isEmpty
                    ? ListView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        children: const [
                          SizedBox(height: 48),
                          Center(child: Text('Aucune passkey enregistrée')),
                        ],
                      )
                    : ListView.builder(
                        itemCount: _items.length,
                        itemBuilder: (context, i) {
                          final it = _items[i];
                          final label = it['device_label'] as String? ?? 'Appareil';
                          final cid = it['credential_id'] as String? ?? '';
                          final created = it['created_at'] as String? ?? '';
                          final last = it['last_used_at'] as String? ?? '—';
                          return ListTile(
                            title: Text(label),
                            subtitle: Text('Créée : $created\nDernière utilisation : $last'),
                            trailing: IconButton(
                              icon: const Icon(Icons.delete_outline),
                              onPressed: cid.isEmpty ? null : () => _revoke(cid),
                            ),
                          );
                        },
                      ),
      ),
    );
  }
}
