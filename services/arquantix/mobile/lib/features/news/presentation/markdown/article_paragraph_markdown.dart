import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:markdown/markdown.dart' as md;
import 'package:url_launcher/url_launcher.dart';

import '../../../../design_system/design_system.dart';
import 'article_detail_markdown_body.dart';

/// Rend un fragment de texte Markdown comme un paragraphe d'article.
///
/// Utilise [ArticleDetailMarkdownBody] (fork local de `MarkdownBody`) avec :
///
/// - les blocs de code ``` ``` rendus comme du paragraphe (pas de monospace) ;
/// - les `<a>` stylés DS (accent + flèche) et fusionnables avec le texte ;
/// - les `>` blockquote → [ArticleQuoteBlock] (citation/note selon attribution) ;
/// - les `<table>` avec scrollbar horizontale custom dessinée *sous* la dernière
///   ligne ([_MarkdownTableHorizontalScrollbar]).
///
/// Le widget n'ajoute **aucun fond / carte** : il s'intègre comme du texte courant
/// dans un paragraphe (article, chat IA, etc.). [baseStyle] définit la typo
/// utilisée pour les paragraphes du markdown rendu.
class ArticleParagraphMarkdown extends StatelessWidget {
  const ArticleParagraphMarkdown({
    super.key,
    required this.text,
    required this.baseStyle,
    this.onOpenLink,
    this.blockSpacing = 0,
  });

  /// Markdown brut (peut contenir gras, italique, listes, liens, tableaux,
  /// blockquotes, blocs de code…).
  final String text;

  /// Style typo des paragraphes (`p`, `strong`, `em`, `a`, `listBullet`).
  final TextStyle baseStyle;

  /// Surcharge l'ouverture d'un lien (par défaut : [launchUrl] en mode externe).
  final Future<void> Function(String href)? onOpenLink;

  /// Espacement vertical entre deux blocs Markdown frères (paragraphes,
  /// listes, titres, blockquote…). Défaut `0` pour les articles dont chaque
  /// segment est un widget indépendant avec son propre spacing externe.
  /// Le chat IA (multi-blocs dans une seule réponse) passe une valeur > 0.
  final double blockSpacing;

