import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/locale_preference.dart';
import '../../../design_system/components/app_tab_bar.dart';

/// Cible mobile possible pour un tab.
sealed class AppShellTarget {
  const AppShellTarget();
}

class NativeTabTarget extends AppShellTarget {
  const NativeTabTarget(this.value);
  final String value;
}

class CmsPageTarget extends AppShellTarget {
  const CmsPageTarget(this.slug);
  final String slug;
}

class ExternalUrlTarget extends AppShellTarget {
  const ExternalUrlTarget(this.url);
  final String url;
}

/// Tab résolu (label localisé + icon + target).
class AppShellTab {
  const AppShellTab({
    required this.id,
    required this.order,
    required this.label,
    required this.icon,
    required this.target,
  });

  final String id;
  final int order;
  final String label;
  final IconData icon;
  final AppShellTarget target;

  AppTabBarItemData toTabBarItem() => AppTabBarItemData(icon: icon, label: label);
}

/// Service de chargement et cache mémoire de la **tab bar de l'app Flutter**
/// (et plus tard d'autres éléments du shell).
///
/// **Offline-first** : si l'API `/api/mobile/flutter/shell` est indisponible
/// ou si la `Page(slug='app:main-tabs')` n'a pas encore été seedée, on retombe
/// sur le set compilé `kFallbackTabs` — ce qui garantit zéro régression visuelle
/// même en cas de panne BFF.
///
/// Le service écoute `LocalePreference` et recharge automatiquement quand la
/// langue active change (via le sélecteur du profil).
class AppShellService extends ChangeNotifier {
  AppShellService._() {
    LocalePreference.instance.addListener(_onLocaleChanged);
  }

  static final AppShellService instance = AppShellService._();

  /// Filet de secours compilé — doit refléter `DEFAULT_APP_MAIN_TABS` (web).
  static const List<AppShellTab> kFallbackTabs = [
    AppShellTab(
      id: 'fallback.home',
      order: 0,
      label: 'Home',
      icon: Icons.home_rounded,
      target: NativeTabTarget('home'),
    ),
    AppShellTab(
      id: 'fallback.offers',
      order: 1,
      label: 'Invest',
      icon: Icons.trending_up_rounded,
      target: NativeTabTarget('offers'),
    ),
    AppShellTab(
      id: 'fallback.markets',
      order: 2,
      label: 'Markets',
      icon: Icons.currency_bitcoin,
      target: NativeTabTarget('markets'),
    ),
    AppShellTab(
      id: 'fallback.design',
      order: 3,
      label: 'Design',
      icon: Icons.radio_rounded,
      target: NativeTabTarget('design_system'),
    ),
  ];

  List<AppShellTab> _tabs = kFallbackTabs;
  bool _loaded = false;
  bool _loading = false;

  List<AppShellTab> get tabs => List.unmodifiable(_tabs);
  bool get isLoaded => _loaded;

  Future<void> _onLocaleChanged() async {
    /// Refresh silencieux : on garde l'ancien set tant que le nouveau n'arrive pas
    /// (évite un flash visuel pendant la transition de langue).
    await refresh();
  }

  /// À appeler **une fois** au boot (warm-start), idéalement après
  /// `LocalePreference.bootstrap()`.
  Future<void> bootstrap() async {
    if (_loaded) return;
    await refresh();
  }

  Future<void> refresh() async {
    if (_loading) return;
    _loading = true;
    try {
      final locale = LocalePreference.instance.locale;
      final uri = Uri.parse(
        '${Config.apiBaseUrl}/api/mobile/flutter/shell?locale=${Uri.encodeComponent(locale)}',
      );
      final res = await http.get(uri).timeout(const Duration(seconds: 5));
      if (res.statusCode != 200) {
        if (kDebugMode) {
          debugPrint('AppShellService: ${res.statusCode} → fallback compilé');
        }
        _markLoaded();
        return;
      }
      final json = jsonDecode(res.body);
      if (json is! Map) {
        _markLoaded();
        return;
      }
      final list = json['tabs'];
      if (list is! List) {
        _markLoaded();
        return;
      }
      final parsed = <AppShellTab>[];
      for (final raw in list) {
        if (raw is! Map) continue;
        final tab = _parseTab(Map<String, dynamic>.from(raw));
        if (tab != null) parsed.add(tab);
      }
      if (parsed.isEmpty) {
        _markLoaded();
        return;
      }
      parsed.sort((a, b) => a.order.compareTo(b.order));
      _tabs = parsed;
      _loaded = true;
      notifyListeners();
    } catch (e) {
      if (kDebugMode) {
        debugPrint('AppShellService.refresh error: $e (fallback compilé)');
      }
      _markLoaded();
    } finally {
      _loading = false;
    }
  }

  void _markLoaded() {
    if (_loaded) return;
    _loaded = true;
    notifyListeners();
  }

  AppShellTab? _parseTab(Map<String, dynamic> raw) {
    final id = (raw['id'] ?? '').toString();
    if (id.isEmpty) return null;
    if (raw['enabled'] == false) return null;
    final orderRaw = raw['order'];
    final order = orderRaw is num ? orderRaw.toInt() : 0;
    final label = (raw['label'] ?? '').toString().trim();
    if (label.isEmpty) return null;
    final iconKey = (raw['icon'] ?? '').toString();
    final icon = _iconFor(iconKey);
    if (icon == null) return null;
    final targetRaw = raw['target'];
    if (targetRaw is! Map) return null;
    final target = _parseTarget(Map<String, dynamic>.from(targetRaw));
    if (target == null) return null;
    return AppShellTab(
      id: id,
      order: order,
      label: label,
      icon: icon,
      target: target,
    );
  }

  AppShellTarget? _parseTarget(Map<String, dynamic> raw) {
    final kind = (raw['kind'] ?? '').toString();
    switch (kind) {
      case 'native_tab':
        final v = (raw['value'] ?? '').toString();
        if (v.isEmpty) return null;
        return NativeTabTarget(v);
      case 'cms_page':
        final s = (raw['slug'] ?? '').toString();
        if (s.isEmpty) return null;
        return CmsPageTarget(s);
      case 'external_url':
        final u = (raw['value'] ?? '').toString();
        if (u.isEmpty) return null;
        return ExternalUrlTarget(u);
      default:
        return null;
    }
  }

  /// Mapping clé d'icône CMS → IconData. Garder synchronisé avec
  /// `APP_MOBILE_ICON_KEYS` côté web (`appShellModel.ts`).
  IconData? _iconFor(String key) {
    switch (key) {
      case 'home_rounded':
        return Icons.home_rounded;
      case 'trending_up_rounded':
        return Icons.trending_up_rounded;
      case 'currency_bitcoin':
        return Icons.currency_bitcoin;
      case 'radio_rounded':
        return Icons.radio_rounded;
      case 'search_rounded':
        return Icons.search_rounded;
      case 'more_horiz_rounded':
        return Icons.more_horiz_rounded;
      default:
        return null;
    }
  }
}
