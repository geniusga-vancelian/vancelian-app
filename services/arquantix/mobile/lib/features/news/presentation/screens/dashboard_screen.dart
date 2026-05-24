import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../design_system/design_system.dart';
import '../../data/blog_api.dart';
import '../../domain/models/article.dart';
import 'article_detail_screen.dart';

/// Dashboard : liste d’articles en cartes avec sliding horizontal (gauche → droite).
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final BlogApi _api = BlogApi();
  final PageController _pageController = PageController(
    viewportFraction: 0.88,
  );

  List<ArticlePreview> _items = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadFeed();
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  Future<void> _loadFeed() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final data = await _api.getFeed(pageSize: 20);
      final list = <ArticlePreview>[];
      if (data.featured != null) list.add(data.featured!);
      list.addAll(data.highlighted);
      list.addAll(data.articles);
      setState(() {
        _items = list;
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F5F5),
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 20, 24, 8),
              child: Text(
                'Read Later',
                style: AppTypography.displayMedium.copyWith(
                  color: const Color(0xFF1a1a1a),
                  letterSpacing: -0.5,
                ),
              ),
            ),
            Expanded(
              child: _loading && _items.isEmpty
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null && _items.isEmpty
                      ? _buildError()
                      : PageView.builder(
                          controller: _pageController,
                          scrollDirection: Axis.horizontal,
                          padEnds: true,
                          itemCount: _items.isEmpty ? 0 : _items.length,
                          itemBuilder: (context, index) {
                            return Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 12,
                              ),
                              child: _NewsCard(
                                article: _items[index],
                                onTap: () => _openArticle(_items[index]),
                              ),
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }

  /// Message d'erreur lisible (sans HTML brut, limité pour éviter overflow)
  String _errorMessage() {
    final e = _error ?? 'Erreur';
    if (e.contains('404')) {
      return 'API non disponible (404).\n\nVérifiez que le serveur Next.js du projet Arquantix tourne sur le port 3000 :\n  cd services/arquantix/web && npm run dev';
    }
    // Éviter d'afficher du HTML ou des réponses énormes
    final noHtml = e.replaceAll(RegExp(r'<[^>]*>'), ' ').replaceAll(RegExp(r'\s+'), ' ').trim();
    return noHtml.length > 300 ? '${noHtml.substring(0, 300)}…' : noHtml;
  }

  Widget _buildError() {
    return Center(
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 48, color: Colors.grey[600]),
              const SizedBox(height: 16),
              Text(
                _errorMessage(),
                style: AppTypography.paragraph.copyWith(fontSize: 14, color: Colors.grey[700]),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: _loadFeed,
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
      MaterialPageRoute<void>(
        builder: (context) => ArticleDetailScreen(slug: article.slug),
      ),
    );
  }
}

class _NewsCard extends StatelessWidget {
  final ArticlePreview article;
  final VoidCallback onTap;

  const _NewsCard({
    required this.article,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final dateStr = article.publishedAt != null
        ? DateFormat('MMMM d, yyyy', 'en_US').format(article.publishedAt!)
        : '';

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.06),
                blurRadius: 12,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'ARQUANTIX',
                        style: AppTypography.labelSmall.copyWith(
                          fontWeight: FontWeight.w600,
                          color: Colors.grey[600],
                          letterSpacing: 0.8,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        article.title,
                        style: AppTypography.paragraphLarge.copyWith(
                          fontWeight: FontWeight.w700,
                          color: const Color(0xFF1a1a1a),
                          height: 1.3,
                        ),
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 10),
                      Text(
                        dateStr,
                        style: AppTypography.paragraphSmall.copyWith(color: Colors.grey[500]),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 16),
                ClipRRect(
                  borderRadius: BorderRadius.circular(10),
                  child: SizedBox(
                    width: 100,
                    height: 100,
                    child: article.coverUrl.isNotEmpty
                        ? Image.network(
                            article.coverUrl,
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => Container(
                              color: Colors.grey[200],
                              child: Icon(
                                Icons.image_not_supported,
                                color: Colors.grey[400],
                              ),
                            ),
                          )
                        : Container(
                            color: Colors.grey[200],
                            child: Icon(
                              Icons.article_outlined,
                              color: Colors.grey[400],
                            ),
                          ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