  @override
  Widget build(BuildContext context) {
    final borderSide = BorderSide(
      color: AppColors.separatorOpaque,
      width: 1,
    );
    final tableDepth = _MarkdownTableDepthTracker();
    final openLink = onOpenLink ?? _defaultOpenMarkdownLink;

    return ArticleDetailMarkdownBody(
      data: _normalizeMarkdownLinkLabelsForFlutterMarkdown(text),
      selectable: true,
      onTapLink: (_, href, __) {
        if (href == null || href.trim().isEmpty) return;
        openLink(href.trim());
      },
      builders: <String, MarkdownElementBuilder>{
        'blockquote': _ArticleParagraphMarkdownBlockquoteBuilder(),
        'table': _ArticleParagraphMarkdownTableBoundaryBuilder(tableDepth),
        'a': _ArticleParagraphMarkdownLinkBuilder(
          onOpen: (href) async {
            if (href == null || href.trim().isEmpty) return;
            await openLink(href.trim());
          },
          tableDepth: tableDepth,
          paragraphBaseStyle: baseStyle,
        ),
      },
      styleSheet: MarkdownStyleSheet(
        p: baseStyle,
        // Gras Markdown (`**…**`) → atome DS Body emphasized (Inter Semi‑Bold
        // 17/w600). Si le paragraphe courant est en italique on bascule sur
        // bodyEmphasizedItalic pour préserver le contexte. La couleur du
        // paragraphe est conservée pour s'aligner sur le baseStyle (article
        // noir / chat textPrimary).
        strong: (baseStyle.fontStyle == FontStyle.italic
                ? AppTypography.bodyEmphasizedItalic
                : AppTypography.bodyEmphasized)
            .copyWith(color: baseStyle.color),
        em: baseStyle.copyWith(fontStyle: FontStyle.italic),
        a: baseStyle.copyWith(
          color: AppColors.accent,
          decoration: TextDecoration.none,
        ),
        listBullet: baseStyle,
        blockSpacing: blockSpacing,
        pPadding: EdgeInsets.zero,
        // Titres Markdown → atomes DS, palier net entre chaque niveau :
        // - `# titre` → [AppTypography.title1] (Title 1, 24/w700) — 4px
        //   au-dessus de Section title pour un palier visible
        // - `## titre` → [AppTypography.sectionTitle] (Section title, 20/w700)
        // - `### titre` → [AppTypography.bodyEmphasized] (Body emphasized, 17/w600)
        // - `#### titre` et + → fallback Body emphasized (cohérence visuelle)
        // Padding top dosé (en plus de [blockSpacing]) pour aérer du paragraphe
        // précédent ; padding bottom plus serré, dans l'esprit ChatGPT.
        h1: AppTypography.title1.copyWith(color: AppColors.textPrimary),
        h1Padding: const EdgeInsets.only(top: AppSpacing.md, bottom: AppSpacing.xs),
        h2: AppTypography.sectionTitle.copyWith(color: AppColors.textPrimary),
        h2Padding: const EdgeInsets.only(top: AppSpacing.md, bottom: AppSpacing.xs),
        h3: AppTypography.bodyEmphasized.copyWith(color: AppColors.textPrimary),
        h3Padding: const EdgeInsets.only(top: AppSpacing.sm, bottom: AppSpacing.xs),
        h4: AppTypography.bodyEmphasized.copyWith(color: AppColors.textPrimary),
        h4Padding: const EdgeInsets.only(top: AppSpacing.sm, bottom: AppSpacing.xs),
        // Tableaux : typos Item (DS), séparateurs horizontaux ; barre de défilement
        // custom rendue sous la dernière ligne par [ArticleDetailMarkdownBuilder].
        tableHead: AppTypography.itemPrimary.copyWith(color: AppColors.black),
        tableBody:
            AppTypography.itemSupporting.copyWith(color: AppColors.black),
        tableHeadAlign: TextAlign.left,
        tableBorder: TableBorder(
          horizontalInside: borderSide,
        ),
        tableColumnWidth: IntrinsicColumnWidth(),
        tableCellsPadding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.md,
        ),
        tablePadding: EdgeInsets.zero,
        tableCellsDecoration: const BoxDecoration(),
        tableScrollbarThumbVisibility: false,
        // Séparateur Markdown `---` / `<hr>` : ligne fine 1px gris léger
        // ([separatorOpaque] DS) au lieu du double-trait épais par défaut
        // de flutter_markdown.
        horizontalRuleDecoration: const BoxDecoration(
          border: Border(
            top: BorderSide(
              color: AppColors.separatorOpaque,
              width: 1,
            ),
          ),
        ),
      ),
    );
  }
}

Future<void> _defaultOpenMarkdownLink(String href) async {
  final uri = Uri.tryParse(href);
  if (uri == null) return;
  try {
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  } catch (_) {
    // Lien externe non ouvrable : on ignore silencieusement (cohérent avec les
    // autres écrans qui ne remontent pas non plus l'erreur à l'utilisateur).
  }
}

/// Évite les doublons de libellé avec un [MarkdownElementBuilder] sur les `<a>` :
/// flutter_markdown ne remplace que le *premier* enfant inline et conserve les autres
/// (ex. emphases dans `[Voir **les** offres](url)` → répétition du texte).
///
/// On aplatit le markdown à l'intérieur de chaque `[libellé](url)` en texte visible brut.
String _normalizeMarkdownLinkLabelsForFlutterMarkdown(String markdown) {
  return markdown.replaceAllMapped(
    RegExp(r'\[([^\]]+)\]\(([^)]*)\)'),
    (Match m) {
      var label = m.group(1)!.replaceAll(RegExp(r'[\r\n]+'), ' ').trim();
      final url = m.group(2)!;
      for (var i = 0; i < 6; i++) {
        final next = label
            .replaceAllMapped(
              RegExp(r'\*\*([^*]+)\*\*'),
              (Match x) => x.group(1)!,
            )
            .replaceAllMapped(
              RegExp(r'(?<!\*)\*(?!\*)([^*]+)\*(?!\*)'),
              (Match x) => x.group(1)!,
            )
            .replaceAllMapped(
              RegExp(r'__([^_]+)__'),
              (Match x) => x.group(1)!,
            )
            .replaceAllMapped(
              RegExp(r'(?<!_)_(?!_)([^_]+)_(?!_)'),
              (Match x) => x.group(1)!,
            )
            .replaceAll('`', '');
        if (next == label) break;
        label = next;
      }
      return '[$label]($url)';
    },
  );
}

