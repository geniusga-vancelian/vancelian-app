// Variante locale de [MarkdownBody] : parse via [ArticleDetailMarkdownBuilder]
// (scrollbar custom sous les tableaux, blocs ``` rendus comme paragraphe…).

// ignore_for_file: implementation_imports — kFallbackStyle non exporté par flutter_markdown.

import 'dart:convert';

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_markdown/src/_functions_io.dart'
    if (dart.library.js_interop) 'package:flutter_markdown/src/_functions_web.dart';
import 'package:markdown/markdown.dart' as md;

import 'article_detail_markdown_builder.dart';

/// Variante de [MarkdownBody] qui rend les tableaux Markdown avec une scrollbar
/// horizontale custom dessinée sous la dernière ligne.
class ArticleDetailMarkdownBody extends MarkdownWidget {
  const ArticleDetailMarkdownBody({
    super.key,
    required super.data,
    super.selectable,
    super.styleSheet,
    super.styleSheetTheme = null,
    super.syntaxHighlighter,
    super.onSelectionChanged,
    super.onTapLink,
    super.onTapText,
    super.imageDirectory,
    super.blockSyntaxes,
    super.inlineSyntaxes,
    super.extensionSet,
    @Deprecated('Use sizedImageBuilder instead.') super.imageBuilder,
    super.sizedImageBuilder,
    super.checkboxBuilder,
    super.bulletBuilder,
    super.builders,
    super.paddingBuilders,
    super.listItemCrossAxisAlignment,
    this.shrinkWrap = true,
    super.fitContent = true,
    super.softLineBreak,
  });

  final bool shrinkWrap;

  @override
  State<MarkdownWidget> createState() => _ArticleDetailMarkdownBodyState();

  @override
  Widget build(BuildContext context, List<Widget>? children) {
    if (children!.length == 1 && shrinkWrap) {
      return children.single;
    }
    return Column(
      mainAxisSize: shrinkWrap ? MainAxisSize.min : MainAxisSize.max,
      crossAxisAlignment:
          fitContent ? CrossAxisAlignment.start : CrossAxisAlignment.stretch,
      children: children,
    );
  }
}

class _ArticleDetailMarkdownBodyState extends State<ArticleDetailMarkdownBody>
    implements MarkdownBuilderDelegate {
  List<Widget>? _children;
  final List<GestureRecognizer> _recognizers = <GestureRecognizer>[];

  @override
  void didChangeDependencies() {
    _parseMarkdown();
    super.didChangeDependencies();
  }

  @override
  void didUpdateWidget(ArticleDetailMarkdownBody oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.data != oldWidget.data ||
        widget.styleSheet != oldWidget.styleSheet) {
      _parseMarkdown();
    }
  }

  @override
  void dispose() {
    _disposeRecognizers();
    super.dispose();
  }

  void _parseMarkdown() {
    final MarkdownStyleSheet fallbackStyleSheet =
        kFallbackStyle(context, widget.styleSheetTheme);
    final MarkdownStyleSheet styleSheet =
        fallbackStyleSheet.merge(widget.styleSheet);

    _disposeRecognizers();

    final md.Document document = md.Document(
      blockSyntaxes: widget.blockSyntaxes,
      inlineSyntaxes: widget.inlineSyntaxes,
      extensionSet: widget.extensionSet ?? md.ExtensionSet.gitHubFlavored,
      encodeHtml: false,
    );

    final List<String> lines = const LineSplitter().convert(widget.data);
    final List<md.Node> astNodes = document.parseLines(lines);

    final ArticleDetailMarkdownBuilder builder = ArticleDetailMarkdownBuilder(
      delegate: this,
      selectable: widget.selectable,
      styleSheet: styleSheet,
      imageDirectory: widget.imageDirectory,
      // ignore: deprecated_member_use — aligné sur MarkdownWidget / flutter_markdown.
      imageBuilder: widget.imageBuilder,
      sizedImageBuilder: widget.sizedImageBuilder,
      checkboxBuilder: widget.checkboxBuilder,
      bulletBuilder: widget.bulletBuilder,
      builders: widget.builders,
      paddingBuilders: widget.paddingBuilders,
      fitContent: widget.fitContent,
      listItemCrossAxisAlignment: widget.listItemCrossAxisAlignment,
      onSelectionChanged: widget.onSelectionChanged,
      onTapText: widget.onTapText,
      softLineBreak: widget.softLineBreak,
    );

    _children = builder.build(astNodes);
  }

  void _disposeRecognizers() {
    if (_recognizers.isEmpty) {
      return;
    }
    final List<GestureRecognizer> localRecognizers =
        List<GestureRecognizer>.from(_recognizers);
    _recognizers.clear();
    for (final GestureRecognizer recognizer in localRecognizers) {
      recognizer.dispose();
    }
  }

  @override
  GestureRecognizer createLink(String text, String? href, String title) {
    final TapGestureRecognizer recognizer = TapGestureRecognizer()
      ..onTap = () {
        if (widget.onTapLink != null) {
          widget.onTapLink!(text, href, title);
        }
      };
    _recognizers.add(recognizer);
    return recognizer;
  }

  @override
  TextSpan formatText(MarkdownStyleSheet styleSheet, String code) {
    code = code.replaceAll(RegExp(r'\n$'), '');
    if (widget.syntaxHighlighter != null) {
      return widget.syntaxHighlighter!.format(code);
    }
    return TextSpan(style: styleSheet.code, text: code);
  }

  @override
  Widget build(BuildContext context) => widget.build(context, _children);
}
