import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../data/help_api.dart';
import '../../domain/models/help_center_models.dart';
import 'help_article_detail_screen.dart';
import 'help_widgets.dart';

class HelpTaggedArticlesScreen extends StatefulWidget {
  const HelpTaggedArticlesScreen({
    super.key,
    required this.tagType,
    required this.tagId,
    required this.title,
  });

  final String tagType;
  final String tagId;
  final String title;

  @override
  State<HelpTaggedArticlesScreen> createState() =>
      _HelpTaggedArticlesScreenState();
}

class _HelpTaggedArticlesScreenState
    extends State<HelpTaggedArticlesScreen> {
  final HelpApi _api = HelpApi();
  final TextEditingController _searchController = TextEditingController();

  bool _loading = true;
  String? _error;
  List<HelpTaggedArticleItem> _articles = const [];

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
      final result = await _api.getArticlesByTag(
        tagType: widget.tagType,
        tagId: widget.tagId,
      );
      if (!mounted) return;
      setState(() {
        _articles = result;
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

  List<HelpTaggedArticleItem> get _filtered {
    final q = _searchController.text.trim().toLowerCase();
    if (q.isEmpty) return _articles;
    return _articles.where((item) {
      final base =
          '${item.question} ${item.standfirst ?? ''}'.toLowerCase();
      return base.contains(q);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return PageSimpleNavBarTopTitlePageContent(
      pageTitle: widget.title,
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
            (item) => HelpChevronCardItem(
              title: item.question,
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => HelpArticleDetailScreen(
                      collectionSlug: item.collectionSlug,
                      categorySlug: item.categorySlug,
                      articleSlug: item.slug,
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