/// Concatène les paragraphes d'un `<blockquote>` Markdown avec des sauts de ligne.
String _markdownBlockquotePlainText(md.Element blockquote) {
  final ch = blockquote.children;
  if (ch == null || ch.isEmpty) return '';
  final parts = <String>[];
  for (final node in ch) {
    if (node is md.Element) {
      final t = node.textContent.trim();
      if (t.isNotEmpty) parts.add(t);
    } else if (node is md.Text) {
      final t = node.text.trim();
      if (t.isNotEmpty) parts.add(t);
    }
  }
  return parts.join('\n');
}

/// Détecte une attribution en fin de bloc : ligne seule `— Auteur` / `- …`, ou
/// `… — Auteur` sur une seule ligne. Sinon tout le texte est la citation (note).
({String quote, String? author}) _markdownParseBlockquoteAttribution(
    String raw) {
  final trimmed = raw.trim();
  if (trimmed.isEmpty) return (quote: '', author: null);

  final lines = trimmed
      .split(RegExp(r'\r?\n'))
      .map((l) => l.trim())
      .where((l) => l.isNotEmpty)
      .toList();

  final attStart = RegExp(r'^[—\-–]\s*(.+)$');

  if (lines.length >= 2) {
    final m = attStart.firstMatch(lines.last);
    if (m != null) {
      final authorPart = m.group(1)!.trim();
      final quotePart = lines.sublist(0, lines.length - 1).join('\n').trim();
      if (quotePart.isNotEmpty && authorPart.isNotEmpty) {
        return (quote: quotePart, author: authorPart);
      }
    }
  }

  if (lines.length == 1) {
    final m = RegExp(r'^(.*?)\s+[—\-–]\s+(.+)$').firstMatch(lines.single);
    if (m != null) {
      final qPart = m.group(1)!.trim();
      final aPart = m.group(2)!.trim();
      if (qPart.isNotEmpty && aPart.isNotEmpty) {
        return (quote: qPart, author: aPart);
      }
    }
  }

  return (quote: trimmed, author: null);
}

bool _markdownBlockquoteHasNested(md.Element el) {
  for (final c in el.children ?? const <md.Node>[]) {
    if (c is! md.Element) continue;
    if (c.tag == 'blockquote') return true;
    if (_markdownBlockquoteHasNested(c)) return true;
  }
  return false;
}

/// Bloc `>` Markdown → [ArticleQuoteBlock] (citation avec guillemets si auteur ;
/// sinon note sans guillemets).
final class _ArticleParagraphMarkdownBlockquoteBuilder
    extends MarkdownElementBuilder {
  @override
  Widget? visitElementAfterWithContext(
    BuildContext context,
    md.Element element,
    TextStyle? preferredStyle,
    TextStyle? parentStyle,
  ) {
    if (element.tag != 'blockquote') return null;
    if (_markdownBlockquoteHasNested(element)) return null;
    final raw = _markdownBlockquotePlainText(element);
    final parsed = _markdownParseBlockquoteAttribution(raw);
    if (parsed.quote.isEmpty) return const SizedBox.shrink();
    return ArticleQuoteBlock(
      quote: parsed.quote,
      author: parsed.author,
      asCard: true,
    );
  }
}

/// Compteur de profondeur `<table>` pour les builders Markdown du même bloc.
final class _MarkdownTableDepthTracker {
  int _depth = 0;

  bool get insideTable => _depth > 0;

  void enterTable() => _depth++;

  void exitTable() {
    if (_depth > 0) _depth--;
  }
}

