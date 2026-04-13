import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/http_error_display.dart';
import '../../../core/session_bearer_http.dart';
import '../../../design_system/components/assets_bundles_module.dart';
import '../../../design_system/components/marketing_cards_module.dart';

class VaultsApiException implements Exception {
  VaultsApiException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  @override
  String toString() => 'VaultsApiException($statusCode): $message';
}

class VaultListItem {
  const VaultListItem({
    required this.id,
    required this.slug,
    required this.title,
    this.description,
    required this.urlPath,
    required this.coverImage,
  });

  final String id;
  final String slug;
  final String title;
  final String? description;
  final String urlPath;
  final String coverImage;
}

class VaultsApi {
  VaultsApi({String? baseUrl}) : baseUrl = baseUrl ?? Config.apiBaseUrl;

  final String baseUrl;

  Future<Map<String, String>> _headers(Uri uri, String tag) =>
      SessionBearerHttp.jsonHeadersAppScoped(uri: uri, debugTag: tag);

  Future<List<VaultListItem>> getVaults() async {
    final uri = Uri.parse(Config.vaultsUrl);
    final response = await http.get(
      uri,
      headers: await _headers(uri, 'VaultsApi.getVaults'),
    );
    if (response.statusCode != 200) {
      final raw = response.body.isNotEmpty ? response.body : 'Erreur réseau';
      throw VaultsApiException(
        response.statusCode,
        userFacingHttpErrorMessage(response.statusCode, raw),
      );
    }

    if (responseBodyLooksLikeNonJsonApi(response.body)) {
      throw VaultsApiException(502, kContentTemporarilyUnavailable);
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final vaults = json['vaults'] as List<dynamic>? ?? [];
    return vaults
        .map((v) {
          if (v is! Map<String, dynamic>) return null;
          final id = v['id']?.toString() ?? '';
          final slug = v['slug']?.toString() ?? '';
          final title = v['title']?.toString() ?? slug;
          final description = v['description']?.toString();
          final urlPath = v['urlPath']?.toString() ?? '/$slug';
          final coverImage = v['coverImage']?.toString() ?? '';
          if (slug.isEmpty) return null;
          return VaultListItem(
            id: id,
            slug: slug,
            title: title,
            description: description,
            urlPath: urlPath,
            coverImage: coverImage.isNotEmpty ? coverImage : 'https://picsum.photos/seed/vault-$slug/600/400',
          );
        })
        .whereType<VaultListItem>()
        .toList();
  }

  /// Feed des modules Marketing Cards Sliding depuis les vaults.
  Future<List<VaultsMarketingCardsFeedSection>> getMarketingCardsFeed({
    String? investmentTypeSlug,
  }) async {
    final uri = Uri.parse(
      Config.vaultsMarketingCardsFeedUrl(investmentTypeSlug: investmentTypeSlug),
    );
    final response = await http.get(
      uri,
      headers: await _headers(uri, 'VaultsApi.getMarketingCardsFeed'),
    );
    if (response.statusCode != 200) {
      final raw = response.body.isNotEmpty ? response.body : 'Erreur réseau';
      throw VaultsApiException(
        response.statusCode,
        userFacingHttpErrorMessage(response.statusCode, raw),
      );
    }

    if (responseBodyLooksLikeNonJsonApi(response.body)) {
      throw VaultsApiException(502, kContentTemporarilyUnavailable);
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final sectionsRaw = json['sections'] as List<dynamic>? ?? [];
    return sectionsRaw
        .whereType<Map>()
        .map<VaultsMarketingCardsFeedSection>((s) {
          final itemsRaw = (s['items'] as List?) ?? [];
          final items = itemsRaw
              .whereType<Map>()
              .map((it) => MarketingCardItemConfig(
                    imageUrl: (it['imageUrl'] ?? '').toString().trim().isEmpty
                        ? ((s['isPortrait'] == true)
                            ? 'https://picsum.photos/600/800'
                            : 'https://picsum.photos/800/600')
                        : (it['imageUrl'] ?? '').toString().trim(),
                    redirectUrl: (it['redirectUrl'] ?? it['url'] ?? 'https://arquantix.com').toString().trim(),
                    title: (it['title'] ?? '').toString().trim().isEmpty ? null : (it['title'] ?? '').toString().trim(),
                    description: (it['description'] ?? '').toString().trim().isEmpty
                        ? null
                        : (it['description'] ?? '').toString().trim(),
                    logoLabel: (it['logoLabel'] ?? '').toString().trim().isEmpty
                        ? null
                        : (it['logoLabel'] ?? '').toString().trim(),
                    buttonLabel: (it['buttonLabel'] ?? '').toString().trim().isEmpty
                        ? null
                        : (it['buttonLabel'] ?? '').toString().trim(),
                  ))
              .toList();
          return VaultsMarketingCardsFeedSection(
            moduleType: 'marketing_cards',
            vaultSlug: (s['vaultSlug'] ?? '').toString(),
            vaultTitle: (s['vaultTitle'] ?? '').toString(),
            isPortrait: s['isPortrait'] == true,
            title: (s['title'] ?? '').toString().trim(),
            assetsBundleItems: const [],
            items: items,
          );
        })
        .where((s) => s.items.isNotEmpty)
        .toList(growable: false);
  }

  /// Charge un widget Builder par slug et résout les modules
  /// MarketingCardsSmallSlidingCarrousel_Paysage en sections affichables.
  /// Si [assetSlug] est fourni (ex. btc, eth), le feed peut être filtré par crypto (widget blog-a-la-une).
  Future<List<VaultsMarketingCardsFeedSection>> getMarketingCardsSectionsFromWidget(
    String widgetSlug, {
    String locale = 'fr',
    String? assetSlug,
    /// Incrémenté au pull-to-refresh pour éviter le cache HTTP/CDN (hot reload contenu + images).
    int? cacheBust,
  }) async {
    final queryParams = <String, String>{'locale': locale};
    if (assetSlug != null && assetSlug.trim().isNotEmpty) {
      queryParams['assetSlug'] = assetSlug.trim().toLowerCase();
    }
    if (cacheBust != null && cacheBust > 0) {
      queryParams['_t'] = cacheBust.toString();
    }
    final uri = Uri.parse(Config.flutterWidgetUrl(widgetSlug)).replace(
      queryParameters: queryParams,
    );
    final response = await http.get(
      uri,
      headers: await _headers(uri, 'VaultsApi.getMarketingCardsSectionsFromWidget'),
    );
    if (response.statusCode != 200) {
      final raw = response.body.isNotEmpty ? response.body : 'Erreur réseau';
      throw VaultsApiException(
        response.statusCode,
        userFacingHttpErrorMessage(response.statusCode, raw),
      );
    }

    if (responseBodyLooksLikeNonJsonApi(response.body)) {
      throw VaultsApiException(502, kContentTemporarilyUnavailable);
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final widgetRaw = json['widget'];
    final feedsRaw = json['feeds'];
    if (widgetRaw is! Map || feedsRaw is! Map) {
      return const [];
    }

    final schema = (widgetRaw['schemaJson'] as Map?)?.cast<String, dynamic>() ?? const {};
    final widgetTitle = (schema['title'] ?? '').toString().trim();
    final titleRedirect =
        (schema['titleRedirect'] as Map?)?.cast<String, dynamic>() ?? const {};
    final titleRedirectType = (titleRedirect['type'] ?? '').toString().trim().toLowerCase();
    final titleRedirectTarget = (titleRedirect['target'] ?? '').toString().trim();
    final widgetTitleRedirect = titleRedirectType == 'internal' && titleRedirectTarget.isNotEmpty
        ? titleRedirectTarget
        : null;
    final modules = (schema['modules'] as List?) ?? const [];
    final feeds = feedsRaw.cast<String, dynamic>();
    final sections = <VaultsMarketingCardsFeedSection>[];

    int? readIntOrder(Map<String, dynamic> map, List<String> keys) {
      for (final key in keys) {
        final raw = map[key];
        if (raw is num) return raw.toInt();
        if (raw is String) {
          final parsed = int.tryParse(raw.trim());
          if (parsed != null) return parsed;
        }
      }
      return null;
    }

    int? readAdminSortOrder(Map<String, dynamic> map) {
      return readIntOrder(map, const ['sortOrder', 'order']);
    }

    int? readDbOrder(Map<String, dynamic> map) {
      final raw = map['dbOrder'];
      if (raw is num) return raw.toInt();
      if (raw is String) return int.tryParse(raw.trim());
      return null;
    }

    List<Map<String, dynamic>> orderedFeedItems(List<dynamic> rawItems) {
      final indexed = rawItems
          .whereType<Map>()
          .map((it) => it.cast<String, dynamic>())
          .toList()
          .asMap()
          .entries
          .map((e) {
        final adminOrder = readAdminSortOrder(e.value);
        final dbOrder = readDbOrder(e.value);
        return (
          idx: e.key,
          adminOrder: adminOrder ?? 999999,
          dbOrder: dbOrder ?? (100000 + e.key),
          item: e.value,
        );
      }).toList();
      indexed.sort((a, b) {
        final byOrder = a.adminOrder.compareTo(b.adminOrder);
        if (byOrder != 0) return byOrder;
        final byDbOrder = a.dbOrder.compareTo(b.dbOrder);
        if (byDbOrder != 0) return byDbOrder;
        return a.idx.compareTo(b.idx);
      });
      return indexed.map((e) => e.item).toList(growable: false);
    }

    for (final module in modules) {
      if (module is! Map) continue;
      final m = module.cast<String, dynamic>();
      final type = (m['type'] ?? '').toString().trim().toLowerCase();

      final feedSlug = (m['feedSlug'] ?? '').toString().trim();
      if (feedSlug.isEmpty) continue;
      final feed = feeds[feedSlug];
      if (feed is! Map) continue;
      final feedMap = feed.cast<String, dynamic>();
      final feedType = (feedMap['feedType'] ?? '').toString().trim().toLowerCase();
      final itemsRaw = (feedMap['items'] as List?) ?? const [];
      final feedBinding =
          (m['feedBinding'] as Map?)?.cast<String, dynamic>() ?? const {};
      final itemToCard =
          (feedBinding['itemToCard'] as Map?)?.cast<String, dynamic>() ?? const {};
      final moduleDescription = (m['description'] ?? '').toString().trim();
      final visibleCardsCountRaw = m['visibleCardsCount'];
      final visibleCardsCount = visibleCardsCountRaw is num
          ? visibleCardsCountRaw.toDouble()
          : double.tryParse((visibleCardsCountRaw ?? '').toString().trim().replaceAll(',', '.'));
      final cardAspectRatio = (m['cardAspectRatio'] ?? '').toString().trim();

      String mapKey(String fallback) =>
          (itemToCard[fallback] ?? fallback).toString().trim();

      final imageKey = mapKey('imageUrl');
      final redirectKey = mapKey('redirectUrl');
      final titleKey = mapKey('title');
      final descriptionKey = mapKey('description');

      final orderedItemsRaw = orderedFeedItems(itemsRaw);

      if (type == 'topcryptomodule' || type == 'top_crypto_module') {
        final tabs = (m['tabs'] as Map?)?.cast<String, dynamic>() ?? const {};
        final popularLabel = (tabs['popular'] ?? 'Populaires').toString().trim();
        final gainersLabel = (tabs['gainers'] ?? 'Top Gainers').toString().trim();
        final losersLabel = (tabs['losers'] ?? 'Top Losers').toString().trim();
        final seeMoreLabel = (m['seeMoreLabel'] ?? 'See more').toString().trim();
        final seeMoreRedirect = (m['seeMoreRedirect'] ?? '').toString().trim();

        final popularRaw = (feedMap['popular'] as List?) ?? const [];
        final gainersRaw = (feedMap['topGainers'] as List?) ?? const [];
        final losersRaw = (feedMap['topLosers'] as List?) ?? const [];

        TopCryptoFeedItem mapCrypto(dynamic raw) {
          final it = (raw is Map ? raw.cast<String, dynamic>() : const <String, dynamic>{});
          final name = (it['name'] ?? '').toString().trim();
          final ticker = (it['ticker'] ?? '').toString().trim();
          final price = (it['price'] ?? '').toString().trim();
          final redirectUrl = (it['redirectUrl'] ?? '').toString().trim();
          final variationRaw = it['variationPercent'];
          final variation = variationRaw is num
              ? variationRaw.toDouble()
              : double.tryParse((variationRaw ?? '').toString().replaceAll(',', '.')) ?? 0;
          return TopCryptoFeedItem(
            name: name.isEmpty ? 'Crypto' : name,
            ticker: ticker.isEmpty ? '---' : ticker,
            price: price.isEmpty ? '-' : price,
            variationPercent: variation,
            redirectUrl: redirectUrl.isNotEmpty
                ? redirectUrl
                : (ticker.isEmpty ? '' : 'crypto://${ticker.toLowerCase()}'),
          );
        }

        final popular = popularRaw.map(mapCrypto).toList(growable: false);
        final gainers = gainersRaw.map(mapCrypto).toList(growable: false);
        final losers = losersRaw.map(mapCrypto).toList(growable: false);

        sections.add(
          VaultsMarketingCardsFeedSection(
            moduleType: 'top_crypto_module',
            vaultSlug: '',
            vaultTitle: (m['title'] ?? '').toString().trim(),
            isPortrait: false,
            title: (m['title'] ?? '').toString().trim(),
            description: moduleDescription.isEmpty ? null : moduleDescription,
            visibleCardsCount: null,
            cardAspectRatio: null,
            widgetHeaderTitle: widgetTitle.isNotEmpty ? widgetTitle : null,
            widgetHeaderRedirect: widgetTitleRedirect,
            topCryptoPopularLabel: popularLabel,
            topCryptoGainersLabel: gainersLabel,
            topCryptoLosersLabel: losersLabel,
            topCryptoSeeMoreLabel: seeMoreLabel,
            topCryptoSeeMoreRedirect: seeMoreRedirect.isEmpty ? null : seeMoreRedirect,
            topCryptoPopularItems: popular,
            topCryptoGainersItems: gainers,
            topCryptoLosersItems: losers,
            blogItems: const [],
            assetsBundleItems: const [],
            items: const [],
          ),
        );
        continue;
      }
      final items = orderedItemsRaw
          .map((it) {
            final image = (it[imageKey] ?? '').toString().trim();
            final redirect = (it[redirectKey] ?? '').toString().trim();
            final slug = (it['slug'] ?? '').toString().trim();
            final title = (it[titleKey] ?? '').toString().trim();
            final description = (it[descriptionKey] ?? '').toString().trim();
            final isVaultFeed = feedType == 'vaults_by_investment_type';
            final isNewsFeed = feedType == 'top10_news' || feedType == 'blog_articles';
            final internalRedirect = slug.isEmpty
                ? ''
                : isVaultFeed
                    ? 'vault://$slug'
                    : isNewsFeed
                        ? 'blog://$slug'
                        : '';
            final effectiveRedirect = internalRedirect.isNotEmpty
                ? internalRedirect
                : (redirect.isEmpty ? 'https://arquantix.com' : redirect);
            return MarketingCardItemConfig(
              imageUrl: image.isEmpty
                  ? 'https://picsum.photos/800/600'
                  : image,
              redirectUrl: effectiveRedirect,
              title: title.isEmpty ? null : title,
              description: description.isEmpty ? null : description,
            );
          })
          .toList();

      if (type == 'blogalaune' || type == 'blog_a_la_une') {
        final blogItems = orderedItemsRaw
            .map((it) {
              final cover = (it[itemToCard['coverUrl'] ?? 'coverUrl'] ?? '').toString().trim();
              final redirect = (it[itemToCard['redirectUrl'] ?? 'redirectUrl'] ?? '').toString().trim();
              final slug = (it['slug'] ?? '').toString().trim();
              final title = (it[itemToCard['title'] ?? 'title'] ?? '').toString().trim();
              final tag = (it[itemToCard['tag'] ?? 'categoryLabel'] ?? '').toString().trim();
              List<String>? tagList;
              final tagsRaw = it[itemToCard['tags'] ?? 'tags'] ??
                  it['categoryLabels'] ??
                  it['tagLabels'];
              if (tagsRaw is List) {
                tagList = tagsRaw
                    .map((e) => e.toString().trim())
                    .where((s) => s.isNotEmpty)
                    .toList(growable: false);
                if (tagList.isEmpty) tagList = null;
              }
              final publishedDate =
                  (it[itemToCard['metaText'] ?? 'publishedDate'] ?? '').toString().trim();
              final authorName =
                  (it[itemToCard['authorName'] ?? 'authorName'] ?? '').toString().trim();
              final readingRaw = it[itemToCard['readingTime'] ?? 'readingTime'];
              final readingTime = readingRaw is num
                  ? readingRaw.toInt()
                  : int.tryParse((readingRaw ?? '').toString()) ?? 1;
              final internalRedirect = slug.isNotEmpty ? 'blog://$slug' : '';
              return WidgetBlogItem(
                title: title.isEmpty ? 'Article' : title,
                coverUrl: cover.isEmpty ? 'https://picsum.photos/800/600' : cover,
                readingTime: readingTime < 1 ? 1 : readingTime,
                redirectUrl: internalRedirect.isNotEmpty
                    ? internalRedirect
                    : (redirect.isEmpty ? 'https://arquantix.com' : redirect),
                tag: tag.isEmpty ? null : tag,
                tags: tagList,
                metaText: publishedDate.isEmpty ? null : publishedDate,
                authorName: authorName.isEmpty ? null : authorName,
              );
            })
            .toList();
        if (blogItems.isEmpty) continue;
        sections.add(
          VaultsMarketingCardsFeedSection(
            moduleType: 'blog_a_la_une',
            vaultSlug: '',
            vaultTitle: (m['title'] ?? '').toString().trim(),
            isPortrait: false,
            title: (m['title'] ?? '').toString().trim(),
            description: moduleDescription.isEmpty ? null : moduleDescription,
            visibleCardsCount: null,
            cardAspectRatio: null,
            widgetHeaderTitle: widgetTitle.isNotEmpty ? widgetTitle : null,
            widgetHeaderRedirect: widgetTitleRedirect,
            blogItems: blogItems,
            assetsBundleItems: const [],
            items: const [],
          ),
        );
        continue;
      }

      if (type == 'assetsbundlesmodule' || type == 'assets_bundles_module') {
        final bundleItems = orderedItemsRaw
            .map((it) {
              final image = (it[itemToCard['imageUrl'] ?? 'imageUrl'] ?? '').toString().trim();
              final redirect = (it[itemToCard['redirectUrl'] ?? 'redirectUrl'] ?? '').toString().trim();
              final title = (it[itemToCard['title'] ?? 'title'] ?? '').toString().trim();
              final description =
                  (it[itemToCard['description'] ?? 'description'] ?? '').toString().trim();
              final perfRaw = it[itemToCard['performance24h'] ?? 'performance24h'];
              final perf = perfRaw is num ? perfRaw.toDouble() : double.tryParse('$perfRaw');
              final iconCountRaw = it[itemToCard['instrumentCount'] ?? 'instrumentCount'];
              final iconCount = iconCountRaw is num
                  ? iconCountRaw.toInt()
                  : int.tryParse('$iconCountRaw') ?? 0;
              return WidgetAssetsBundleItem(
                imageUrl: image.isEmpty ? 'https://picsum.photos/800/600' : image,
                redirectUrl: redirect.isEmpty ? 'https://arquantix.com' : redirect,
                title: title.isEmpty ? 'Bundle crypto' : title,
                description: description.isEmpty ? null : description,
                performance24h: perf,
                instrumentCount: iconCount < 0 ? 0 : iconCount,
              );
            })
            .toList();
        if (bundleItems.isEmpty) continue;
        final showOverlayRaw = m['showImageOverlay'];
        final showImageOverlay = showOverlayRaw == true ||
            (showOverlayRaw is String && (showOverlayRaw == 'true' || showOverlayRaw == '1'));
        sections.add(
          VaultsMarketingCardsFeedSection(
            moduleType: 'assets_bundles_module',
            vaultSlug: '',
            vaultTitle: (m['title'] ?? '').toString().trim(),
            isPortrait: false,
            title: (m['title'] ?? '').toString().trim(),
            description: moduleDescription.isEmpty ? null : moduleDescription,
            visibleCardsCount: null,
            cardAspectRatio: null,
            showImageOverlay: showImageOverlay ? true : null,
            widgetHeaderTitle: widgetTitle.isNotEmpty ? widgetTitle : null,
            widgetHeaderRedirect: widgetTitleRedirect,
            blogItems: const [],
            assetsBundleItems: bundleItems,
            items: const [],
          ),
        );
        continue;
      }

      final isMarketingCardsLandscape =
          type == 'marketingcardssmallslidingcarrousel_paysage';
      final isMarketingCardsPortrait =
          type == 'marketingcardssmallslidingcarrousel_portrait';
      if (!isMarketingCardsLandscape && !isMarketingCardsPortrait) continue;
      if (items.isEmpty) continue;
      sections.add(
        VaultsMarketingCardsFeedSection(
          moduleType: 'marketing_cards',
          vaultSlug: '',
          vaultTitle: (m['title'] ?? '').toString().trim(),
          isPortrait: isMarketingCardsPortrait,
          title: (m['title'] ?? '').toString().trim(),
          description: moduleDescription.isEmpty ? null : moduleDescription,
          visibleCardsCount: visibleCardsCount,
          cardAspectRatio: cardAspectRatio.isEmpty ? null : cardAspectRatio,
          widgetHeaderTitle: widgetTitle.isNotEmpty ? widgetTitle : null,
          widgetHeaderRedirect: widgetTitleRedirect,
          blogItems: const [],
          assetsBundleItems: const [],
          items: items,
        ),
      );
    }

    return sections;
  }
}

class VaultsMarketingCardsFeedSection {
  const VaultsMarketingCardsFeedSection({
    required this.moduleType,
    required this.vaultSlug,
    required this.vaultTitle,
    required this.isPortrait,
    required this.title,
    this.description,
    this.visibleCardsCount,
    this.cardAspectRatio,
    this.showImageOverlay,
    this.widgetHeaderTitle,
    this.widgetHeaderRedirect,
    this.topCryptoPopularLabel,
    this.topCryptoGainersLabel,
    this.topCryptoLosersLabel,
    this.topCryptoSeeMoreLabel,
    this.topCryptoSeeMoreRedirect,
    this.topCryptoPopularItems = const [],
    this.topCryptoGainersItems = const [],
    this.topCryptoLosersItems = const [],
    this.blogItems = const [],
    this.assetsBundleItems = const [],
    required this.items,
  });

  final String moduleType;
  final String vaultSlug;
  final String vaultTitle;
  final bool isPortrait;
  final String title;
  final String? description;
  final double? visibleCardsCount;
  final String? cardAspectRatio;
  /// Filtre gris sur l'image des cartes (assets_bundles_module). Si null/false, pas d'overlay. Modifiable en base / admin.
  final bool? showImageOverlay;
  final String? widgetHeaderTitle;
  final String? widgetHeaderRedirect;
  final String? topCryptoPopularLabel;
  final String? topCryptoGainersLabel;
  final String? topCryptoLosersLabel;
  final String? topCryptoSeeMoreLabel;
  final String? topCryptoSeeMoreRedirect;
  final List<TopCryptoFeedItem> topCryptoPopularItems;
  final List<TopCryptoFeedItem> topCryptoGainersItems;
  final List<TopCryptoFeedItem> topCryptoLosersItems;
  final List<WidgetBlogItem> blogItems;
  final List<WidgetAssetsBundleItem> assetsBundleItems;
  final List<MarketingCardItemConfig> items;
}

class TopCryptoFeedItem {
  const TopCryptoFeedItem({
    required this.name,
    required this.ticker,
    required this.price,
    required this.variationPercent,
    required this.redirectUrl,
  });

  final String name;
  final String ticker;
  final String price;
  final double variationPercent;
  final String redirectUrl;
}

class WidgetBlogItem {
  const WidgetBlogItem({
    required this.title,
    required this.coverUrl,
    required this.readingTime,
    required this.redirectUrl,
    this.tag,
    this.tags,
    this.metaText,
    this.authorName,
  });

  final String title;
  final String coverUrl;
  final int readingTime;
  final String redirectUrl;
  /// Libellé unique (rétrocompat) — ignoré en affichage si [tags] est non vide.
  final String? tag;
  /// Plusieurs libellés (ex. catégories) — prioritaires sur [tag] si non vide.
  final List<String>? tags;
  final String? metaText;
  final String? authorName;
}

class WidgetAssetsBundleItem {
  const WidgetAssetsBundleItem({
    required this.imageUrl,
    required this.redirectUrl,
    required this.title,
    this.description,
    this.performance24h,
    required this.instrumentCount,
  });

  final String imageUrl;
  final String redirectUrl;
  final String title;
  final String? description;
  final double? performance24h;
  final int instrumentCount;

  AssetsBundleItem toAssetsBundleItem(void Function(String url) onRedirect) {
    final iconCount = instrumentCount <= 0 ? 1 : instrumentCount;
    return AssetsBundleItem(
      imageUrl: imageUrl,
      title: title,
      description: description,
      performance24h: performance24h,
      cryptoIcons: List<IconData>.filled(iconCount, Icons.currency_bitcoin),
      onTap: () => onRedirect(redirectUrl),
    );
  }
}
