import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../data/blog_api.dart';
import '../../domain/models/article.dart';
import 'article_detail_screen.dart';

/// Page Research : même structure que Blog (titre, filtre catégories, à la une, liste)
/// mais dédiée aux articles de type ANALYSIS.
class ResearchScreen extends StatefulWidget {
  const ResearchScreen({super.key, this.initialCategory});

  /// Catégorie pré-sélectionnée au chargement (ex. 'crypto' depuis Crypto Markets).
  final String? initialCategory;

  @override
  State<ResearchScreen> createState() => _ResearchScreenState();
}

class _ResearchScreenState extends State<ResearchScreen> {
  final BlogApi _api = BlogApi();
  BlogFeedResponse? _data;
  bool _loading = true;
  String? _error;
  late String? _selectedCategory;
  final ScrollController _scrollController = ScrollController();
  double _navTitleOpacity = 0;
  ArticlePreview? _featuredArticle;

  @override
  void initState() {
    super.initState();
    _selectedCategory = widget.initialCategory;
    _scrollController.addListener(_onScroll);
    _loadFeed();
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    final offset = _scrollController.hasClients ? _scrollController.offset : 0.0;
    final next = ((offset - 24) / 40).clamp(0.0, 1.0);
    if ((next - _navTitleOpacity).abs() > 0.02) {
      setState(() => _navTitleOpacity = next);
    }
  }

  Future<void> _loadFeed({int page = 1}) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await _api.getFeed(
        locale: 'fr',
        articleType: 'ANALYSIS',
        category: _selectedCategory,
        page: page,
        pageSize: 20,
      );
      setState(() {
        _data = data;
        _loading = false;
        _error = null;
        if (_selectedCategory == null && data.featured != null) {
          _featuredArticle = data.featured;
        }
      });
    } catch (e) {
      setState(() {
        _loading = false;
        _error = e.toString();
      });
    }
  }

  void _onCategorySelected(String? slug) {
    setState(() => _selectedCategory = slug);
    _loadFeed();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.back,
        title: 'Research',
        onBackTap: () => Navigator.of(context).pop(),
        centerTitle: false,
        titleOpacity: _navTitleOpacity,
        titleTextStyle: AppTypography.paragraph.copyWith(
          color: AppColors.textPrimary,
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () => _loadFeed(page: 1),
          child: CustomScrollView(
            controller: _scrollController,
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              const SliverToBoxAdapter(child: SizedBox(height: AppSpacing.md)),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
                  child: AppPageTitle('Research'),
                ),
              ),
              const SliverToBoxAdapter(child: SizedBox(height: AppSpacing.md)),
              if (_loading && _data == null)
                const SliverFillRemaining(
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (_error != null && _data == null)
                SliverFillRemaining(child: _buildError())
              else if (_data != null)
                ..._buildContent(),
            ],
          ),
        ),
      ),
    );
  }

  String? _tagForArticle(ArticlePreview a, List<BlogCategory> categories) {
    final slugs = a.categorySlugs;
    if (slugs == null || slugs.isEmpty) return null;
    for (final c in categories) {
      if (c.slug == slugs.first) return c.label;
    }
    return null;
  }

  List<Widget> _buildContent() {
    final list = <Widget>[];
    final data = _data!;

    if (_featuredArticle != null) {
      final featured = _featuredArticle!;
      list.add(
        SliverToBoxAdapter(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              BlogALaUne(
                title: 'A la une',
                items: [
                  BlogALaUneItem(
                    title: featured.title,
                    coverUrl: featured.coverUrl,
                    readingTime: featured.readingTime,
                    onTap: () => _openArticle(featured),
                    tag: _tagForArticle(featured, data.categories),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.xxl),
            ],
          ),
        ),
      );
    }

    list.add(
      SliverToBoxAdapter(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
          child: AppSectionTitle('All analyses'),
        ),
      ),
    );
    if (data.categories.isNotEmpty) {
      list.add(
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.only(top: AppSpacing.md, bottom: AppSpacing.lg),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  Padding(
                    padding: const EdgeInsets.only(left: AppSpacing.xl),
                    child: AppFilterChip(
                      label: 'Tous',
                      selected: _selectedCategory == null,
                      onTap: () => _onCategorySelected(null),
                    ),
                  ),
                  ...data.categories.asMap().entries.map(
                    (entry) {
                      final isLast = entry.key == data.categories.length - 1;
                      final c = entry.value;
                      return Padding(
                        padding: EdgeInsets.only(
                          left: AppSpacing.sm,
                          right: isLast ? AppSpacing.xl : 0,
                        ),
                        child: AppFilterChip(
                          label: c.label,
                          selected: _selectedCategory == c.slug,
                          onTap: () => _onCategorySelected(c.slug),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    final others = <ArticlePreview>[];
    if (_selectedCategory == null) others.addAll(data.highlighted);
    others.addAll(data.articles);

    for (final article in others) {
      list.add(
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl, vertical: AppSpacing.sm),
            child: NewsRowCard(
              title: article.title,
              coverUrl: article.coverUrl,
              readingTime: article.readingTime,
              onTap: () => _openArticle(article),
            ),
          ),
        ),
      );
    }

    list.add(const SliverToBoxAdapter(child: SizedBox(height: AppSpacing.xxl)));
    return list;
  }

  String _errorMessage() {
    final e = _error ?? 'Erreur';
    if (e.contains('404')) {
      return 'API non disponible (404).\n\nVérifiez que le serveur Next.js tourne sur le port 3000.';
    }
    final noHtml = e.replaceAll(RegExp(r'<[^>]*>'), ' ').replaceAll(RegExp(r'\s+'), ' ').trim();
    return noHtml.length > 300 ? '${noHtml.substring(0, 300)}…' : noHtml;
  }

  Widget _buildError() {
    return Center(
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 48, color: AppColors.textSecondary),
              const SizedBox(height: AppSpacing.lg),
              Text(
                _errorMessage(),
                style: AppTypography.meta.copyWith(color: AppColors.textPrimary),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: AppSpacing.xxl),
              FilledButton.icon(
                onPressed: _loadFeed,
                style: FilledButton.styleFrom(
                  backgroundColor: AppColors.accent,
                  foregroundColor: Colors.white,
                ),
                icon: const Icon(Icons.refresh, size: 20),
                label: const Text('Réessayer'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _openArticle(ArticlePreview article) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (context) => ArticleDetailScreen(slug: article.slug)),
    );
  }
}
