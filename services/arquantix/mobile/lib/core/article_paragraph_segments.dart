/// Découpage du contenu markdown d'un bloc `PARAGRAPH` en segments
/// structurés pour la page Article detail mobile (modules blancs + titres DS).
///
/// Conventions :
///
///   * `---` sur une ligne seule → **fermeture du module blanc** courant ; le
///     texte suivant ouvre un **nouveau** module blanc.
///   * Lignes ATX `# …` à `###### …` → **[ParagraphHeadingSegment]** ; le rendu
///     utilise les composants DS [AppSectionTitle] (niveau 1) ou
///     [AppSectionTitle2] (niveaux 2 à 6).
///
/// Le reste du markdown (gras, listes, `###` non capturés comme ligne seule,
/// etc.) reste dans des [ParagraphTextSegment] rendus via [MarkdownBody].
library;

sealed class ParagraphSegment {
  const ParagraphSegment();
}

/// Bloc de texte markdown libre (peut contenir `**gras**`, `*italique*`,
/// `[lien](url)`, listes…). À rendre via `MarkdownBody`.
final class ParagraphTextSegment extends ParagraphSegment {
  const ParagraphTextSegment(this.text);

  final String text;
}

/// Heading extrait d'une ligne ATX `# …` … `###### …`.
///
/// Rendu Article detail : [AppSectionTitle] si niveau 1, sinon [AppSectionTitle2].
final class ParagraphHeadingSegment extends ParagraphSegment {
  const ParagraphHeadingSegment(this.text, {this.level = 2})
      : assert(level >= 1 && level <= 6, 'Only ATX levels 1–6');

  final String text;

  /// Niveau ATX : `1` pour `#`, … `6` pour `######`.
  final int level;
}

/// Séparateur de carte issu d'une ligne `---`. Aucun rendu propre : signale
/// à l'appelant qu'il doit `flush` la carte blanche en cours et ouvrir une
/// nouvelle carte sur les segments suivants.
final class ParagraphDividerSegment extends ParagraphSegment {
  const ParagraphDividerSegment();
}

/// Découpe [markdown] en une suite de [ParagraphSegment].
///
/// Garanties :
///   * Les segments [ParagraphTextSegment] retournés ont un `text` non vide
///     (les blocs intermédiaires composés uniquement de lignes vides sont
///     filtrés).
///   * Les `---` et titres ATX consécutifs n'entraînent pas de segments texte
///     vides entre eux.
///   * Si [markdown] ne contient ni `---` ni ligne ATX titre, on retourne un
///     unique [ParagraphTextSegment] avec le contenu trimé (ou liste vide).
List<ParagraphSegment> splitParagraphMarkdown(String markdown) {
  final segments = <ParagraphSegment>[];
  final buffer = <String>[];

  void flushText() {
    if (buffer.isEmpty) return;
    final joined = buffer.join('\n').trim();
    buffer.clear();
    if (joined.isEmpty) return;
    segments.add(ParagraphTextSegment(joined));
  }

  // CommonMark autorise jusqu'à 3 espaces d'indentation avant un thematic
  // break / heading ATX. On tolère ce cas pour rester compatible avec le
  // rendu web (`ReactMarkdown` + `remark-gfm`).
  //
  // Le groupe `(#{1,6})` capture tout titre ATX ; `###`+ sort du flux texte
  // pour être rendu en [AppSectionTitle2] (niveaux 2–6).
  final headingRe = RegExp(r'^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$');
  final dividerRe = RegExp(r'^ {0,3}---\s*$');

  for (final line in markdown.split('\n')) {
    if (dividerRe.hasMatch(line)) {
      flushText();
      segments.add(const ParagraphDividerSegment());
      continue;
    }

    final headingMatch = headingRe.firstMatch(line);
    if (headingMatch != null) {
      flushText();
      final level = headingMatch.group(1)!.length; // 1 … 6
      final title = headingMatch.group(2)!.trim();
      if (title.isNotEmpty) {
        segments.add(ParagraphHeadingSegment(title, level: level));
      }
      continue;
    }

    buffer.add(line);
  }

  flushText();
  return segments;
}
