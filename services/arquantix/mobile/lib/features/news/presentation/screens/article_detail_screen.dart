import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../core/article_paragraph_segments.dart';
import '../../../../design_system/design_system.dart';
import '../../../../l10n/app_localizations.dart';
import '../../../academy/data/academy_api.dart';
import '../../../academy/domain/models/academy_center_models.dart';
import '../../../help/data/help_api.dart';
import '../../../help/domain/models/help_center_models.dart';
import '../../data/blog_api.dart';
import '../../domain/models/article_detail.dart';
import '../markdown/article_paragraph_markdown.dart';

/// Origine du contenu affiché par [ArticleDetailScreen] — un seul gabarit UI ;
/// les données sont chargées et normalisées vers [ArticleDetail].
enum ArticleDetailSource {
  news,
  help,
  academy,
}

class ArticleDetailScreen extends StatefulWidget {
  final ArticleDetailSource source;
  final String? slug;
  final String? collectionSlug;
  final String? categorySlug;
  final String? articleSlug;

  /// Article blog / News (`slug` CMS).
  const ArticleDetailScreen({super.key, required String slug})
      : source = ArticleDetailSource.news,
        slug = slug,
        collectionSlug = null,
        categorySlug = null,
        articleSlug = null;

  /// FAQ — même gabarit que News après normalisation du payload.
  const ArticleDetailScreen.help({
    super.key,
    required String collectionSlug,
    required String categorySlug,
    required String articleSlug,
  })  : source = ArticleDetailSource.help,
        slug = null,
        collectionSlug = collectionSlug,
        categorySlug = categorySlug,
        articleSlug = articleSlug;

  /// Academy — même gabarit que Help / News.
  const ArticleDetailScreen.academy({
    super.key,
    required String collectionSlug,
    required String categorySlug,
    required String articleSlug,
  })  : source = ArticleDetailSource.academy,
        slug = null,
        collectionSlug = collectionSlug,
        categorySlug = categorySlug,
        articleSlug = articleSlug;

  @override
  State<ArticleDetailScreen> createState() => _ArticleDetailScreenState();
}

class _ArticleDetailScreenState extends State<ArticleDetailScreen> {
  final BlogApi _blogApi = BlogApi();
  final HelpApi _helpApi = HelpApi();
  final AcademyApi _academyApi = AcademyApi();
  final ScrollController _scrollController = ScrollController();
  ArticleDetail? _article;
  bool _loading = true;
  String? _error;
  double _navTitleOpacity = 0;
  double _navBarBgOpacity = 0;
  /// Markdown brut Help/Academy si aucun bloc structuré (fallback carte).
  String _markdownFallback = '';
  final GlobalKey _heroKey = GlobalKey();
  double? _measuredHeroHeight;

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

  void _reportHeroHeightAfterLayout() {
    if (!mounted) return;
    final ctx = _heroKey.currentContext;
    if (ctx == null) return;
    final box = ctx.findRenderObject() as RenderBox?;
    if (box == null || !box.hasSize) return;
    final h = box.size.height;
    if (_measuredHeroHeight != null &&
        (h - _measuredHeroHeight!).abs() < 0.5) {
      return;
    }
    setState(() => _measuredHeroHeight = h);
  }

  /// Hauteur hero avant 1ʳᵉ mesure réelle ([_heroKey]) — fade nav bar.
  double _estimatedHeroHeight(BuildContext context) {
    final screenH = MediaQuery.sizeOf(context).height;
    final cover = (_article?.coverUrl ?? '').trim();
    if (cover.isEmpty) {
      // Hero compact sous AppBar : hauteur ≈ contenu (badges + titre), pas de
      // réplication status + toolbar dans ce bloc — valeur de garde modeste.
      return 130;
    }
    return screenH *
            ArticleHeroHeader.kArticleBackgroundHeightScreenFraction -
        16;
  }

