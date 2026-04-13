import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../ui/components/transaction/marketing_features.dart';

class MarketingCardsSmallCarouselItem {
  const MarketingCardsSmallCarouselItem({
    required this.title,
    required this.description,
    required this.icon,
    required this.iconBackgroundColor,
    required this.redirectUrl,
  });

  final String title;
  final String description;
  final IconData icon;
  final Color iconBackgroundColor;
  final String redirectUrl;
}

class MarketingCardsSmallCarouselModule extends StatelessWidget {
  const MarketingCardsSmallCarouselModule({
    super.key,
    required this.items,
    this.showDots = true,
  });

  final List<MarketingCardsSmallCarouselItem> items;
  final bool showDots;

  static List<MarketingCardsSmallCarouselItem> itemsFromJson(List<dynamic> raw) {
    return raw
        .map((entry) {
          if (entry is! Map) return null;
          final map = entry.cast<String, dynamic>();
          final title = (map['title'] ?? '').toString().trim();
          final description = (map['description'] ?? '').toString().trim();
          final redirectUrl = (map['redirectUrl'] ?? '').toString().trim();
          if (title.isEmpty || description.isEmpty) return null;
          return MarketingCardsSmallCarouselItem(
            title: title,
            description: description,
            redirectUrl: redirectUrl,
            icon: _iconFromKey((map['icon'] ?? '').toString()),
            iconBackgroundColor: _colorFromHex(
              (map['iconBackgroundColor'] ?? '').toString(),
              fallback: Colors.orange,
            ),
          );
        })
        .whereType<MarketingCardsSmallCarouselItem>()
        .toList();
  }

  static IconData _iconFromKey(String key) {
    switch (key.trim().toLowerCase()) {
      case 'trending_up':
      case 'trending_up_rounded':
        return Icons.trending_up_rounded;
      case 'savings':
      case 'savings_rounded':
        return Icons.savings_rounded;
      case 'account_balance':
      case 'account_balance_rounded':
        return Icons.account_balance_rounded;
      case 'description':
      case 'description_rounded':
        return Icons.description_rounded;
      case 'payments':
      case 'payments_rounded':
        return Icons.payments_rounded;
      default:
        return Icons.auto_awesome_rounded;
    }
  }

  static Color _colorFromHex(String hex, {required Color fallback}) {
    final value = hex.trim();
    if (value.isEmpty) return fallback;
    final normalized = value.replaceFirst('#', '');
    final buffer = StringBuffer();
    if (normalized.length == 6) buffer.write('ff');
    buffer.write(normalized);
    if (buffer.length != 8) return fallback;
    final parsed = int.tryParse(buffer.toString(), radix: 16);
    return parsed == null ? fallback : Color(parsed);
  }

  Future<void> _openLink(String url) async {
    final normalized = url.trim();
    if (normalized.isEmpty) return;
    final uri = Uri.tryParse(normalized);
    if (uri == null) return;
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    final mappedItems = items
        .map(
          (item) => MarketingFeaturesItem(
            title: item.title,
            subtitle: item.description,
            icon: item.icon,
            iconBackgroundColor: item.iconBackgroundColor,
            onTap: () => _openLink(item.redirectUrl),
          ),
        )
        .toList();

    if (mappedItems.isEmpty) return const SizedBox.shrink();

    return MarketingFeatures(
      items: mappedItems,
      showDots: showDots,
    );
  }
}
