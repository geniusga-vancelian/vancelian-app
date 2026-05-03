import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../data/help_api.dart';
import '../../domain/models/help_center_models.dart';
import '../../../news/presentation/screens/article_detail_screen.dart';
import 'help_search_layer.dart';
import 'help_widgets.dart';

class HelpArticlesScreen extends StatefulWidget {
  const HelpArticlesScreen({
    super.key,
    required this.collectionSlug,
    required this.collectionTitle,
    required this.categorySlug,
    required this.categoryTitle,
    this.initialFilterTagLabel,
    this.allArticlesInCollection = false,
    this.initialArticles,
  });

  final String collectionSlug;
  final String collectionTitle;
  final String categorySlug;
  final String categoryTitle;
  final String? initialFilterTagLabel;
  /// Liste plate `/collections/:slug/articles` (sans étape tags).
  final bool allArticlesInCollection;
  /// Évite un second fetch après `browse` en mode flat.
  final List<HelpArticleItem>? initialArticles;

  @override
  State<HelpArticlesScreen> createState() => _HelpArticlesScreenState();
}

class _HelpArticlesScreenState extends State<HelpArticlesScreen> {
  final HelpApi _api = HelpApi();
  final TextEditingController _searchController = TextEditingController();
  final FocusNode _searchFocusNode = FocusNode();
  String _selectedTagKey = 'ALL';
  bool _loading = true;
  String? _error;
  List<HelpArticleItem> _articles = const [];
  String? _resolvedCategoryTitle;

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
      final HelpArticleListResponse response;
      if (widget.allArticlesInCollection) {
        if (widget.initialArticles != null) {
          if (!mounted) return;
          setState(() {
            _articles = widget.initialArticles!;
            _resolvedCategoryTitle = widget.collectionTitle;
            _loading = false;
            _syncTagSelectionAfterLoad();
          });
          return;
        }
        response = await _api.getAllArticlesInCollection(
          collectionSlug: widget.collectionSlug,
        );
      } else {
        response = await _api.getArticles(
          collectionSlug: widget.collectionSlug,
          categorySlug: widget.categorySlug,
        );
      }
      if (!mounted) return;
      setState(() {
        _articles = response.articles;
        _resolvedCategoryTitle = response.categoryTitle;

        _syncTagSelectionAfterLoad();

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

  void _syncTagSelectionAfterLoad() {
    final tagKeys = <String>{};
    for (final article in _articles) {
      for (final tag in article.targetTags) {
        tagKeys.add(tag.key);
      }
    }
    if (_selectedTagKey != 'ALL' && !tagKeys.contains(_selectedTagKey)) {
      _selectedTagKey = 'ALL';
    }

    final filterLabel = widget.initialFilterTagLabel?.trim();
    if (filterLabel != null &&
        filterLabel.isNotEmpty &&
        _selectedTagKey == 'ALL') {
      final filterLower = filterLabel.toLowerCase();
      for (final article in _articles) {
        for (final tag in article.targetTags) {
          if (tag.label.toLowerCase() == filterLower ||
              tag.slug.toLowerCase() == filterLower) {
            _selectedTagKey = tag.key;
            break;
          }
        }
        if (_selectedTagKey != 'ALL') break;
      }
    }
  }

  List<HelpArticleItem> get _filtered {
    return _articles.where((item) {
      if (_selectedTagKey != 'ALL' &&
          !item.targetTags.any((tag) => tag.key == _selectedTagKey)) {
        return false;
      }
      return true;
    }).toList();
  }

  List<HelpTargetTag> get _availableTags {
    final byKey = <String, HelpTargetTag>{};
    for (final article in _articles) {
      for (final tag in article.targetTags) {
        byKey.putIfAbsent(tag.key, () => tag);
      }
    }
    final tags = byKey.values.toList();
    tags.sort(
        (a, b) => a.label.toLowerCase().compareTo(b.label.toLowerCase()));
    return tags;
  }

  bool get _filterLocked =>
      widget.initialFilterTagLabel != null &&
      widget.initialFilterTagLabel!.trim().isNotEmpty;

  @override
  Widget build(BuildContext context) {
    return PageSimpleNavBarTopTitlePageContent(
      pageTitle: _resolvedCategoryTitle ?? widget.categoryTitle,
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
          categorySlug: widget.categorySlug,
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
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (_availableTags.isNotEmpty && !_filterLocked) ...[
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Row(
              children: [
                AppFilterChip(
                  label: 'Tous',
                  selected: _selectedTagKey == 'ALL',
                  onTap: () =>
                      setState(() => _selectedTagKey = 'ALL'),
                ),
                for (final tag in _availableTags)
                  AppFilterChip(
                    label: tag.label,
                    selected: _selectedTagKey == tag.key,
                    onTap: () =>
                        setState(() => _selectedTagKey = tag.key),
                  ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.md),
        ],
        if (_filtered.isEmpty)
          const HelpEmptyResults()
        else
          ListCardModule(
            items: _filtered
                .map(
                  (a) => ListCardItem(
                    title: a.question,
                    onTap: () {
                      final categorySlugForDetail = widget.allArticlesInCollection
                          ? (a.collectionTags.isNotEmpty
                              ? a.collectionTags.first
                              : 'general')
                          : widget.categorySlug;
                      Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => ArticleDetailScreen.help(
                            collectionSlug: widget.collectionSlug,
                            categorySlug: categorySlugForDetail,
                            articleSlug: a.slug,
                          ),
                        ),
                      );
                    },
                  ),
                )
                .toList(),
          ),
      ],
    );
  }
}
