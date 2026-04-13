import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../data/help_api.dart';
import '../../domain/models/help_center_models.dart';
import 'help_article_detail_screen.dart';
import 'help_widgets.dart';

class HelpArticlesScreen extends StatefulWidget {
  const HelpArticlesScreen({
    super.key,
    required this.collectionSlug,
    required this.collectionTitle,
    required this.categorySlug,
    required this.categoryTitle,
    this.initialFilterTagLabel,
  });

  final String collectionSlug;
  final String collectionTitle;
  final String categorySlug;
  final String categoryTitle;
  final String? initialFilterTagLabel;

  @override
  State<HelpArticlesScreen> createState() => _HelpArticlesScreenState();
}

class _HelpArticlesScreenState extends State<HelpArticlesScreen> {
  final HelpApi _api = HelpApi();
  final TextEditingController _searchController = TextEditingController();
  String _selectedTagKey = 'ALL';
  bool _loading = true;
  String? _error;
  List<HelpArticleItem> _articles = const [];
  String? _resolvedCategoryTitle;

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
      final response = await _api.getArticles(
        collectionSlug: widget.collectionSlug,
        categorySlug: widget.categorySlug,
      );
      if (!mounted) return;
      setState(() {
        _articles = response.articles;
        _resolvedCategoryTitle = response.categoryTitle;

        final tagKeys = <String>{};
        for (final article in response.articles) {
          for (final tag in article.targetTags) {
            tagKeys.add(tag.key);
          }
        }
        if (_selectedTagKey != 'ALL' &&
            !tagKeys.contains(_selectedTagKey)) {
          _selectedTagKey = 'ALL';
        }

        final filterLabel = widget.initialFilterTagLabel?.trim();
        if (filterLabel != null &&
            filterLabel.isNotEmpty &&
            _selectedTagKey == 'ALL') {
          final filterLower = filterLabel.toLowerCase();
          for (final article in response.articles) {
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

  List<HelpArticleItem> get _filtered {
    final q = _searchController.text.trim().toLowerCase();
    return _articles.where((item) {
      if (_selectedTagKey != 'ALL' &&
          !item.targetTags.any((tag) => tag.key == _selectedTagKey)) {
        return false;
      }
      if (q.isEmpty) return true;
      final base =
          '${item.question} ${item.standfirst ?? ''}'.toLowerCase();
      return base.contains(q);
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
        HelpChevronCardList(
          items: _filtered
              .map(
                (a) => HelpChevronCardItem(
                  title: a.question,
                  onTap: () {
                    Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => HelpArticleDetailScreen(
                          collectionSlug: widget.collectionSlug,
                          categorySlug: widget.categorySlug,
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
