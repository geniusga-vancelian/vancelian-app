import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../data/help_api.dart';
import '../../domain/models/help_center_models.dart';
import 'help_categories_screen.dart';
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
  bool _loading = true;
  String? _error;
  List<HelpCollectionItem> _collections = const [];

  @override
  void initState() {
    super.initState();
    _load();
    _searchController.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _searchController.dispose();
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

  List<HelpCollectionItem> get _filtered {
    final q = _searchController.text.trim().toLowerCase();
    if (q.isEmpty) return _collections;
    return _collections.where((item) {
      final base =
          '${item.title} ${item.subtitle ?? ''} ${item.description ?? ''}'
              .toLowerCase();
      return base.contains(q);
    }).toList();
  }

  IconData _iconForCollection(HelpCollectionItem item) {
    final iconKey = (item.iconKey ?? '').trim().toLowerCase();
    switch (iconKey) {
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
        HelpSearchBar(controller: _searchController),
        const SizedBox(height: AppSpacing.xxl),
        _buildBody(),
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
    return HelpChevronCardList(
      items: _filtered
          .map(
            (item) => HelpChevronCardItem(
              title: item.title,
              leadingIcon: _iconForCollection(item),
              leadingBackgroundColor:
                  AppColors.textPrimary.withValues(alpha: 0.06),
              leadingIconColor: AppColors.textPrimary,
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
