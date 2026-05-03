import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../data/help_api.dart';
import '../../domain/models/help_center_models.dart';
import 'help_categories_screen.dart';
import 'help_search_layer.dart';
import 'help_widgets.dart';

class HelpCenterScreen extends StatefulWidget {
  const HelpCenterScreen({super.key, this.onBack});

  final VoidCallback? onBack;

  @override
  State<HelpCenterScreen> createState() => _HelpCenterScreenState();
}

class _HelpCenterScreenState extends State<HelpCenterScreen> {
  final HelpApi _api = HelpApi();
  final TextEditingController _searchController = TextEditingController();
  final FocusNode _searchFocusNode = FocusNode();
  bool _loading = true;
  String? _error;
  List<HelpCollectionItem> _collections = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _searchController.dispose();
    _searchFocusNode.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final collections = await _api.getCollections(locale: 'fr');
      if (!mounted) return;
      setState(() {
        _collections = collections;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e.toString();
      });
    }
  }

  /// Sous-titre cas 3 DS : champ CMS ou repli sur le nombre d’articles.
  String? _collectionDescription(HelpCollectionItem item) {
    final sub = item.subtitle?.trim();
    if (sub != null && sub.isNotEmpty) return sub;
    final desc = item.description?.trim();
    if (desc != null && desc.isNotEmpty) return desc;
    final n = item.articleCount;
    if (n <= 0) return null;
    if (n == 1) return '1 article';
    return '$n articles';
  }

  /// Icône métadonnée `iconKey` (CMS) — mêmes clés que l’admin Help Collection.
  IconData _iconForCollection(HelpCollectionItem item) {
    final iconKey = (item.iconKey ?? '').trim().toLowerCase();
    switch (iconKey) {
      case 'wallet':
        return Icons.account_balance_wallet_outlined;
      case 'users':
        return Icons.groups_outlined;
      case 'user':
        return Icons.person_outline_rounded;
      case 'bell':
        return Icons.notifications_none_rounded;
      case 'settings':
        return Icons.settings_outlined;
      case 'home':
        return Icons.home_outlined;
      case 'star':
        return Icons.star_outline_rounded;
      case 'zap':
        return Icons.bolt_rounded;
      case 'lock':
        return Icons.lock_outline_rounded;
      case 'key':
        return Icons.key_rounded;
      case 'mail':
        return Icons.mail_outline_rounded;
      case 'phone':
        return Icons.phone_iphone_rounded;
      case 'globe':
        return Icons.public_rounded;
      case 'pie-chart':
        return Icons.pie_chart_outline_rounded;
      case 'briefcase':
        return Icons.work_outline_rounded;
      case 'calculator':
        return Icons.calculate_outlined;
      case 'clipboard-list':
        return Icons.checklist_rounded;
      case 'clock':
        return Icons.schedule_rounded;
      case 'landmark':
        return Icons.account_balance_rounded;
      case 'receipt':
        return Icons.receipt_long_rounded;
      case 'percent':
        return Icons.percent_rounded;
      case 'dollar-sign':
        return Icons.attach_money_rounded;
      case 'gift':
        return Icons.card_giftcard_rounded;
      case 'heart':
        return Icons.favorite_border_rounded;
      case 'info':
        return Icons.info_outline_rounded;
      case 'lightbulb':
        return Icons.lightbulb_outline_rounded;
      case 'map-pin':
        return Icons.place_outlined;
      case 'megaphone':
        return Icons.campaign_outlined;
      case 'package':
        return Icons.inventory_2_outlined;
      case 'search':
        return Icons.search_rounded;
      case 'sparkles':
        return Icons.auto_awesome_rounded;
      case 'truck':
        return Icons.local_shipping_outlined;
      case 'umbrella':
        return Icons.umbrella_rounded;
      case 'building':
      case 'bank':
      case 'account-balance':
        return Icons.account_balance_rounded;
      case 'shield':
      case 'security':
        return Icons.shield_rounded;
      case 'card':
      case 'credit-card':
        return Icons.credit_card_rounded;
      case 'swap':
      case 'payment':
      case 'virement':
        return Icons.swap_horiz_rounded;
      case 'trending-up':
      case 'investment':
        return Icons.trending_up_rounded;
      case 'book':
      case 'article':
      case 'file-text':
        return Icons.article_outlined;
      case 'help-circle':
      case 'help':
        return Icons.help_outline_rounded;
      default:
        final normalized = item.slug.toLowerCase();
        if (normalized.contains('account') ||
            normalized.contains('compte')) {
          return Icons.account_balance_rounded;
        }
        if (normalized.contains('security') ||
            normalized.contains('fraud')) {
          return Icons.shield_rounded;
        }
        if (normalized.contains('card') || normalized.contains('carte')) {
          return Icons.credit_card_rounded;
        }
        if (normalized.contains('payment') ||
            normalized.contains('virement')) {
          return Icons.swap_horiz_rounded;
        }
        if (normalized.contains('invest')) {
          return Icons.trending_up_rounded;
        }
        return Icons.article_outlined;
    }
  }

  @override
  Widget build(BuildContext context) {
    return PageSimpleNavBarTopTitlePageContent(
      pageTitle: 'Centre d\'aide',
      onBackTap: widget.onBack,
      onRefresh: _load,
      content: [
        HelpSearchBar(
          controller: _searchController,
          focusNode: _searchFocusNode,
        ),
        const SizedBox(height: AppSpacing.xxl),
        HelpDualSearchBody(
          controller: _searchController,
          focusNode: _searchFocusNode,
          helpApi: _api,
          normalBody: _buildBody(),
        ),
      ],
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const SizedBox(
        height: 220,
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (_error != null) {
      return _buildError(_error!);
    }
    if (_collections.isEmpty) {
      return const HelpEmptyResults();
    }
    return ListCardModule(
      items: _collections
          .map(
            (item) => ListCardItem(
              icon: _iconForCollection(item),
              title: item.title,
              description: _collectionDescription(item),
              showChevron: true,
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => HelpCategoriesScreen(
                      collectionSlug: item.slug,
                      collectionTitle: item.title,
                    ),
                  ),
                );
              },
            ),
          )
          .toList(),
    );
  }

  Widget _buildError(String msg) {
    return SizedBox(
      height: 220,
      child: Center(
        child: Text(
          msg,
          style:
              AppTypography.bodyMedium.copyWith(color: AppColors.errorText),
        ),
      ),
    );
  }
}
