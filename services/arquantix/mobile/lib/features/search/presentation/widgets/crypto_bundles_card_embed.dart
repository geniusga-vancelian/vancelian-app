import 'package:flutter/material.dart';

import '../../../../design_system/atoms/app_colors.dart';
import '../../../../design_system/atoms/app_radius.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/atoms/kalai_icons.dart';
import '../../../../design_system/components/assets_bundles_module.dart';
import '../../../../design_system/components/kalai_icon.dart';
import '../../../markets/data/product_catalog_api.dart';
import '../../application/assistance_deep_link_resolver.dart';
import '../../data/chat_api.dart';

/// Embed chat « Crypto Bundles » — Phase 2 wiki (refonte v2 : pixel-perfect
/// vs widget markets `CryptoBundlesWidget`).
///
/// Réplique exacte du widget [CryptoBundlesWidget] de la page markets
/// (slider horizontal de cartes bundle), réutilisée ici dans une bulle
/// assistant pour répondre concrètement à *« quels bundles je peux
/// prendre ? »*, *« la liste des crypto baskets »*, etc.
///
/// Le tool serveur `show_crypto_bundles` (agent `product`) émet un
/// embed `crypto_bundles_card` contenant la liste des bundles publics
/// actifs avec :
///
///   - `bundles[*].id` (UUID `pe_product_definitions`)
///   - `bundles[*].name`, `product_code`, `description`,
///     `risk_label`, `base_currency`
///   - `bundles[*].allocations` (liste de `{symbol, instrument_name,
///     weight}`)
///   - `bundles[*].actions` : 2 deep-links whitelisted
///     - `view_bundle_detail` → tap card → fiche détail produit
///     - `invest_bundle` → bouton « Investir » → flow d'investissement
///
/// Différence clé avec [InstrumentDetailCardEmbed] : on affiche **N
/// cartes** en slider (≥ 1), et le LLM peut écrire un texte
/// d'introduction au-dessus pour situer.
///
/// Refonte 2026-05-04 :
///   - **Pas de titre de module** (`title: ''`) — le LLM rédige son
///     propre intro au-dessus.
///   - `visibleCardsCount: 1.4` — comme la page markets.
///   - **Marge horizontale** : `horizontalMargin: 0` + [AssetsBundlesModule.layoutWidth]
///     (piste = [LayoutBuilder]) car le `ListView` du chat applique déjà
///     `AppSpacing.lg` — évite de cumuler deux gouttières sur la 1ʳᵉ carte.
///   - Fetch `ProductCatalogApi.getDisplayConfigs()` au mount pour
///     récupérer `headerMediaUrl` (image cover) et `sortOrder` —
///     correctif du bug *« l'image de cover ne s'affiche pas »*. Le
///     payload backend ne contient pas ces métadonnées CMS (Prisma
///     côté Web/BFF, pas FastAPI Python).
///   - On ne filtre **pas** sur la présence d'une config (le widget
///     markets le fait via `displayConfigs.containsKey`) : le
///     LLM est autoritaire — s'il a appelé `show_crypto_bundles`
///     avec un filtre, on respecte sa sélection même sans config CMS
///     (placeholder gracieux affiché).
///
/// Cohérence visuelle : on délègue à [AssetsBundlesModule] pour
/// garantir un rendu strictement identique au widget markets.
class CryptoBundlesCardEmbed extends StatefulWidget {
  const CryptoBundlesCardEmbed({
    super.key,
    required this.bundles,
    this.title,
  });

  final List<AssistanceCryptoBundleItem> bundles;

  /// Titre optionnel — **ignoré** dans la refonte v2 (pas de titre de
  /// module dans la bulle chat). Conservé dans l'API pour
  /// rétrocompatibilité du payload `crypto_bundles_card`.
  final String? title;

  @override
  State<CryptoBundlesCardEmbed> createState() => _CryptoBundlesCardEmbedState();
}

class _CryptoBundlesCardEmbedState extends State<CryptoBundlesCardEmbed> {
  final ProductCatalogApi _catalogApi = ProductCatalogApi();

  /// Map `productCode (upper)` → config CMS (image cover, perf1d,
  /// titre override, sortOrder). Vide tant que l'appel API n'a pas
  /// répondu — on rend les cards malgré tout (placeholder image).
  Map<String, ProductDisplayConfig> _displayConfigs = const {};

  @override
  void initState() {
    super.initState();
    _loadDisplayConfigs();
  }

