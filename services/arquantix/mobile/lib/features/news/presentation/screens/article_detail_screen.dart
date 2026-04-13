import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../design_system/design_system.dart';
import '../../data/blog_api.dart';
import '../../domain/models/article_detail.dart';

class ArticleDetailScreen extends StatefulWidget {
  final String slug;

  const ArticleDetailScreen({super.key, required this.slug});

  @override
  State<ArticleDetailScreen> createState() => _ArticleDetailScreenState();
}

class _ArticleDetailScreenState extends State<ArticleDetailScreen> {
  final BlogApi _api = BlogApi();
  final ScrollController _scrollController = ScrollController();
  ArticleDetail? _article;
  bool _loading = true;
  String? _error;
  double _navTitleOpacity = 0;
  double _navBarBgOpacity = 0;

  static const Map<String, Color> _categoryColors = {
    'economie': Color(0xFFFF383C),
    'economy': Color(0xFFFF383C),
    'crypto': Color(0xFFFF8D28),
    'cryptocurrency': Color(0xFFFF8D28),
    'banque': Color(0xFF0088FF),
    'banking': Color(0xFF0088FF),
    'guerre': Color(0xFFAC7F5E),
    'war': Color(0xFFAC7F5E),
    'politique': Color(0xFF6155F5),
    'politics': Color(0xFF6155F5),
    'tech': Color(0xFF00DAC3),
    'technology': Color(0xFF00DAC3),
  };

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    _loadArticle();
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    final offset = _scrollController.hasClients ? _scrollController.offset : 0.0;
    final heroBottom = MediaQuery.of(context).size.width -
        kToolbarHeight -
        MediaQuery.of(context).padding.top;
    final fadeStart = heroBottom - 60;
    const fadeRange = 40.0;

    final progress = ((offset - fadeStart) / fadeRange).clamp(0.0, 1.0);

