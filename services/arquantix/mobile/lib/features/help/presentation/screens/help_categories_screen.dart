import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../data/help_api.dart';
import '../../domain/models/help_center_models.dart';
import 'help_articles_screen.dart';
import 'help_search_layer.dart';
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
  final FocusNode _searchFocusNode = FocusNode();
  bool _loading = true;
  String? _error;
  List<HelpCategoryItem> _categories = const [];

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
      final browse =
          await _api.getCollectionBrowse(collectionSlug: widget.collectionSlug);
      if (!mounted) return;
      if (browse.displayMode == HelpBrowseDisplayMode.flat) {
        await Navigator.of(context).pushReplacement(
          MaterialPageRoute<void>(
            builder: (_) => HelpArticlesScreen(
              collectionSlug: widget.collectionSlug,
              collectionTitle: widget.collectionTitle,
              categorySlug: '__all__',
              categoryTitle: widget.collectionTitle,
              allArticlesInCollection: true,
              initialArticles: browse.articles,
            ),
          ),
        );
        return;
      }
      setState(() {
        _categories = browse.tagGroups;
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

  @override
  Widget build(BuildContext context) {
    return PageSimpleNavBarTopTitlePageContent(
      pageTitle: widget.collectionTitle,
      onBackTap: () => Navigator.of(context).pop(),
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
          collectionSlug: widget.collectionSlug,
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
    if (_categories.isEmpty) return const HelpEmptyResults();

    return ListCardModule(
      items: _categories
          .map(
            (c) => ListCardItem(
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