/// Entre/sort d'un tableau sans remplacer le widget tableau (retour `null`).
/// Permet aux liens `<a>` de savoir s'ils sont dans une cellule.
final class _ArticleParagraphMarkdownTableBoundaryBuilder
    extends MarkdownElementBuilder {
  _ArticleParagraphMarkdownTableBoundaryBuilder(this.depth);

  final _MarkdownTableDepthTracker depth;

  @override
  void visitElementBefore(md.Element element) {
    if (element.tag == 'table') depth.enterTable();
  }

  @override
  Widget? visitElementAfterWithContext(
    BuildContext context,
    md.Element element,
    TextStyle? preferredStyle,
    TextStyle? parentStyle,
  ) {
    if (element.tag == 'table') depth.exitTable();
    return null;
  }
}

/// Liens Markdown : le rendu doit rester **fusionnable** avec le texte adjacent
/// (`SelectableText.rich` dans flutter_markdown). Un [GestureDetector] autour du
/// lien entier empêche la fusion → second enfant du [Wrap] → ligne suivante et
/// double saut visuel après un `<br>` dans une liste. On encapsule donc le bloc
/// tap texte + icône dans un seul [WidgetSpan] à l'intérieur d'un [Text.rich].
///
/// [visitElementBefore] fusionne toujours le sous-arbre `<a>` en un seul [md.Text].
final class _ArticleParagraphMarkdownLinkBuilder
    extends MarkdownElementBuilder {
  _ArticleParagraphMarkdownLinkBuilder({
    required this.onOpen,
    required this.tableDepth,
    required this.paragraphBaseStyle,
  });

  final Future<void> Function(String? href) onOpen;
  final _MarkdownTableDepthTracker tableDepth;
  final TextStyle paragraphBaseStyle;

  static const double _paragraphLinkIconSize = 18;
  static const double _tableLinkIconSize = 16;

  @override
  void visitElementBefore(md.Element element) {
    if (element.tag != 'a') return;
    final merged = element.textContent.trim();
    final href = element.attributes['href']?.trim() ?? '';
    final label = merged.isEmpty ? href : merged;
    if (label.isEmpty) return;
    final ch = element.children;
    if (ch == null || ch.isEmpty) return;
    try {
      ch
        ..clear()
        ..add(md.Text(label));
    } catch (_) {
      // Liste non modifiable (ex. `const []`) : la normalisation markdown reste le secours.
    }
  }

  @override
  Widget? visitElementAfterWithContext(
    BuildContext context,
    md.Element element,
    TextStyle? preferredStyle,
    TextStyle? parentStyle,
  ) {
    final href = element.attributes['href'];
    final rawLabel = element.textContent.trim();
    final label = rawLabel.isEmpty ? (href ?? '').trim() : rawLabel;
    if (label.isEmpty) return null;

    const color = AppColors.accent;

    if (tableDepth.insideTable) {
      final linkStyle = AppTypography.itemSupporting.copyWith(color: color);
      return Text.rich(
        TextSpan(
          children: [
            WidgetSpan(
              alignment: PlaceholderAlignment.middle,
              child: GestureDetector(
                behavior: HitTestBehavior.translucent,
                onTap: () => onOpen(href),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Text(label, style: linkStyle),
                    Padding(
                      padding: const EdgeInsets.only(left: AppSpacing.sm),
                      child: KalaiIcon(
                        KalaiIcons.arrowRight,
                        size: _tableLinkIconSize,
                        color: color,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
        softWrap: false,
      );
    }

    final linkStyle = paragraphBaseStyle.copyWith(
      color: color,
      decoration: TextDecoration.none,
    );

    return Text.rich(
      TextSpan(
        children: [
          WidgetSpan(
            alignment: PlaceholderAlignment.middle,
            child: GestureDetector(
              behavior: HitTestBehavior.translucent,
              onTap: () => onOpen(href),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Text(label, style: linkStyle),
                  Padding(
                    padding: const EdgeInsets.only(left: AppSpacing.sm),
                    child: KalaiIcon(
                      KalaiIcons.arrowRight,
                      size: _paragraphLinkIconSize,
                      color: color,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