  Future<void> _loadDisplayConfigs() async {
    try {
      final configs = await _catalogApi.getDisplayConfigs();
      if (!mounted) return;
      setState(() {
        _displayConfigs = configs.map(
          (k, v) => MapEntry(k.toUpperCase(), v),
        );
      });
    } catch (_) {
      // En cas d'erreur, on laisse `_displayConfigs` vide :
      // le widget reste fonctionnel avec placeholders d'image.
    }
  }

  /// Bundles triés par `sortOrder` (config CMS) si dispo, sinon ordre
  /// d'arrivée du payload backend.
  List<AssistanceCryptoBundleItem> get _orderedBundles {
    if (_displayConfigs.isEmpty) return widget.bundles;
    final sorted = List<AssistanceCryptoBundleItem>.from(widget.bundles);
    sorted.sort((a, b) {
      final ca = _displayConfigs[a.productCode.toUpperCase()];
      final cb = _displayConfigs[b.productCode.toUpperCase()];
      final sa = ca?.sortOrder ?? 999;
      final sb = cb?.sortOrder ?? 999;
      return sa.compareTo(sb);
    });
    return sorted;
  }

  @override
  Widget build(BuildContext context) {
    if (widget.bundles.isEmpty) {
      return _buildEmpty();
    }

    final items = _orderedBundles
        .map((b) => _toAssetsBundleItem(context, b))
        .toList(growable: false);

    // [SearchScreen] padde déjà la liste de messages avec `lg` : ne pas
    // redoubler via [AssetsBundlesModule.horizontalMargin], sinon la 1ʳᵉ
    // carte est trop rentrée vs le slider Markets (une seule marge xl là-bas,
    // ici une seule couche `lg` côté liste). [layoutWidth] aligne le calcul
    // des largeurs de cartes sur la voie utile du parent.
    return LayoutBuilder(
      builder: (context, constraints) {
        return AssetsBundlesModule(
          title: '',
          visibleCardsCount: 1.4,
          horizontalMargin: 0,
          layoutWidth: constraints.maxWidth,
          items: items,
        );
      },
    );
  }

  AssetsBundleItem _toAssetsBundleItem(
    BuildContext context,
    AssistanceCryptoBundleItem bundle,
  ) {
    final cfg = _displayConfigs[bundle.productCode.toUpperCase()];
    return AssetsBundleItem(
      imageUrl: (cfg?.headerMediaUrl?.trim().isNotEmpty ?? false)
          ? cfg!.headerMediaUrl!.trim()
          : '',
      title: (cfg?.cardTitle?.trim().isNotEmpty ?? false)
          ? cfg!.cardTitle!.trim()
          : bundle.name,
      description: bundle.description,
      performance24h: cfg?.performance1d,
      cryptoIcons: const [],
      cryptoTickers: bundle.cryptoTickers,
      onTap: () => _resolveDeepLink(
        context,
        bundle.viewDetailDeepLink,
        fallback: 'Action indisponible.',
      ),
      onInvestTap: () => _resolveDeepLink(
        context,
        bundle.investDeepLink,
        fallback: 'Investissement indisponible pour ce bundle.',
      ),
    );
  }

  Future<void> _resolveDeepLink(
    BuildContext context,
    String? deepLink, {
    required String fallback,
  }) async {
    if (deepLink == null || deepLink.isEmpty) {
      _showSnack(context, fallback);
      return;
    }
    await AssistanceDeepLinkResolver.resolve(context, deepLink);
  }

  Widget _buildEmpty() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.md,
      ),
      decoration: const BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.only(
          topLeft: Radius.zero,
          topRight: Radius.circular(AppRadius.bubble),
          bottomLeft: Radius.circular(AppRadius.bubble),
          bottomRight: Radius.circular(AppRadius.bubble),
        ),
      ),
      child: const Row(
        children: [
          KalaiIcon(KalaiIcons.info, size: 18),
          SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              "Aucun Crypto Bundle n'est disponible pour ton compte. "
              "Consulte la section Crypto Bundles dans l'app pour le détail.",
            ),
          ),
        ],
      ),
    );
  }

  void _showSnack(BuildContext context, String message) {
    final messenger = ScaffoldMessenger.maybeOf(context);
    messenger?.showSnackBar(
      SnackBar(
        content: Text(message),
        duration: const Duration(seconds: 3),
      ),
    );
  }
}