    if ((progress - _navTitleOpacity).abs() > 0.02 ||
        (progress - _navBarBgOpacity).abs() > 0.02) {
      setState(() {
        _navTitleOpacity = progress;
        _navBarBgOpacity = progress;
      });
    }
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
    if (_loading && _article == null) {
      return Scaffold(
        backgroundColor: AppColors.pageBackground,
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_error != null && _article == null) {
      return Scaffold(
        backgroundColor: AppColors.pageBackground,
        appBar: AppTopNavBar(
          leadingType: AppTopNavBarLeading.back,
          onBackTap: () => Navigator.of(context).pop(),
        ),
        body: _buildError(),
      );
    }

    final navFg = _navBarBgOpacity > 0.5 ? AppColors.textPrimary : AppColors.white;

    return ImmersiveHeroPageTemplate(
      scrollController: _scrollController,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.back,
        onBackTap: () => Navigator.of(context).pop(),
        title: _article?.title ?? 'Article',
        titleOpacity: _navTitleOpacity,
        centerTitle: true,
        titleMaxLines: 1,
        titleTextStyle: AppTypography.itemPrimary.copyWith(color: navFg),
        backgroundColor: Color.lerp(
          Colors.transparent,
          AppColors.pageBackground,
          _navBarBgOpacity,
        ),
        foregroundColor: navFg,
      ),
      hero: _buildHero(),
      belowHero: _buildBody(),
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
              style: AppTypography.paragraph.copyWith(color: Colors.grey[600]),
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

  Widget _buildHero() {
    final a = _article!;
    final editorial = a.articleType == 'ANALYSIS'
        ? 'Analysis'
        : a.isCompanyNews
            ? 'Company News'
            : 'Market News';
    final editorialBadge = ArticleCategoryBadgeData(
      label: editorial,
      dotColor: AppColors.accent,
    );
    final topicBadges = a.categories.map((cat) {
      final color = _categoryColors[cat.slug.toLowerCase()] ?? AppColors.gray;
      return ArticleCategoryBadgeData(label: cat.label, dotColor: color);
    }).toList();

    return ArticleHeroHeader(
      imageUrl: a.coverUrl,
      title: a.title,
      badges: [editorialBadge, ...topicBadges],
      showNavBar: false,
    );
  }

  static const double _hPad = AppSpacing.s4;

  Widget _padH(Widget child) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: _hPad),
        child: child,
      );

  Widget _buildBody() {
    final a = _article!;
    final dateStr = a.publishedAt != null
        ? DateFormat('d MMMM yyyy', 'fr_FR').format(a.publishedAt!)
        : '';

    final blocks = a.blocks;
    // Standfirst + **tous** les PARAGRAPH consécutifs en tête de liste (sans autre type entre
    // eux) dans une seule carte blanche. Dès que le 1er bloc n’est pas un paragraphe (heading,
    // image, etc.), rien n’est fusionné avec le chapô — tout part dans [_buildGroupedBlocks].
    final leadingParagraphCount = _countLeadingParagraphRun(blocks);
    final introParagraphBlocks = leadingParagraphCount > 0
        ? blocks.sublist(0, leadingParagraphCount)
        : const <ArticleBlock>[];
    final blocksAfterIntro =
        leadingParagraphCount > 0 ? blocks.sublist(leadingParagraphCount) : blocks;

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.s8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _padH(_buildIntroCard(
            a,
            dateStr,
            introParagraphBlocks: introParagraphBlocks,
          )),
          const SizedBox(height: AppSpacing.s8),

          ..._buildGroupedBlocks(blocksAfterIntro),

          if (a.videoUrl != null && a.videoUrl!.isNotEmpty) ...[
            _padH(ArticleVideoBlock(
              thumbnailUrl: a.coverUrl,
              onPlay: () => _launchUrl(a.videoUrl!),
            )),
            const SizedBox(height: AppSpacing.s8),
          ],

          if (a.galleryUrls.isNotEmpty) ...[
            ArticleGalleryBlock(
              imageUrls: a.galleryUrls,
              horizontalPadding: _hPad,
            ),
            const SizedBox(height: AppSpacing.s8),
          ],

          if (a.documents.isNotEmpty) ...[
            _padH(_buildResourcesSection(a.documents)),
            const SizedBox(height: AppSpacing.s8),
          ],

          _padH(ArticleAuthorRow(
            name: a.authorName,
            subtitle: [
              if (a.authorRole != null) a.authorRole!,
              if (dateStr.isNotEmpty) dateStr,
            ].join(' • '),
          )),
        ],
      ),
    );
  }

  /// Nombre de blocs PARAGRAPH consécutifs depuis l’index 0 (interrompu par tout autre type).
  int _countLeadingParagraphRun(List<ArticleBlock> blocks) {
    var n = 0;
    for (final b in blocks) {
      if (b.type != 'PARAGRAPH') break;
      n++;
    }
    return n;
  }

  Widget _buildIntroCard(
    ArticleDetail a,
    String dateStr, {
    List<ArticleBlock> introParagraphBlocks = const [],
  }) {
    final standfirst = a.standfirst.trim();
    final hasStandfirst = standfirst.isNotEmpty;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.s4),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (hasStandfirst) ...[
            Text(
              standfirst,
              style: AppTypography.bodyEmphasized.copyWith(
                color: AppColors.black,
                height: 1.45,
              ),
            ),
            const SizedBox(height: AppSpacing.s2),
            _buildReadingTimeRow(),
          ] else if (introParagraphBlocks.isNotEmpty) ...[
            _buildReadingTimeRow(),
          ],
          for (var i = 0; i < introParagraphBlocks.length; i++) ...[
            const SizedBox(height: AppSpacing.s4),
            _buildBlockContent(introParagraphBlocks[i]),
          ],
        ],
      ),
    );
  }

  Widget _buildReadingTimeRow() {
    return Row(
      children: [
        const Icon(Icons.schedule_rounded, size: 12, color: Color(0xFF6155F5)),
        const SizedBox(width: AppSpacing.s1),
        Text(
          'Reading time',
          style: AppTypography.bodySmRegular.copyWith(
            color: AppColors.gray,
          ),
        ),
      ],
    );
  }

  /// Ferme le bloc blanc courant : photo, carrousel, vidéo, document, citation.
  static const _cardBreakTypes = {
    'IMAGE',
    'GALLERY',
    'VIDEO',
    'DOCUMENT',
    'QUOTE',
  };

  static const _fullBleedTypes = {'GALLERY'};

  List<Widget> _buildGroupedBlocks(List<ArticleBlock> blocks) {
    final widgets = <Widget>[];
    final pendingTextWidgets = <Widget>[];

    void flushTextCard() {
      if (pendingTextWidgets.isEmpty) return;
      widgets.add(_padH(_wrapInCard(List.of(pendingTextWidgets))));
      widgets.add(const SizedBox(height: AppSpacing.s8));
      pendingTextWidgets.clear();
    }

    for (final block in blocks) {
      if (block.type == 'HEADING') {
        flushTextCard();
        final title = block.data['text'] as String? ?? '';
        if (title.trim().isNotEmpty) {
          widgets.add(_padH(AppSectionTitle(title.trim())));
          widgets.add(const SizedBox(height: AppSpacing.s4));
        }
        continue;
      }

      if (_cardBreakTypes.contains(block.type)) {
        flushTextCard();
        final w = _buildBlockContent(block);
        if (_fullBleedTypes.contains(block.type)) {
          widgets.add(w);
        } else {
          widgets.add(_padH(w));
        }
        widgets.add(const SizedBox(height: AppSpacing.s8));
        continue;
      }

      if (pendingTextWidgets.isNotEmpty) {
        pendingTextWidgets.add(const SizedBox(height: AppSpacing.s4));
      }
      pendingTextWidgets.add(_buildBlockContent(block));
    }

    flushTextCard();
    return widgets;
  }

  Widget _wrapInCard(List<Widget> children) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.s4),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: children,
      ),
    );
  }

  Widget _buildBlockContent(ArticleBlock block) {
    switch (block.type) {
      case 'HEADING':
        return Text(
          block.data['text'] as String? ?? '',
          style: AppTypography.bodyEmphasized.copyWith(
            color: AppColors.black,
          ),
        );

      case 'PARAGRAPH':
        return _buildParagraphBlock(block);

      case 'BULLET_LIST':
        final items = (block.data['items'] is List)
            ? (block.data['items'] as List)
                .map((e) => e.toString())
                .where((e) => e.trim().isNotEmpty)
                .toList()
            : const <String>[];
        if (items.isEmpty) return const SizedBox.shrink();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: items
              .map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.xs),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Padding(
                        padding: const EdgeInsets.only(top: 7, right: 8),
                        child: Container(
                          width: 5,
                          height: 5,
                          decoration: const BoxDecoration(
                            color: AppColors.black,
                            shape: BoxShape.circle,
                          ),
                        ),
                      ),
                      Expanded(
                        child: Text(
                          item,
                          style: AppTypography.bodyRegular.copyWith(
                            color: AppColors.black,
                            height: 1.45,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              )
              .toList(),
        );

      case 'QUOTE':
        return ArticleQuoteBlock(
          quote: block.data['text'] as String? ?? '',
          author: block.data['author'] as String?,
          asCard: block.data['asCard'] != false,
        );

      case 'IMAGE':
        final imageUrl = block.imageUrl ?? block.data['url'] as String? ?? '';
        if (imageUrl.isEmpty) return const SizedBox.shrink();
        return ArticleImageBlock(
          imageUrl: imageUrl,
          caption: block.data['caption'] as String? ??
              block.data['credit'] as String?,
          height: 193,
        );

      case 'VIDEO':
        final videoThumb = block.data['thumbnailUrl'] as String? ??
            block.data['coverUrl'] as String? ??
            '';
        final videoUrl = block.data['url'] as String? ?? '';
        return ArticleVideoBlock(
          thumbnailUrl: videoThumb,
          onPlay: videoUrl.isNotEmpty ? () => _launchUrl(videoUrl) : null,
        );

      case 'GALLERY':
        final urls = (block.data['urls'] as List<dynamic>?)
                ?.map((e) => e.toString())
                .toList() ??
            [];
        if (urls.isEmpty) return const SizedBox.shrink();
        return ArticleGalleryBlock(
          imageUrls: urls,
          horizontalPadding: _hPad,
        );

      case 'DOCUMENT':
        final docTitle = block.data['title'] as String? ?? 'Document';
        final docSubtitle = block.data['subtitle'] as String? ?? '';
        final docUrl = block.data['url'] as String? ?? '';
        return ArticleDocumentCard(
          title: docTitle,
          subtitle: docSubtitle,
          onTap: docUrl.isNotEmpty ? () => _launchUrl(docUrl) : null,
        );

      default:
        return const SizedBox.shrink();
    }
  }

  /// Paragraphe : atomes body (Regular / Emphasized / Italic / EmphasizedItalic).
  Widget _buildParagraphBlock(ArticleBlock block) {
    final raw = block.data['text'] as String? ?? '';
    if (raw.trim().isEmpty) return const SizedBox.shrink();
    final isBold = block.data['bold'] == true;
    final isItalic = block.data['italic'] == true;

    final TextStyle style;
    if (isBold && isItalic) {
      style = AppTypography.bodyEmphasizedItalic;
    } else if (isBold) {
      style = AppTypography.bodyEmphasized;
    } else if (isItalic) {
      style = AppTypography.bodyItalic;
    } else {
      style = AppTypography.bodyRegular;
    }

    return Text(
      raw,
      style: style.copyWith(color: AppColors.black, height: 1.45),
    );
  }

  Widget _buildResourcesSection(List<ArticleDocument> documents) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Ressources'),
        const SizedBox(height: AppSpacing.s2),
        ...documents.expand((doc) => [
              ArticleDocumentCard(
                title: doc.title,
                subtitle: 'PDF',
                onTap: doc.url != null ? () => _launchUrl(doc.url!) : null,
              ),
              const SizedBox(height: AppSpacing.s2),
            ]),
      ],
    );
  }

  Future<void> _launchUrl(String url) async {
    final uri = Uri.tryParse(url);
    if (uri != null && await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}
