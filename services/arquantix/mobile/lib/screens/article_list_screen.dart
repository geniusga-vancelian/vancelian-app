import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/article.dart';
import '../services/blog_api.dart';
import '../features/news/presentation/screens/article_detail_screen.dart';

class ArticleListScreen extends StatefulWidget {
  const ArticleListScreen({super.key});

  @override
  State<ArticleListScreen> createState() => _ArticleListScreenState();
}

class _ArticleListScreenState extends State<ArticleListScreen> {
  final BlogApi _api = BlogApi();
  BlogFeedResponse? _data;
  bool _loading = true;
  String? _error;
  String? _selectedCategory;

  @override
  void initState() {
    super.initState();
    _loadFeed();
  }

  Future<void> _loadFeed({int page = 1}) async {
    if (page == 1) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }

    try {
      final data = await _api.getFeed(
        locale: 'fr',
        category: _selectedCategory,
        page: page,
      );

      setState(() {
        if (page == 1) {
          _data = data;
        } else if (_data != null) {
          _data = BlogFeedResponse(
            featured: _data!.featured,
            highlighted: _data!.highlighted,
            articles: [..._data!.articles, ...data.articles],
            categories: data.categories,
            pagination: data.pagination,
          );
        } else {
          _data = data;
        }
        _loading = false;
        _error = null;
      });
    } catch (e) {
      setState(() {
        _loading = false;
        _error = e.toString();
      });
    }
  }

  void _onCategorySelected(String? slug) {
    setState(() {
      _selectedCategory = slug;
    });
    _loadFeed();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 24, 20, 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Arquantix',
                      style: TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.w700,
                        color: Colors.grey[900],
                        letterSpacing: -0.5,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Actualités & Insights',
                      style: TextStyle(
                        fontSize: 16,
                        color: Colors.grey[600],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            if (_data?.categories.isNotEmpty == true)
              SliverToBoxAdapter(
                child: SizedBox(
                  height: 44,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    children: [
                      _CategoryChip(
                        label: 'Tous',
                        selected: _selectedCategory == null,
                        onTap: () => _onCategorySelected(null),
                      ),
                      ..._data!.categories.map(
                        (c) => _CategoryChip(
                          label: c.label,
                          selected: _selectedCategory == c.slug,
                          onTap: () => _onCategorySelected(c.slug),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            const SliverToBoxAdapter(child: SizedBox(height: 16)),
            if (_loading && _data == null)
              const SliverFillRemaining(
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              SliverFillRemaining(
                child: Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.error_outline, size: 48, color: Colors.grey[400]),
                        const SizedBox(height: 16),
                        Text(
                          'Impossible de charger les articles',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                            color: Colors.grey[800],
                          ),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _error!,
                          style: TextStyle(
                            fontSize: 14,
                            color: Colors.grey[600],
                          ),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 24),
                        FilledButton.icon(
                          onPressed: () => _loadFeed(),
                          icon: const Icon(Icons.refresh, size: 20),
                          label: const Text('Réessayer'),
                        ),
                      ],
                    ),
                  ),
                ),
              )
            else if (_data != null)
              ..._buildContent()
            else
              const SliverToBoxAdapter(child: SizedBox.shrink()),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildContent() {
    final list = <Widget>[];

    if (_data!.featured != null) {
      list.add(
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: _ArticleCard(
              article: _data!.featured!,
              featured: true,
              onTap: () => _openArticle(_data!.featured!),
            ),
          ),
        ),
      );
      list.add(const SliverToBoxAdapter(child: SizedBox(height: 24)));
    }

    if (_data!.highlighted.isNotEmpty) {
      list.add(
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Text(
              'À la une',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: Colors.grey[800],
              ),
            ),
          ),
        ),
      );
      list.add(const SliverToBoxAdapter(child: SizedBox(height: 12)));
      for (final a in _data!.highlighted) {
        list.add(
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
              child: _ArticleCard(
                article: a,
                featured: false,
                onTap: () => _openArticle(a),
              ),
            ),
          ),
        );
      }
      list.add(const SliverToBoxAdapter(child: SizedBox(height: 24)));
    }

    list.add(
      SliverToBoxAdapter(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Text(
            'Articles',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: Colors.grey[800],
            ),
          ),
        ),
      ),
    );
    list.add(const SliverToBoxAdapter(child: SizedBox(height: 12)));

    for (final a in _data!.articles) {
      list.add(
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
            child: _ArticleCard(
              article: a,
              featured: false,
              onTap: () => _openArticle(a),
            ),
          ),
        ),
      );
    }

    if (_data!.pagination.hasMore) {
      list.add(
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Center(
              child: _loading
                  ? const CircularProgressIndicator()
                  : TextButton(
                      onPressed: () => _loadFeed(page: _data!.pagination.page + 1),
                      child: const Text('Charger plus'),
                    ),
            ),
          ),
        ),
      );
    }

    list.add(const SliverToBoxAdapter(child: SizedBox(height: 32)));
    return list;
  }

  void _openArticle(ArticlePreview article) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => ArticleDetailScreen(slug: article.slug),
      ),
    );
  }
}

class _CategoryChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _CategoryChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: FilterChip(
        label: Text(label),
        selected: selected,
        onSelected: (_) => onTap(),
        selectedColor: const Color(0xFF4F46E5).withValues(alpha: 0.2),
        checkmarkColor: const Color(0xFF4F46E5),
      ),
    );
  }
}

class _ArticleCard extends StatelessWidget {
  final ArticlePreview article;
  final bool featured;
  final VoidCallback onTap;

  const _ArticleCard({
    required this.article,
    required this.featured,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final dateStr = article.publishedAt != null
        ? DateFormat('d MMM yyyy', 'fr_FR').format(article.publishedAt!)
        : '';

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          decoration: BoxDecoration(
            color: featured ? Colors.grey[50] : Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.grey[200]!),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (article.coverUrl.isNotEmpty)
                ClipRRect(
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(11)),
                  child: AspectRatio(
                    aspectRatio: featured ? 16 / 9 : 2,
                    child: Image.network(
                      article.coverUrl,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Container(
                        color: Colors.grey[300],
                        child: Icon(Icons.image_not_supported, color: Colors.grey[500]),
                      ),
                    ),
                  ),
                ),
              Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (dateStr.isNotEmpty)
                      Text(
                        dateStr,
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.grey[500],
                        ),
                      ),
                    if (dateStr.isNotEmpty) const SizedBox(height: 6),
                    Text(
                      article.title,
                      style: TextStyle(
                        fontSize: featured ? 20 : 16,
                        fontWeight: FontWeight.w600,
                        color: Colors.grey[900],
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      article.standfirst,
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey[600],
                        height: 1.4,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Text(
                          article.authorName,
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w500,
                            color: Colors.grey[700],
                          ),
                        ),
                        if (article.readingTime > 0) ...[
                          Text(
                            ' • ${article.readingTime} min',
                            style: TextStyle(
                              fontSize: 13,
                              color: Colors.grey[500],
                            ),
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