  void _onScroll() {
    final offset = _scrollController.hasClients ? _scrollController.offset : 0.0;
    final topInset = MediaQuery.paddingOf(context).top;
    final heroHeight =
        _measuredHeroHeight ?? _estimatedHeroHeight(context);
    final hasCover = (_article?.coverUrl ?? '').trim().isNotEmpty;
    // Mode immersif : le hero est sous la status bar ; la zone « titre » pour
    // le fade est décalée. Sans cover : le hero commence sous la AppBar —
    // utiliser la hauteur mesurée telle quelle.
    final heroBottom = hasCover
        ? heroHeight - kToolbarHeight - topInset
        : heroHeight;
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
      _markdownFallback = '';
    });
    try {
      switch (widget.source) {
        case ArticleDetailSource.news:
          final article =
              await _blogApi.getArticle(widget.slug!, locale: 'fr');
          if (!mounted) return;
          setState(() {
            _article = article;
            _loading = false;
            _error = article == null ? 'Article non trouvé' : null;
            _measuredHeroHeight = null;
          });
        case ArticleDetailSource.help:
          final detail = await _helpApi.getArticleDetail(
            collectionSlug: widget.collectionSlug!,
            categorySlug: widget.categorySlug!,
            articleSlug: widget.articleSlug!,
          );
          if (!mounted) return;
          setState(() {
            _article = _mapHelpToArticleDetail(detail);
            _markdownFallback = detail.markdownContent;
            _loading = false;
            _error = null;
            _measuredHeroHeight = null;
          });
        case ArticleDetailSource.academy:
          final detail = await _academyApi.getArticleDetail(
            collectionSlug: widget.collectionSlug!,
            categorySlug: widget.categorySlug!,
            articleSlug: widget.articleSlug!,
          );
          if (!mounted) return;
          setState(() {
            _article = _mapAcademyToArticleDetail(detail);
            _markdownFallback = detail.markdownContent;
            _loading = false;
            _error = null;
            _measuredHeroHeight = null;
          });
      }
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

    // Sans image de fond : hero « light » (texte sombre sur pageBackground) et
    // corps qui commence sous la AppBar — hauteur du hero ≈ contenu uniquement.
    // Avec cover : scroll sous la barre + hero immersif inchangé.
    final hasCover = (_article?.coverUrl ?? '').trim().isNotEmpty;
    final hasNoCover = !hasCover;

    // Quand l'article n'a pas de cover image, le hero passe en mode compact
    // (`compactWhenNoCover` du DS `ArticleHeroHeader`) avec un fond clair
    // (`pageBackground`) — un back-button blanc serait invisible. On force
    // donc la couleur sombre pour la nav bar dès le haut de page.
    final navFg = hasNoCover
        ? AppColors.textPrimary
        : (_navBarBgOpacity > 0.5 ? AppColors.textPrimary : AppColors.white);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _reportHeroHeightAfterLayout();
    });

    return ImmersiveHeroPageTemplate(
      scrollController: _scrollController,
      onRefresh: _loadArticle,
      extendBodyBehindAppBar: hasCover,
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
    final cover = a.coverUrl.trim();
    final hasCover = cover.isNotEmpty;
    final badges = widget.source == ArticleDetailSource.news
        ? _newsHeroBadges(a)
        : _centreHeroBadges(a);

    return ArticleHeroHeader(
      key: _heroKey,
      imageUrl: cover,
      title: a.title,
      badges: badges,
      showNavBar: false,
      compactWhenNoCover: true,
      compactBodyExtendsBehindAppBar: hasCover,
      heroFallbackColor: AppColors.pageBackground,
      compactTextColor: AppColors.textPrimary,
    );
  }

  List<ArticleCategoryBadgeData> _newsHeroBadges(ArticleDetail a) {
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
    return [editorialBadge, ...topicBadges];
  }

  List<ArticleCategoryBadgeData> _centreHeroBadges(ArticleDetail a) {
    if (a.categories.isEmpty) return [];
    final label = a.categories.first.label.trim();
    if (label.isEmpty) return [];
    return [
      ArticleCategoryBadgeData(label: label, dotColor: AppColors.gray),
    ];
  }

  /// Méta sous le standfirst dans la **carte intro blanche** (light mode) :
  /// « Par <auteur> · <rôle> » + icône clock + « X min de lecture ». Mappe
  /// `ArticleDetail.authorName`, `authorRole` et `readingTime` (déjà calculés
  /// côté API web). L10n : `articleAuthorByPrefix` / `articleReadingTimeMinutes`.
  /// Aligne le mobile sur le module CMS web `blog_article_reader`.
  ///
  /// Choix UI : nom de l'auteur en noir / poids fort, le reste (préfixe, rôle,
  /// séparateurs, durée) en gris — cohérent avec la version web.
  Widget _buildIntroMetaRow(ArticleDetail a) {
    final l10n = AppLocalizations.of(context)!;
    final hasAuthor = a.authorName.trim().isNotEmpty;
    final hasRole = a.authorRole != null && a.authorRole!.trim().isNotEmpty;
    final hasReadingTime = a.readingTime > 0;

    if (!hasAuthor && !hasReadingTime) return const SizedBox.shrink();

    final mutedStyle = AppTypography.bodySmRegular.copyWith(
      color: AppColors.gray,
    );
    final emphasizedStyle = AppTypography.bodySmRegular.copyWith(
      color: AppColors.black,
      fontWeight: FontWeight.w600,
    );
    const iconColor = Color(0xFF6155F5);

    final inlineSpans = <InlineSpan>[];
    if (hasAuthor) {
      inlineSpans.add(TextSpan(
        text: '${l10n.articleAuthorByPrefix} ',
        style: mutedStyle,
      ));
      inlineSpans.add(TextSpan(
        text: a.authorName,
        style: emphasizedStyle,
      ));
      if (hasRole) {
        inlineSpans.add(TextSpan(
          text: ' · ${a.authorRole!}',
          style: mutedStyle,
        ));
      }
    }

    final widgets = <Widget>[];
    if (inlineSpans.isNotEmpty) {
      widgets.add(Flexible(
        child: RichText(
          text: TextSpan(children: inlineSpans),
          overflow: TextOverflow.ellipsis,
          maxLines: 2,
        ),
      ));
    }
    if (hasAuthor && hasReadingTime) {
      widgets.add(Padding(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.s2),
        child: Text('·', style: mutedStyle),
      ));
    }
    if (hasReadingTime) {
      widgets.add(const Icon(Icons.schedule_rounded, size: 12, color: iconColor));
      widgets.add(const SizedBox(width: AppSpacing.s1));
      widgets.add(Text(
        l10n.articleReadingTimeMinutes(a.readingTime),
        style: mutedStyle,
      ));
    }

    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: widgets,
    );
  }

  static const double _hPad = AppSpacing.s4;

  Widget _padH(Widget child) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: _hPad),
        child: child,
      );

  bool _shouldShowIntroCard(
    ArticleDetail a,
    List<ArticleBlock> introParagraphBlocks,
  ) {
    final standfirst = a.standfirst.trim();
    final hasStandfirst = standfirst.isNotEmpty;
    final metaRow = _buildIntroMetaRow(a);
    final hasMetaRow = metaRow is! SizedBox;
    return hasStandfirst || hasMetaRow || introParagraphBlocks.isNotEmpty;
  }

  Widget _buildBody() {
    final a = _article!;
    // Les méta auteur + reading time sont rendues dans la carte intro blanche
    // (cf. `_buildIntroMetaRow`, sous le standfirst). L'ancienne
    // `ArticleAuthorRow` de pied de page est supprimée pour éviter le doublon.

    final blocks = a.blocks;
    // Standfirst + **tous** les PARAGRAPH consécutifs en tête sont traités dans
    // [_buildIntroWhiteModuleWidgets] (titres ATX + `---` comme pour le corps).
    final leadingParagraphCount = _countLeadingParagraphRun(blocks);
    final introParagraphBlocks = leadingParagraphCount > 0
        ? blocks.sublist(0, leadingParagraphCount)
        : const <ArticleBlock>[];
    final blocksAfterIntro =
        leadingParagraphCount > 0 ? blocks.sublist(leadingParagraphCount) : blocks;

    final showIntro = _shouldShowIntroCard(a, introParagraphBlocks);

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.s8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Intro : un ou plusieurs modules blancs si `---` dans le markdown ;
          // titres ATX → [AppSectionTitle] / [AppSectionTitle2].
          if (showIntro)
            ..._buildIntroWhiteModuleWidgets(a, introParagraphBlocks),

          ..._buildGroupedBlocks(blocksAfterIntro),

          if (a.blocks.isEmpty && _markdownFallback.trim().isNotEmpty)
            ..._buildMarkdownFallbackModules(_markdownFallback),

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

  /// Chapô / méta + paragraphes d’ouverture : un ou plusieurs modules blancs
  /// si le markdown contient `---` ; lignes `#`…`######` → [AppSectionTitle] /
  /// [AppSectionTitle2].
  List<Widget> _buildIntroWhiteModuleWidgets(
    ArticleDetail a,
    List<ArticleBlock> introParagraphBlocks,
  ) {
    final standfirst = a.standfirst.trim();
    final hasStandfirst = standfirst.isNotEmpty;
    final metaRow = _buildIntroMetaRow(a);
    final hasMetaRow = metaRow is! SizedBox;

    List<Widget> headerChunks() {
      if (!hasStandfirst && !hasMetaRow) return [];
      return [
        if (hasStandfirst) ...[
          Text(
            standfirst,
            style: AppTypography.bodyEmphasized.copyWith(
              color: AppColors.black,
              height: 1.45,
            ),
          ),
          if (hasMetaRow) ...[
            const SizedBox(height: AppSpacing.s2),
            metaRow,
          ],
        ] else if (hasMetaRow) ...[
          metaRow,
        ],
      ];
    }

    final out = <Widget>[];
    final pending = <Widget>[];
    var mergeHeaderIntoNextCard = headerChunks().isNotEmpty;

    void appendBody(Widget w) {
      if (pending.isNotEmpty) {
        pending.add(const SizedBox(height: AppSpacing.s4));
      }
      pending.add(w);
    }

    void flushIntroWhiteCard() {
      final header = headerChunks();
      final children = <Widget>[
        if (mergeHeaderIntoNextCard && header.isNotEmpty) ...header,
        if (mergeHeaderIntoNextCard &&
            header.isNotEmpty &&
            pending.isNotEmpty)
          const SizedBox(height: AppSpacing.s4),
        ...pending,
      ];
      mergeHeaderIntoNextCard = false;
      if (children.isEmpty) return;
      out.add(_padH(_wrapInCard(children)));
      out.add(const SizedBox(height: AppSpacing.s8));
      pending.clear();
    }

    if (introParagraphBlocks.isEmpty) {
      if (headerChunks().isEmpty) return [];
      flushIntroWhiteCard();
      return out;
    }

    for (final block in introParagraphBlocks) {
      final raw = (block.data['text'] ?? '').toString();
      if (raw.trim().isEmpty) continue;
      final baseStyle = _paragraphBaseStyle(block);
      for (final seg in splitParagraphMarkdown(raw)) {
        switch (seg) {
          case ParagraphDividerSegment():
            flushIntroWhiteCard();
          case ParagraphHeadingSegment(
              text: final headingText,
              level: final headingLevel,
            ):
            final clean = headingText.trim();
            if (clean.isEmpty) break;
            appendBody(
              headingLevel == 1
                  ? AppSectionTitle(clean)
                  : AppSectionTitle2(clean),
            );
          case ParagraphTextSegment(text: final paragraphText):
            appendBody(
              _paragraphMarkdownWidget(paragraphText, baseStyle),
            );
        }
      }
    }

    flushIntroWhiteCard();
    return out;
  }

  /// Ferme le bloc blanc courant : photo, carrousel, vidéo, document, citation,
  /// itinéraire (Steps), liste de documents (Documents list), carrousel d'images,
  /// parcours étape par étape (HowItWorksCarousel).
  ///
  /// `HOW_IT_WORKS_CAROUSEL` est listé ici **et** dans `_fullBleedTypes` :
  /// le widget DS [HowItWorksCarousel] est conçu full width (les cartes vont
  /// jusqu'aux bords de l'écran), il gère lui-même la marge horizontale de son
  /// titre + barre de bullets via `kModuleHorizontalMargin`. Sans ce double
  /// listing, le bloc serait enveloppé dans `_wrapInCard` (carte blanche
  /// redondante) et `_padH` ajouterait une marge latérale qui tronquerait
  /// les cartes par rapport au design DS.
  static const _cardBreakTypes = {
    'IMAGE',
    'GALLERY',
    'VIDEO',
    'DOCUMENT',
    'QUOTE',
    'STEPS_MODULE',
    'DOCUMENTS_LIST',
    'MEDIA_IMAGE_CAROUSEL',
    'HOW_IT_WORKS_CAROUSEL',
  };

  static const _fullBleedTypes = {'GALLERY', 'HOW_IT_WORKS_CAROUSEL'};

  List<Widget> _buildGroupedBlocks(List<ArticleBlock> blocks) {
    final widgets = <Widget>[];
    final pendingTextWidgets = <Widget>[];

    void flushTextCard() {
      if (pendingTextWidgets.isEmpty) return;
      widgets.add(_padH(_wrapInCard(List.of(pendingTextWidgets))));
      widgets.add(const SizedBox(height: AppSpacing.s8));
      pendingTextWidgets.clear();
    }

    // Bloc CMS `HEADING` natif : hors module blanc (comme avant).
    void emitHeading(String title, {int level = 2}) {
      flushTextCard();
      final clean = title.trim();
      if (clean.isEmpty) return;
      final Widget headingWidget = level == 1
          ? Text(
              clean,
              style: AppTypography.welcomeTitle.copyWith(
                color: AppColors.black,
              ),
            )
          : AppSectionTitle(clean);
      widgets.add(_padH(headingWidget));
      widgets.add(const SizedBox(height: AppSpacing.s4));
    }

    void appendInCardText(Widget w) {
      if (pendingTextWidgets.isNotEmpty) {
        pendingTextWidgets.add(const SizedBox(height: AppSpacing.s4));
      }
      pendingTextWidgets.add(w);
    }

    for (final block in blocks) {
      if (block.type == 'HEADING') {
        emitHeading(block.data['text'] as String? ?? '');
        continue;
      }

      // PARAGRAPH : [splitParagraphMarkdown] — `---` ferme et rouvre un module
      // blanc ; lignes ATX `#`…`######` → [AppSectionTitle] / [AppSectionTitle2].
      if (block.type == 'PARAGRAPH') {
        final raw = (block.data['text'] ?? '').toString();
        if (raw.trim().isEmpty) continue;
        final baseStyle = _paragraphBaseStyle(block);
        for (final seg in splitParagraphMarkdown(raw)) {
          switch (seg) {
            case ParagraphDividerSegment():
              flushTextCard();
            case ParagraphHeadingSegment(
                text: final headingText,
                level: final headingLevel,
              ):
              final clean = headingText.trim();
              if (clean.isEmpty) break;
              appendInCardText(
                headingLevel == 1
                    ? AppSectionTitle(clean)
                    : AppSectionTitle2(clean),
              );
            case ParagraphTextSegment(text: final paragraphText):
              appendInCardText(
                _paragraphMarkdownWidget(paragraphText, baseStyle),
              );
          }
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

      appendInCardText(_buildBlockContent(block));
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
        return _buildBulletListBlock(block);

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

      case 'STEPS_MODULE':
        return _buildStepsModuleBlock(block);

      case 'DOCUMENTS_LIST':
        return _buildDocumentsListBlock(block);

      case 'MEDIA_IMAGE_CAROUSEL':
        return _buildMediaImageCarouselBlock(block);

      case 'HOW_IT_WORKS_CAROUSEL':
        return _buildHowItWorksCarouselBlock(block);

      default:
        return const SizedBox.shrink();
    }
  }

  /// Bloc article `HOW_IT_WORKS_CAROUSEL` (cf. `articleBlockDataSchemas.ts`,
  /// calque section CMS `how_it_works`).
  ///
  /// `data` = `{ label?, title?, subtitle?, hideStepNumbering?, steps[] :
  /// { number, title, description?, imageMediaId?, imageMediaUrl?,
  /// stepButtonLabel?, stepButtonHref? }, primaryCta…, secondaryCta…,
  /// surface? }`. Les URLs `steps[].imageMediaUrl` sont enrichies côté serveur
  /// par `enrichPublicArticleBlockData` (résolution depuis `imageMediaId`).
  ///
  /// Mapping vers le widget DS [HowItWorksCarousel] :
  /// - `data.title`             → titre du module ([HowItWorksCarousel.title])
  ///   avec fallback sur `data.label` si vide (côté admin, le surtitre
  ///   « HOW IT WORKS » est souvent l'unique identifiant du module).
  /// - `data.steps[].number`           → [HowItWorksCarouselItem.stepLabel]
  /// - `data.steps[].title`            → [HowItWorksCarouselItem.title]
  /// - `data.steps[].imageMediaUrl`    → [HowItWorksCarouselItem.imageUrl]
  /// - `data.steps[].stepButtonLabel`  → [HowItWorksCarouselItem.ctaLabel]
  /// - `data.steps[].stepButtonHref`   → ouverture externe via `_launchUrl`
  ///   au tap CTA ([HowItWorksCarouselItem.onCtaTap]).
  ///
  /// Champs **non utilisés** côté mobile (rendus uniquement côté web par
  /// `SectionHowItWorksCms`) : `subtitle`, `description` par step,
  /// `hideStepNumbering`, `primaryCta…`, `secondaryCta…`, `surface`.
  Widget _buildHowItWorksCarouselBlock(ArticleBlock block) {
    final data = block.data;
    final label = (data['label'] as String?)?.trim() ?? '';
    final title = (data['title'] as String?)?.trim() ?? '';
    final rawSteps = data['steps'];
    final stepsList = rawSteps is List ? rawSteps : const <dynamic>[];

    final items = <HowItWorksCarouselItem>[];
    for (final raw in stepsList) {
      if (raw is! Map) continue;
      final step = Map<String, dynamic>.from(raw);
      final stepLabel = (step['number'] as String?)?.trim() ?? '';
      final stepTitle = (step['title'] as String?)?.trim() ?? '';
      // Une étape sans titre ni numéro n'a rien à afficher dans la carte
      // mobile (différent du web qui peut afficher la description seule).
      if (stepLabel.isEmpty && stepTitle.isEmpty) continue;
      final imageUrl = (step['imageMediaUrl'] as String?)?.trim() ?? '';
      final ctaLabel = (step['stepButtonLabel'] as String?)?.trim() ?? '';
      final ctaHref = (step['stepButtonHref'] as String?)?.trim() ?? '';
      items.add(
        HowItWorksCarouselItem(
          stepLabel: stepLabel,
          title: stepTitle,
          imageUrl: imageUrl.isNotEmpty ? imageUrl : null,
          ctaLabel: ctaLabel.isNotEmpty && ctaHref.isNotEmpty ? ctaLabel : null,
          onCtaTap: ctaLabel.isNotEmpty && ctaHref.isNotEmpty
              ? () => _launchUrl(ctaHref)
              : null,
        ),
      );
    }

    if (items.isEmpty) return const SizedBox.shrink();

    final moduleTitle = title.isNotEmpty ? title : label;

    return HowItWorksCarousel(
      title: moduleTitle,
      items: items,
    );
  }

  /// Bloc article `STEPS_MODULE` (cf. `articleBlockDataSchemas.ts`) :
  /// `data` = `{ title?, subtitle?, description?, rightLabel?, items: [...] }`.
  /// Rendu via [StepsModuleWidget] (DS « timeline » de la page Design system).
  ///
  /// Mapping (avril 2026 — formalisme aligné sur `HEADING` pour éviter le
  /// rendu « landing centré » qui détonnait dans le flux d'article) :
  /// - `data.subtitle`    → **non rendu** (eyebrow supprimé côté mobile).
  /// - `data.title`       → titre de bloc (`AppTypography.bodyEmphasized`,
  ///                        noir, **aligné à gauche**, identique à `HEADING`).
  /// - `data.description` → paragraphe d'intro aligné à gauche.
  /// - `data.rightLabel`  → libellé secondaire aligné à gauche, sous le header.
  /// - `data.items[]`     → [StepItem] (`dayLabel`, `date`, `title`,
  ///                        `description`, `isCompleted` mappés 1:1).
  Widget _buildStepsModuleBlock(ArticleBlock block) {
    final data = block.data;
    final title = (data['title'] as String?)?.trim() ?? '';
    final description = (data['description'] as String?)?.trim() ?? '';
    final rightLabel = (data['rightLabel'] as String?)?.trim() ?? '';
    final items = StepItem.listFromJson(data['items']);

    if (items.isEmpty) return const SizedBox.shrink();

    final hasHeader = title.isNotEmpty || description.isNotEmpty;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (title.isNotEmpty) ...[
          Text(
            title,
            style: AppTypography.bodyEmphasized.copyWith(
              color: AppColors.black,
            ),
          ),
        ],
        if (description.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.s2),
          Text(
            description,
            style: AppTypography.bodyRegular.copyWith(
              color: AppColors.textSecondary,
              height: 1.45,
            ),
          ),
        ],
        if (rightLabel.isNotEmpty) ...[
          SizedBox(height: hasHeader ? AppSpacing.s2 : 0),
          Text(
            rightLabel,
            style: AppTypography.bodySmRegular.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
        if (hasHeader || rightLabel.isNotEmpty) const SizedBox(height: AppSpacing.s4),
        StepsModuleWidget(
          title: title.isNotEmpty ? title : 'Steps',
          rightLabel: rightLabel.isNotEmpty ? rightLabel : null,
          steps: items,
          horizontalMargin: 0,
        ),
      ],
    );
  }

  /// Bloc article `DOCUMENTS_LIST` (cf. `enrichPublicArticleBlockData.ts`) :
  /// `data` = `{ subtitle?, moduleTitle?, description?, documentItems: [...] }`
  /// avec chaque item enrichi côté API : `mediaId`, `downloadUrl`, `displayName`,
  /// `dateLabel`, `sizeBytes`, `sizeLabel`, `mimeType`, `formatLabel`.
  ///
  /// Rendu via [ArticleDocumentCard] (DS, identique à la page Design system) :
  /// - `displayName` → `title`
  /// - `formatLabel` + `sizeLabel` → `subtitle` (ex. « PDF · 3,4 Mo »),
  ///   fallback : `formatLabel` seul, puis `dateLabel`, puis `'Document'`.
  /// - `downloadUrl` → ouverture externe (`url_launcher`) au tap.
  /// - icône fichier ajustée selon `mimeType` / `formatLabel`.
  Widget _buildDocumentsListBlock(ArticleBlock block) {
    final data = block.data;
    final moduleTitle = (data['moduleTitle'] as String?)?.trim() ?? '';
    final description = (data['description'] as String?)?.trim() ?? '';
    final rawItems = data['documentItems'];
    if (rawItems is! List || rawItems.isEmpty) return const SizedBox.shrink();

    final items = rawItems
        .whereType<Map>()
        .map((m) => Map<String, dynamic>.from(m))
        .where((m) {
          final url = (m['downloadUrl'] as String?)?.trim() ?? '';
          return url.isNotEmpty;
        })
        .toList();
    if (items.isEmpty) return const SizedBox.shrink();

    final hasHeader = moduleTitle.isNotEmpty || description.isNotEmpty;

    // Header aligné sur le formalisme `HEADING` (avril 2026) :
    // titre `bodyEmphasized` noir aligné à gauche, description grise gauche,
    // `subtitle` (eyebrow) **non rendu**.
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (moduleTitle.isNotEmpty) ...[
          Text(
            moduleTitle,
            style: AppTypography.bodyEmphasized.copyWith(
              color: AppColors.black,
            ),
          ),
        ],
        if (description.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.s2),
          Text(
            description,
            style: AppTypography.bodyRegular.copyWith(
              color: AppColors.textSecondary,
              height: 1.45,
            ),
          ),
        ],
        if (hasHeader) const SizedBox(height: AppSpacing.s4),
        for (var i = 0; i < items.length; i++) ...[
          if (i > 0) const SizedBox(height: AppSpacing.s2),
          _buildDocumentsListItem(items[i]),
        ],
      ],
    );
  }

  Widget _buildDocumentsListItem(Map<String, dynamic> item) {
    final downloadUrl = (item['downloadUrl'] as String?)?.trim() ?? '';
    final displayName = (item['displayName'] as String?)?.trim();
    final formatLabel = (item['formatLabel'] as String?)?.trim() ?? '';
    final sizeLabel = (item['sizeLabel'] as String?)?.trim() ?? '';
    final dateLabel = (item['dateLabel'] as String?)?.trim() ?? '';
    final mimeType = (item['mimeType'] as String?)?.trim() ?? '';

    final title = (displayName != null && displayName.isNotEmpty) ? displayName : 'Document';

    final String subtitle;
    if (formatLabel.isNotEmpty && sizeLabel.isNotEmpty) {
      subtitle = '$formatLabel · $sizeLabel';
    } else if (formatLabel.isNotEmpty) {
      subtitle = formatLabel;
    } else if (sizeLabel.isNotEmpty) {
      subtitle = sizeLabel;
    } else if (dateLabel.isNotEmpty) {
      subtitle = dateLabel;
    } else {
      subtitle = 'Document';
    }

    return ArticleDocumentCard(
      title: title,
      subtitle: subtitle,
      fileIcon: _resolveDocumentIcon(mimeType, formatLabel),
      onTap: downloadUrl.isNotEmpty ? () => _launchUrl(downloadUrl) : null,
    );
  }

  /// Bloc article `MEDIA_IMAGE_CAROUSEL` (cf. `enrichPublicArticleBlockData.ts`) :
  /// `data` = `{ moduleTitle?, description?, carouselItems: [{ url, mediaId, alt }] }`.
  ///
  /// Rendu via [MediaImageCarouselStory] (DS, type « stories Instagram ») :
  /// - Image plein cadre 16:9, coins arrondis, fond bleu pâle pendant le chargement.
  /// - Story bar segmentée en overlay haut (1 segment par image).
  /// - Tap n'importe où sur l'image → image suivante (sens unique).
  /// - Swipe horizontal au doigt → précédent / suivant.
  /// - Loader [WaveDotsLoadingIndicator] centré tant que l'image n'est pas chargée.
  Widget _buildMediaImageCarouselBlock(ArticleBlock block) {
    final data = block.data;
    final moduleTitle = (data['moduleTitle'] as String?)?.trim() ?? '';
    final description = (data['description'] as String?)?.trim() ?? '';
    final rawItems = data['carouselItems'];
    if (rawItems is! List || rawItems.isEmpty) return const SizedBox.shrink();

    final items = rawItems
        .whereType<Map>()
        .map((m) => Map<String, dynamic>.from(m))
        .map((m) {
          final url = (m['url'] as String?)?.trim() ?? '';
          final alt = m['alt'] is String ? (m['alt'] as String).trim() : null;
          return MediaImageCarouselItem(url: url, alt: alt);
        })
        .where((it) => it.url.isNotEmpty)
        .toList();
    if (items.isEmpty) return const SizedBox.shrink();

    final hasHeader = moduleTitle.isNotEmpty || description.isNotEmpty;

    // Header aligné sur le formalisme `HEADING` (avril 2026) — voir
    // `_buildStepsModuleBlock` / `_buildDocumentsListBlock` pour la même règle.
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (moduleTitle.isNotEmpty) ...[
          Text(
            moduleTitle,
            style: AppTypography.bodyEmphasized.copyWith(
              color: AppColors.black,
            ),
          ),
        ],
        if (description.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.s2),
          Text(
            description,
            style: AppTypography.bodyRegular.copyWith(
              color: AppColors.textSecondary,
              height: 1.45,
            ),
          ),
        ],
        if (hasHeader) const SizedBox(height: AppSpacing.s4),
        MediaImageCarouselStory(items: items),
      ],
    );
  }

  /// Icône fichier dérivée du `mimeType` (priorité) ou du `formatLabel` (fallback).
  /// Conserve `picture_as_pdf_rounded` (défaut DS) tant que ce n'est pas un autre type connu.
  IconData _resolveDocumentIcon(String mimeType, String formatLabel) {
    final m = mimeType.toLowerCase();
    final f = formatLabel.toUpperCase();
    if (m.contains('pdf') || f == 'PDF') return Icons.picture_as_pdf_rounded;
    if (m.startsWith('image/') ||
        const {'PNG', 'JPG', 'JPEG', 'GIF', 'WEBP', 'SVG', 'HEIC'}.contains(f)) {
      return Icons.image_rounded;
    }
    if (m.startsWith('video/') ||
        const {'MP4', 'MOV', 'AVI', 'MKV', 'WEBM'}.contains(f)) {
      return Icons.movie_rounded;
    }
    if (m.startsWith('audio/') ||
        const {'MP3', 'WAV', 'AAC', 'M4A', 'OGG'}.contains(f)) {
      return Icons.audiotrack_rounded;
    }
    if (m.contains('zip') || m.contains('compressed') ||
        const {'ZIP', 'RAR', '7Z', 'TAR', 'GZ'}.contains(f)) {
      return Icons.folder_zip_rounded;
    }
    if (m.contains('csv') || m.contains('sheet') || m.contains('excel') ||
        const {'CSV', 'XLS', 'XLSX', 'NUMBERS'}.contains(f)) {
      return Icons.table_chart_rounded;
    }
    if (m.contains('word') || m.contains('document') ||
        const {'DOC', 'DOCX', 'PAGES', 'TXT', 'RTF'}.contains(f)) {
      return Icons.description_rounded;
    }
    if (m.contains('presentation') || m.contains('powerpoint') ||
        const {'PPT', 'PPTX', 'KEY'}.contains(f)) {
      return Icons.slideshow_rounded;
    }
    return Icons.insert_drive_file_rounded;
  }

  /// Bloc article `BULLET_LIST` : chaque item utilise [DsSuccessBulletItem]
  /// (DS), qui pose un avatar [DsSuccessIcon] à **gauche** du texte et le
  /// centre verticalement sur la première ligne (calcul `fontSize × height`).
  Widget _buildBulletListBlock(ArticleBlock block) {
    final items = (block.data['items'] is List)
        ? (block.data['items'] as List)
            .map((e) => e.toString())
            .where((e) => e.trim().isNotEmpty)
            .toList()
        : const <String>[];
    if (items.isEmpty) return const SizedBox.shrink();

    final textStyle = AppTypography.bodyRegular.copyWith(
      color: AppColors.black,
      height: 1.45,
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (var i = 0; i < items.length; i++)
          Padding(
            padding: EdgeInsets.only(
              bottom: i == items.length - 1 ? 0 : AppSpacing.s2,
            ),
            child: DsSuccessBulletItem(
              text: items[i],
              style: textStyle,
            ),
          ),
      ],
    );
  }

  /// Paragraphe : atomes body (Regular / Emphasized / Italic / EmphasizedItalic).
  ///
  /// Avril 2026 — le contenu est désormais interprété comme du **Markdown**
  /// pour rester cohérent avec le rendu web (`<ReactMarkdown>` dans
  /// [ArticleBlockStream]). Les caractères `**gras**`, `*italique*`,
  /// `[lien](url)` sont rendus comme tels au lieu d'apparaître en clair.
  /// Le `baseStyle` (gras/italique global du bloc) reste appliqué via le
  /// styleSheet `p`, et les surcharges `strong` / `em` / `a` viennent par
  /// dessus pour les inlines.
  ///
  /// La gestion de `## titre` et `---` au sein du markdown n'est **pas**
  /// faite ici : elle est portée par [_buildGroupedBlocks] qui découpe le
  /// texte via [splitParagraphMarkdown] pour pouvoir respectivement émettre
  /// un heading natif (hors carte) et fermer/rouvrir la carte blanche.
  Widget _buildParagraphBlock(ArticleBlock block) {
    final raw = block.data['text'] as String? ?? '';
    if (raw.trim().isEmpty) return const SizedBox.shrink();
    return _paragraphMarkdownWidget(raw, _paragraphBaseStyle(block));
  }

  /// Style de base du paragraphe en fonction des flags `bold` / `italic`
  /// portés par la donnée du bloc. Réutilisé par [_buildParagraphBlock] et
  /// par [_buildGroupedBlocks] pour les sous-segments texte issus de
  /// [splitParagraphMarkdown].
  TextStyle _paragraphBaseStyle(ArticleBlock block) {
    final isBold = block.data['bold'] == true;
    final isItalic = block.data['italic'] == true;
    final TextStyle base;
    if (isBold && isItalic) {
      base = AppTypography.bodyEmphasizedItalic;
    } else if (isBold) {
      base = AppTypography.bodyEmphasized;
    } else if (isItalic) {
      base = AppTypography.bodyItalic;
    } else {
      base = AppTypography.bodyRegular;
    }
    return base.copyWith(color: AppColors.black, height: 1.45);
  }

  /// Rend un fragment de texte markdown comme un paragraphe d'article
  /// (typos DS, blockquote, table, code…). Délégué à [ArticleParagraphMarkdown]
  /// (partagé avec le chat IA pour l'interprétation des réponses bot).
  Widget _paragraphMarkdownWidget(String text, TextStyle baseStyle) {
    return ArticleParagraphMarkdown(
      text: text,
      baseStyle: baseStyle,
    );
  }

  /// Markdown brut Help/Academy sans blocs CMS : mêmes règles que les
  /// paragraphes (`---` → nouveau module ; titres ATX → DS Section Title).
  List<Widget> _buildMarkdownFallbackModules(String markdown) {
    final out = <Widget>[];
    final pending = <Widget>[];
    final baseStyle = AppTypography.bodyRegular.copyWith(
      color: AppColors.black,
      height: 1.45,
    );

    void append(Widget w) {
      if (pending.isNotEmpty) {
        pending.add(const SizedBox(height: AppSpacing.s4));
      }
      pending.add(w);
    }

    void flush() {
      if (pending.isEmpty) return;
      out.add(_padH(_wrapInCard(List.of(pending))));
      out.add(const SizedBox(height: AppSpacing.s8));
      pending.clear();
    }

    for (final seg in splitParagraphMarkdown(markdown.trim())) {
      switch (seg) {
        case ParagraphDividerSegment():
          flush();
        case ParagraphHeadingSegment(
            text: final headingText,
            level: final headingLevel,
          ):
          final clean = headingText.trim();
          if (clean.isEmpty) break;
          append(
            headingLevel == 1
                ? AppSectionTitle(clean)
                : AppSectionTitle2(clean),
          );
        case ParagraphTextSegment(text: final paragraphText):
          append(_paragraphMarkdownWidget(paragraphText, baseStyle));
      }
    }
    flush();
    return out;
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

  ArticleDetail _mapHelpToArticleDetail(HelpArticleDetail h) {
    return ArticleDetail(
      id: h.id,
      slug: h.slug,
      title: h.question,
      standfirst: h.standfirst,
      coverUrl: h.coverUrl.trim(),
      authorName: '',
      publishedAt: h.publishedAt,
      updatedAt: h.updatedAt ?? DateTime.now(),
      readingTime: 0,
      categorySlugs: const [],
      categories: h.categoryTitle.trim().isNotEmpty
          ? [
              ArticleCategory(
                id: '',
                slug: h.categorySlug,
                label: h.categoryTitle,
              ),
            ]
          : const [],
      galleryUrls: const [],
      documents: const [],
      blocks: [
        for (final b in h.blocks)
          ArticleBlock(
            id: b.id,
            type: b.type,
            order: b.order,
            data: b.data,
            imageUrl: b.imageUrl,
          ),
      ],
    );
  }

  ArticleDetail _mapAcademyToArticleDetail(AcademyArticleDetail d) {
    return ArticleDetail(
      id: d.id,
      slug: d.slug,
      title: d.question,
      standfirst: d.standfirst,
      coverUrl: d.coverUrl.trim(),
      authorName: '',
      publishedAt: d.publishedAt,
      updatedAt: d.updatedAt ?? DateTime.now(),
      readingTime: 0,
      categorySlugs: const [],
      categories: d.categoryTitle.trim().isNotEmpty
          ? [
              ArticleCategory(
                id: '',
                slug: d.categorySlug,
                label: d.categoryTitle,
              ),
            ]
          : const [],
      galleryUrls: const [],
      documents: const [],
      blocks: [
        for (final b in d.blocks)
          ArticleBlock(
            id: b.id,
            type: b.type,
            order: b.order,
            data: b.data,
            imageUrl: b.imageUrl,
          ),
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

