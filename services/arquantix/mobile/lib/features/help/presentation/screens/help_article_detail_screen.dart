import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../design_system/design_system.dart';
import '../../data/help_api.dart';
import '../../domain/models/help_center_models.dart';

class HelpArticleDetailScreen extends StatefulWidget {
  const HelpArticleDetailScreen({
    super.key,
    required this.collectionSlug,
    required this.categorySlug,
    required this.articleSlug,
  });

  final String collectionSlug;
  final String categorySlug;
  final String articleSlug;

  @override
  State<HelpArticleDetailScreen> createState() =>
      _HelpArticleDetailScreenState();
}

class _HelpArticleDetailScreenState extends State<HelpArticleDetailScreen> {
  final HelpApi _api = HelpApi();
  bool _loading = true;
  String? _error;
  HelpArticleDetail? _detail;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final detail = await _api.getArticleDetail(
        collectionSlug: widget.collectionSlug,
        categorySlug: widget.categorySlug,
        articleSlug: widget.articleSlug,
      );
      if (!mounted) return;
      setState(() {
        _detail = detail;
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

  Future<void> _openUrl(String raw) async {
    final uri = Uri.tryParse(raw);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  static const double _hPad = AppSpacing.s4;

  Widget _padH(Widget child) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: _hPad),
        child: child,
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.back,
        onBackTap: () => Navigator.of(context).pop(),
        title: _detail?.question ?? 'Article',
        centerTitle: true,
        titleMaxLines: 1,
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 48, color: Colors.grey[400]),
              const SizedBox(height: 16),
              Text(
                _error!,
                style: AppTypography.paragraph
                    .copyWith(color: Colors.grey[600]),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }
    if (_detail == null) return const SizedBox.shrink();
    return _buildContent();
  }

  Widget _buildContent() {
    final detail = _detail!;
    final hasMarkdown = detail.markdownContent.trim().isNotEmpty;
    final hasBlocks = detail.blocks.isNotEmpty;

    return SingleChildScrollView(
      padding: const EdgeInsets.only(
        top: AppSpacing.s4,
        bottom: AppSpacing.s8,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (detail.standfirst.trim().isNotEmpty) ...[
            _padH(_buildIntroCard(detail)),
            const SizedBox(height: AppSpacing.s8),
          ],

          if (hasMarkdown)
            _padH(_buildMarkdownCard(detail.markdownContent))
          else if (hasBlocks)
            ..._buildGroupedBlocks(detail.blocks),
        ],
      ),
    );
  }

  Widget _buildIntroCard(HelpArticleDetail detail) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.s4),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: Text(
        detail.standfirst,
        style: AppTypography.bodyEmphasized.copyWith(
          color: AppColors.black,
        ),
      ),
    );
  }

  Widget _buildMarkdownCard(String markdown) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.s4),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: MarkdownBody(
        data: markdown,
        selectable: true,
        styleSheet: _markdownStyle(),
        onTapLink: (_, href, __) {
          if (href != null && href.trim().isNotEmpty) {
            _openUrl(href);
          }
        },
      ),
    );
  }

  MarkdownStyleSheet _markdownStyle() {
    return MarkdownStyleSheet(
      p: AppTypography.bodySmRegular.copyWith(
        color: AppColors.black,
        height: 1.5,
      ),
      h1: AppTypography.sectionTitle.copyWith(
        color: AppColors.black,
      ),
      h2: AppTypography.headerAppbar.copyWith(
        color: AppColors.black,
      ),
      h3: AppTypography.bodySmEmphasized.copyWith(
        color: AppColors.black,
      ),
      a: AppTypography.bodySmRegular.copyWith(
        color: AppColors.accent,
        height: 1.5,
      ),
      blockSpacing: 12,
      listBullet: AppTypography.bodySmRegular.copyWith(
        color: AppColors.black,
      ),
    );
  }

  static const _textBlockTypes = {'HEADING', 'PARAGRAPH', 'BULLET_LIST'};

  List<Widget> _buildGroupedBlocks(List<HelpArticleBlock> blocks) {
    final widgets = <Widget>[];
    final pendingTextWidgets = <Widget>[];

    void flushText() {
      if (pendingTextWidgets.isEmpty) return;
      widgets.add(_padH(_wrapInCard(List.of(pendingTextWidgets))));
      widgets.add(const SizedBox(height: AppSpacing.s8));
      pendingTextWidgets.clear();
    }

    for (final block in blocks) {
      if (_textBlockTypes.contains(block.type)) {
        if (pendingTextWidgets.isNotEmpty) {
          pendingTextWidgets.add(const SizedBox(height: AppSpacing.s4));
        }
        pendingTextWidgets.add(_buildBlockContent(block));
      } else {
        flushText();
        widgets.add(_padH(_buildBlockContent(block)));
        widgets.add(const SizedBox(height: AppSpacing.s8));
      }
    }

    flushText();
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

  Widget _buildBlockContent(HelpArticleBlock block) {
    switch (block.type) {
      case 'HEADING':
        return Text(
          (block.data['text'] ?? '').toString(),
          style: AppTypography.bodySmEmphasized.copyWith(
            color: AppColors.black,
          ),
        );

      case 'PARAGRAPH':
        final text = (block.data['text'] ?? '').toString();
        if (text.trim().isEmpty) return const SizedBox.shrink();
        return Text(
          text,
          style: AppTypography.bodySmRegular.copyWith(
            color: AppColors.black,
            height: 1.5,
          ),
        );

      case 'QUOTE':
        return ArticleQuoteBlock(
          quote: (block.data['text'] ?? '').toString(),
          author: block.data['author']?.toString(),
        );

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
                          style: AppTypography.bodySmRegular.copyWith(
                            color: AppColors.black,
                            height: 1.5,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              )
              .toList(),
        );

      case 'IMAGE':
        final imageUrl =
            (block.imageUrl ?? block.data['url'] ?? '').toString();
        if (imageUrl.trim().isEmpty) return const SizedBox.shrink();
        return ArticleImageBlock(
          imageUrl: imageUrl,
          caption: block.data['caption']?.toString(),
          height: 193,
        );

      case 'DOCUMENT':
        final label =
            (block.data['title'] ?? 'Ouvrir le document').toString();
        final url =
            (block.imageUrl ?? block.data['url'] ?? '').toString();
        if (url.trim().isEmpty) return const SizedBox.shrink();
        return ArticleDocumentCard(
          title: label,
          subtitle: block.data['subtitle']?.toString() ?? 'Document',
          onTap: () => _openUrl(url),
        );

      default:
        return const SizedBox.shrink();
    }
  }
}
