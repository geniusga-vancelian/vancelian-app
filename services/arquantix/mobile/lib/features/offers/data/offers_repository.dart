import 'dart:developer' as developer;

import 'package:flutter/foundation.dart';

import '../../../core/config.dart';
import '../domain/catalog_offer_mapper.dart';
import '../domain/models/offer_project.dart';
import 'catalog_api.dart';
import 'offers_api.dart';

/// Répository des offres exclusives : **catalogue unifié** (canonique) avec repli
/// transitoire sur GET /api/projects ([OffersApi]).
///
/// Source données : `packaged_products` + Vault Builder via
/// `GET /api/mobile/flutter/catalog/products?type=exclusive_offer` (Product Registry).
///
/// Phase 8Bis : création EO depuis l’admin Vault Builder → souvent **draft** jusqu’à publication ;
/// la liste par défaut côté BFF = **published** uniquement. Voir [Config.catalogListCommercialStatus].
///
/// Phase 8 — Désactiver le repli : `FALLBACK_LEGACY_PROJECTS_ON_CATALOG_FAILURE=false`
/// (puis supprimer le repli une fois la prod validée ; voir doc Product Registry).
class OffersRepository {
  final OffersApi _api = OffersApi();
  final CatalogApi _catalogApi = CatalogApi();

  /// Liste des offres exclusives : Product Registry si activé, sinon projets CMS.
  Future<List<OfferProject>> getProjects() async {
    if (!Config.useCatalogForExclusiveOffers) {
      return _api.getProjects(limit: 50);
    }
    try {
      final items = await _catalogApi.getProducts(
        limit: 50,
        commercialStatus: Config.catalogListCommercialStatus.isEmpty
            ? null
            : Config.catalogListCommercialStatus,
        visibility:
            Config.catalogListVisibility.isEmpty ? null : Config.catalogListVisibility,
      );
      return items.map(CatalogOfferMapper.fromListItem).toList();
    } catch (e, st) {
      if (Config.fallbackLegacyProjectsOnCatalogFailure) {
        // Toujours émettre (logcat / Xcode) — le repli ne doit pas être « silencieux » en pilote/prod.
        developer.log(
          '[OffersRepository] Catalog API failed → fallback GET /api/projects (legacy). '
          'Disable fallback: FALLBACK_LEGACY_PROJECTS_ON_CATALOG_FAILURE=false',
          name: 'OffersRepository',
          level: 900, // warning
          error: e,
          stackTrace: st,
        );
        if (kDebugMode) {
          debugPrint('[OffersRepository] fallback (debug): $e');
        }
        return _api.getProjects(limit: 50);
      }
      rethrow;
    }
  }
}
