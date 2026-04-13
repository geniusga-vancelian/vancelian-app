import 'package:arquantix_news/features/offers/domain/catalog_offer_mapper.dart';
import 'package:arquantix_news/features/offers/domain/models/catalog_product.dart';
import 'package:arquantix_news/features/offers/domain/models/offer_project.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('CatalogOfferMapper', () {
    test('fromListItem maps legacy id and lending snapshot', () {
      final item = CatalogListItem.fromJson({
        'id': 'pack-1',
        'slug': 'my-offer',
        'legacyProjectId': 'proj-legacy',
        'productType': 'exclusive_offer',
        'title': 'Titre',
        'subtitle': 'Sous-titre',
        'coverUrl': 'https://x/cover.png',
        'category': 'real-estate',
        'engine': {
          'type': 'lending',
          'referenceId': 'ref',
          'snapshot': {
            'supply_apr': 11.5,
            'current_raised': 100000,
            'target_size': 1000000,
            'progress_pct': 10,
            'investors_count': 42,
            'product_id': 'prod-uuid',
            'asset': 'EUR',
            'status': 'fundraising',
          },
        },
      });

      final p = CatalogOfferMapper.fromListItem(item);
      expect(p.id, 'proj-legacy');
      expect(p.catalogSlug, 'my-offer');
      expect(p.packagedProductId, 'pack-1');
      expect(p.apy, 11.5);
      expect(p.raised, 100000);
      expect(p.target, 1000000);
      expect(p.progress, 10);
      expect(p.investorsCount, 42);
      expect(p.lendingProductId, 'prod-uuid');
      expect(p.isInvestable, isTrue);
      expect(p.lendingAsset, 'EUR');
    });

    test('mergeWithDetail prefers legacy id from packaged meta', () {
      const base = OfferProject(
        id: 'pack-1',
        imageUrl: '',
        title: 'Old',
        category: 'Real estate',
        catalogSlug: 'slug-a',
        packagedProductId: 'pack-1',
      );
      final detail = CatalogProductDetail.fromJson({
        'packagedProduct': {
          'id': 'pack-1',
          'slug': 'slug-a',
          'legacyProjectId': 'cms-proj',
          'productType': 'exclusive_offer',
          'categorySlug': 'energy',
        },
        'presentation': {'title': 'New title', 'subtitle': 'Sub', 'coverUrl': 'https://c.png'},
        'vault': {
          'data': {
            'modules': [
              {
                'type': 'SimpleMarkdownContentModule',
                'content': {
                  'moduleTitle': 'À propos',
                  'markdown': 'Hello',
                  'links': [],
                },
              },
            ],
          },
        },
        'engine': {
          'type': 'lending',
          'referenceId': null,
          'snapshot': null,
        },
      });

      final merged = CatalogOfferMapper.mergeWithDetail(base, detail);
      expect(merged.id, 'cms-proj');
      expect(merged.title, 'New title');
      expect(merged.description, 'Hello');
      expect(merged.category, 'Energy');
    });

    test('mergeWithDetail leaves base lending when snapshot absent', () {
      const base = OfferProject(
        id: 'x',
        imageUrl: '',
        title: 'T',
        category: 'Real estate',
        apy: 7,
        raised: 1,
        target: 10,
        progress: 10,
      );
      final detail = CatalogProductDetail.fromJson({
        'packagedProduct': {
          'id': 'x',
          'slug': 's',
          'productType': 'exclusive_offer',
        },
        'presentation': {'title': 'T', 'subtitle': null, 'coverUrl': null},
        'vault': {'data': null},
        'engine': {'type': null, 'referenceId': null, 'snapshot': null},
      });
      final merged = CatalogOfferMapper.mergeWithDetail(base, detail);
      expect(merged.apy, 7);
      expect(merged.target, 10);
    });

    test('mergeWithDetail maps ContentBasDePageSansModuleBlanc to bottomPageMarkdown', () {
      const base = OfferProject(
        id: 'x',
        imageUrl: '',
        title: 'T',
        category: 'Real estate',
        catalogSlug: 'slug',
      );
      final detail = CatalogProductDetail.fromJson({
        'packagedProduct': {
          'id': 'x',
          'slug': 'slug',
          'productType': 'exclusive_offer',
        },
        'presentation': {'title': 'T', 'subtitle': null, 'coverUrl': null},
        'vault': {
          'data': {
            'modules': [
              {
                'type': 'ContentBasDePageSansModuleBlanc',
                'enabled': true,
                'content': {
                  'markdown':
                      'En participant, vous acceptez nos [CGU](https://arquantix.com).',
                },
              },
            ],
          },
        },
        'engine': {'type': null, 'referenceId': null, 'snapshot': null},
      });
      final merged = CatalogOfferMapper.mergeWithDetail(base, detail);
      expect(
        merged.bottomPageMarkdown,
        'En participant, vous acceptez nos [CGU](https://arquantix.com).',
      );
    });

    test('mergeWithDetail maps SimpleMarkdown moduleTitle to descriptionModuleTitle', () {
      const base = OfferProject(
        id: 'x',
        imageUrl: '',
        title: 'T',
        category: 'Real estate',
        catalogSlug: 'slug',
      );
      final detail = CatalogProductDetail.fromJson({
        'packagedProduct': {
          'id': 'x',
          'slug': 'slug',
          'productType': 'exclusive_offer',
        },
        'presentation': {'title': 'T', 'subtitle': null, 'coverUrl': null},
        'vault': {
          'data': {
            'modules': [
              {
                'type': 'SimpleMarkdownContentModule',
                'content': {
                  'moduleTitle': 'Présentation du programme',
                  'markdown': 'Corps',
                  'links': [],
                },
              },
            ],
          },
        },
        'engine': {'type': null, 'referenceId': null, 'snapshot': null},
      });
      final merged = CatalogOfferMapper.mergeWithDetail(base, detail);
      expect(merged.descriptionModuleTitle, 'Présentation du programme');
      expect(merged.description, 'Corps');
    });

    test('mergeWithDetail maps TitlePage promoVideoUrls', () {
      const base = OfferProject(
        id: 'x',
        imageUrl: '',
        title: 'T',
        category: 'Real estate',
        catalogSlug: 'slug',
      );
      final detail = CatalogProductDetail.fromJson({
        'packagedProduct': {
          'id': 'x',
          'slug': 'slug',
          'productType': 'exclusive_offer',
        },
        'presentation': {'title': 'T', 'subtitle': null, 'coverUrl': null},
        'vault': {
          'data': {
            'modules': [
              {
                'type': 'TitlePage',
                'content': {
                  'promoVideoUrls': ['https://v.example.com/a', 'https://v.example.com/b'],
                },
              },
            ],
          },
        },
        'engine': {'type': null, 'referenceId': null, 'snapshot': null},
      });
      final merged = CatalogOfferMapper.mergeWithDetail(base, detail);
      expect(merged.promoVideoUrls.length, 2);
      expect(merged.teaserVideoUrl, 'https://v.example.com/a');
    });
  });
}
