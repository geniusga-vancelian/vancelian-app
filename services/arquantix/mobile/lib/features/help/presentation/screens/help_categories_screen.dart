import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../data/help_api.dart';
import '../../domain/models/help_center_models.dart';
import 'help_articles_screen.dart';
import 'help_widgets.dart';

class HelpCategoriesScreen extends StatefulWidget {
  const HelpCategoriesScreen({
    super.key,
    required this.collectionSlug,
    required this.collectionTitle,
  });

  final String collectionSlug;
  final String collectionTitle;

  @override
  State<HelpCategoriesScreen> createState() => _HelpCategoriesScreenState();
}

class _HelpCategoriesScreenState extends State<HelpCategoriesScreen> {
  final HelpApi _api = HelpApi();
  final TextEditingController _searchController = TextEditingController();
  bool _loading = true;
  String? _error;
  List<HelpCategoryItem> _categories = const [];

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
      final response =
          await _api.getCategories(collectionSlug: widget.collectionSlug);
      if (!mounted) return;
      setState(() {
        _categories = response.categories;
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

  List<HelpCategoryItem> get _filtered {
    final q = _searchController.text.trim().toLowerCase();
    if (q.isEmpty) return _categories;
    return _categories.where((item) {
      final base =
          '${item.title} ${item.description ?? ''}'.toLowerCase();
      return base.contains(q);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return PageSimpleNavBarTopTitlePageContent(
      pageTitle: widget.collectionTitle,
      onBackTap: () => Navigator.of(context).pop(),
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
      return SizedBox(
        height: 220,
        child: Center(
          child: Text(
            _error!,
            style: AppTypography.bodyMedium
                .copyWith(color: AppColors.errorText),
          ),
        ),
      );
    }
    return HelpChevronCardList(
      items: _filtered
          .map(
            (c) => HelpChevronCardItem(
              title: c.title,
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => HelpArticlesScreen(
                      collectionSlug: widget.collectionSlug,
                      collectionTitle: widget.collectionTitle,
                      categorySlug: c.slug,
                      categoryTitle: c.title,
                    ),
                  ),
                );
              },
            ),
          )
          .toList(),
    );
  }
}
