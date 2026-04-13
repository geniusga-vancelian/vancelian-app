import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/article_detail.dart';
import '../services/blog_api.dart';

class ArticleDetailScreen extends StatefulWidget {
  final String slug;

  const ArticleDetailScreen({super.key, required this.slug});

  @override
  State<ArticleDetailScreen> createState() => _ArticleDetailScreenState();
}

class _ArticleDetailScreenState extends State<ArticleDetailScreen> {
  final BlogApi _api = BlogApi();
  ArticleDetail? _article;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadArticle();
  }

  Future<void> _loadArticle() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final article = await _api.getArticle(widget.slug, locale: 'fr');
      setState(() {
        _article = article;
        _loading = false;
        _error = article == null ? 'Article non trouvé' : null;
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
      backgroundColor: Colors.white,
      body: SafeArea(
        child: _loading && _article == null
            ? const Center(child: CircularProgressIndicator())
            : _error != null && _article == null
                ? _buildError()
                : _article != null
                    ? CustomScrollView(
                        slivers: [
                          SliverAppBar(
                            pinned: true,
                            backgroundColor: Colors.white,
                            foregroundColor: Colors.grey[900],
                            elevation: 0,
                            leading: IconButton(
                              icon: const Icon(Icons.arrow_back),
                              onPressed: () => Navigator.of(context).pop(),
                            ),
                          ),
                          SliverToBoxAdapter(child: _buildArticleContent()),
                        ],
                      )
                    : const SizedBox.shrink(),
      ),
    );
  }

  Widget _buildError() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 48, color: Colors.grey[400]),
            const SizedBox(height: 16),
            Text(
              _error ?? 'Erreur',
              style: TextStyle(fontSize: 16, color: Colors.grey[600]),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: () => Navigator.of(context).pop(),
              icon: const Icon(Icons.arrow_back, size: 20),
              label: const Text('Retour'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildArticleContent() {
    final a = _article!;
    final publishedStr = a.publishedAt != null
        ? DateFormat('d MMMM yyyy', 'fr_FR').format(a.publishedAt!)
        : '';

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            publishedStr,
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey[500],
            ),
          ),
          if (a.categories.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: a.categories.map((c) {
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: const Color(0xFF4F46E5).withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    c.label,
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF4F46E5),
                    ),
                  ),
                );
              }).toList(),
            ),
          ],
          const SizedBox(height: 16),
          Text(
            a.title,
            style: TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.w700,
              color: Colors.grey[900],
              height: 1.2,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            a.standfirst,
            style: TextStyle(
              fontSize: 18,
              color: Colors.grey[600],
              fontStyle: FontStyle.italic,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              Text(
                a.authorName,
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  color: Colors.grey[800],
                ),
              ),
              if (a.authorRole != null) ...[
                Text(
                  ' • ${a.authorRole}',
                  style: TextStyle(
                    fontSize: 15,
                    color: Colors.grey[600],
                  ),
                ),
              ],
              Text(
                ' • ${a.readingTime} min',
                style: TextStyle(
                  fontSize: 15,
                  color: Colors.grey[500],
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          if (a.videoUrl != null && a.videoUrl!.isNotEmpty)
            _buildVideo(a.videoUrl!)
          else if (a.galleryUrls.isNotEmpty)
            _buildGallery(a.coverUrl, a.galleryUrls)
          else if (a.coverUrl.isNotEmpty)
            _buildCoverImage(a.coverUrl),
          if (a.coverTitle != null && a.coverTitle!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              a.coverTitle!,
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[500],
              ),
            ),
          ],
          if (a.coverCredit != null || a.coverSource != null) ...[
            const SizedBox(height: 4),
            Text(
              [a.coverCredit, a.coverSource].where((x) => x != null && x!.isNotEmpty).join(' / '),
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey[400],
              ),
            ),
          ],
          const SizedBox(height: 32),
          ...a.blocks.map((b) => _buildBlock(b)),
          if (a.documents.isNotEmpty) ...[
            const SizedBox(height: 32),
            const Divider(),
            const SizedBox(height: 24),
            Text(
              'Documents',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: Colors.grey[800],
              ),
            ),
            const SizedBox(height: 12),
            ...a.documents.map((d) => _buildDocument(d)),
          ],
          const SizedBox(height: 48),
        ],
      ),
    );
  }

  Widget _buildVideo(String url) {
    String? videoId;
    if (url.contains('youtube.com/watch?v=')) {
      videoId = url.split('v=')[1].split('&')[0];
    } else if (url.contains('youtu.be/')) {
      videoId = url.split('youtu.be/')[1].split('?')[0];
    } else if (url.contains('vimeo.com/')) {
      videoId = url.split('vimeo.com/')[1].split('?')[0];
    }

    if (videoId == null) {
      return const SizedBox.shrink();
    }

    final embedUrl = url.contains('vimeo')
        ? 'https://player.vimeo.com/video/$videoId'
        : 'https://www.youtube.com/embed/$videoId';

    return AspectRatio(
      aspectRatio: 16 / 9,
      child: Container(
        decoration: BoxDecoration(
          color: Colors.black,
          borderRadius: BorderRadius.circular(12),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: InkWell(
            onTap: () => launchUrl(Uri.parse(url)),
            child: Stack(
              alignment: Alignment.center,
              children: [
                Image.network(
                  url.contains('youtube')
                      ? 'https://img.youtube.com/vi/$videoId/maxresdefault.jpg'
                      : '',
                  fit: BoxFit.cover,
                  width: double.infinity,
                  height: double.infinity,
                  errorBuilder: (_, __, ___) => Container(
                    color: Colors.grey[900],
                    child: const Icon(Icons.play_circle_outline, size: 64, color: Colors.white),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.black.withValues(alpha: 0.5),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.play_arrow, size: 48, color: Colors.white),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildGallery(String coverUrl, List<String> galleryUrls) {
    final urls = [coverUrl, ...galleryUrls].where((u) => u.isNotEmpty).toList();
    if (urls.isEmpty) return const SizedBox.shrink();

    return SizedBox(
      height: 220,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: urls.length,
        itemBuilder: (context, i) {
          return Padding(
            padding: EdgeInsets.only(right: i < urls.length - 1 ? 12 : 0),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: SizedBox(
                width: 300,
                child: Image.network(
                  urls[i],
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Container(
                    color: Colors.grey[300],
                    child: Icon(Icons.image_not_supported, color: Colors.grey[500]),
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildCoverImage(String url) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: Image.network(
        url,
        width: double.infinity,
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) => Container(
          height: 200,
          color: Colors.grey[300],
          child: Icon(Icons.image_not_supported, color: Colors.grey[500]),
        ),
      ),
    );
  }

  Widget _buildBlock(ArticleBlock block) {
    switch (block.type) {
      case 'HEADING':
        return Padding(
          padding: const EdgeInsets.only(top: 24, bottom: 12),
          child: Text(
            block.data['text'] as String? ?? '',
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: Colors.grey[900],
            ),
          ),
        );
      case 'PARAGRAPH':
        return Padding(
          padding: const EdgeInsets.only(bottom: 16),
          child: Text(
            block.data['text'] as String? ?? '',
            style: TextStyle(
              fontSize: 17,
              height: 1.6,
              color: Colors.grey[800],
            ),
          ),
        );
      case 'QUOTE':
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 20),
          child: Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.grey[50],
              border: Border(
                left: BorderSide(color: const Color(0xFF4F46E5), width: 4),
              ),
              borderRadius: BorderRadius.circular(0),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  block.data['text'] as String? ?? '',
                  style: TextStyle(
                    fontSize: 18,
                    fontStyle: FontStyle.italic,
                    color: Colors.grey[700],
                    height: 1.5,
                  ),
                ),
                if (block.data['author'] != null && (block.data['author'] as String).isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(
                      '— ${block.data['author']}',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey[500],
                      ),
                    ),
                  ),
              ],
            ),
          ),
        );
      case 'BULLET_LIST':
        final items = block.data['items'] as List<dynamic>? ?? [];
        return Padding(
          padding: const EdgeInsets.only(bottom: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: items.map((item) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '• ',
                      style: TextStyle(
                        fontSize: 17,
                        color: const Color(0xFF4F46E5),
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Expanded(
                      child: Text(
                        item.toString(),
                        style: TextStyle(
                          fontSize: 17,
                          height: 1.5,
                          color: Colors.grey[800],
                        ),
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
        );
      case 'IMAGE':
        final imageUrl = block.imageUrl ?? block.data['url'] as String? ?? '';
        final caption = block.data['caption'] as String? ?? '';
        if (imageUrl.isEmpty) return const SizedBox.shrink();
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.network(
                  imageUrl,
                  width: double.infinity,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Container(
                    height: 200,
                    color: Colors.grey[300],
                    child: Icon(Icons.image_not_supported, color: Colors.grey[500]),
                  ),
                ),
              ),
              if (caption.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    caption,
                    style: TextStyle(
                      fontSize: 14,
                      fontStyle: FontStyle.italic,
                      color: Colors.grey[500],
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),
            ],
          ),
        );
      case 'VIDEO':
        final url = block.data['url'] as String? ?? '';
        if (url.isEmpty) return const SizedBox.shrink();
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 20),
          child: InkWell(
            onTap: () => launchUrl(Uri.parse(url)),
            child: Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: Colors.grey[100],
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  Icon(Icons.play_circle_filled, size: 48, color: const Color(0xFF4F46E5)),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Text(
                      'Vidéo : $url',
                      style: TextStyle(fontSize: 14, color: Colors.grey[700]),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      case 'DOCUMENT':
        final docUrl = block.data['url'] as String? ?? '';
        final title = block.data['title'] as String? ?? 'Document';
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: InkWell(
            onTap: docUrl.isNotEmpty ? () => launchUrl(Uri.parse(docUrl)) : null,
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                border: Border.all(color: Colors.grey[300]!),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: Colors.grey[200],
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Center(
                      child: Text(
                        'PDF',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          color: Colors.grey[600],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Text(
                      title,
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w500,
                        color: Colors.grey[800],
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Icon(Icons.open_in_new, size: 20, color: Colors.grey[500]),
                ],
              ),
            ),
          ),
        );
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _buildDocument(ArticleDocument doc) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: doc.url != null && doc.url!.isNotEmpty
            ? () => launchUrl(Uri.parse(doc.url!))
            : null,
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey[300]!),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: Colors.grey[200],
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Center(
                  child: Text(
                    'PDF',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      color: Colors.grey[600],
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Text(
                  doc.title,
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w500,
                    color: Colors.grey[800],
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Icon(Icons.open_in_new, size: 20, color: Colors.grey[500]),
            ],
          ),
        ),
      ),
    );
  }
}
