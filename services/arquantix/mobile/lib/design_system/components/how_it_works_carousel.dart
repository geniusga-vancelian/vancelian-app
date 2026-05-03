import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import '../atoms/kalai_icons.dart';
import '../layout/module_horizontal_margin.dart';
import 'app_section_title.dart';
import 'ds_story_segment_bar.dart';
import 'kalai_icon.dart';

/// Modèle d'un item du carrousel [HowItWorksCarousel].
///
/// Conçu pour des modules type « How it works » / parcours étapes :
/// chaque carte porte un libellé d'étape (`stepLabel`), un titre et un CTA
/// texte optionnel. L'image (`imageUrl`) est **optionnelle** — si absente, la
/// colonne texte prend toute la largeur de la carte.
class HowItWorksCarouselItem {
  final String stepLabel;
  final String title;
  final String? imageUrl;
  final String? ctaLabel;
  final VoidCallback? onCtaTap;
  final VoidCallback? onTap;

  const HowItWorksCarouselItem({
    required this.stepLabel,
    required this.title,
    this.imageUrl,
    this.ctaLabel,
    this.onCtaTap,
    this.onTap,
  });
}

/// Marge horizontale du **titre**, des **cartes** et de la **barre de
/// bullets**. Pattern carrousel standard (cf. `MarketingCardsCarousel`,
/// `VideoBlockArticleModule`) : chaque carte fait `screenWidth − 2 ·
/// _moduleSideMargin` de large, et la 1ʳᵉ comme la dernière laissent une
/// marge complète sur leur bord externe écran.
const double _moduleSideMargin = kModuleHorizontalMargin;

/// Écart horizontal entre deux cartes adjacentes du carrousel — **8 px** =
/// **1/2 marge** ([_moduleSideMargin]). Conséquence directe : sur la carte
/// courante, la carte suivante est visible (« peek ») de **8 px**
/// (`_moduleSideMargin − _cardGap`), comportement standard d'un carrousel
/// de cartes (App Store, Play Store, …).
const double _cardGap = AppSpacing.s2;

/// Padding interne (top / right / bottom / left) de la carte autour du
/// contenu textuel — **16 px**. L'image, elle, est full hauteur et collée au
/// bord droit (pas de padding).
const double _cardInternalPadding = AppSpacing.s4;

/// Espacement vertical interne entre les éléments du contenu de la carte
/// (tag → titre, titre → CTA) — **12 px**.
const double _cardInternalGap = AppSpacing.s3;

/// Part de largeur prise par l'image de droite quand elle est présente.
/// Ratio **60 / 40** (texte 60 %, image 40 %) — fixé par le design.
const double _imageWidthFraction = 0.40;

/// Nombre maximum de bullets affichés à leur **largeur cible**. Au-delà, la
/// barre passe en mode auto-fit (chaque segment se réduit pour remplir la
/// largeur disponible).
const int _maxBulletsAtTargetWidth = 6;

/// Nombre maximum de lignes du titre de la carte — au-delà, ellipsis.
const int _cardTitleMaxLines = 2;

// ── Mesures internes des atomes DS pour calculer la hauteur intrinsèque ──

/// Padding horizontal interne du **step pill** (`_StepPill`) — convention DS
/// reprise de `_EnCoursTag` (`steps_module.dart`) pour l'atome textuel
/// `label/Emphasized SM` : 6 px à gauche / 6 px à droite.
const double _stepPillPaddingH = 6;

/// Padding vertical interne du **step pill** — 4 px en haut / 4 px en bas
/// (même convention DS que `_EnCoursTag`).
const double _stepPillPaddingV = 4;

/// Hauteur visuelle du **step pill** : line-height 13 (atome
/// `AppTypography.labelEmphasized` → 11 / lh 13) + 2 × `_stepPillPaddingV` (4)
/// = **21 px**. Sert au calcul de la hauteur intrinsèque max de la carte.
const double _tagHeight = 13 + 2 * _stepPillPaddingV;

/// Hauteur d'une ligne du titre carte (`AppTypography.itemPrimary` : 15 px /
/// line-height 20/15 → 20 px par ligne).
const double _cardTitleLineHeight = 20;

/// Hauteur visuelle du **CTA `_CtaLink`** (texte accent + flèche). Texte
/// `AppTypography.itemSupportingBd` (14 / lh 18) et `Icon` 18 px → max = 18.
const double _ctaLinkHeight = 18;

/// Carrousel « How it works » — une carte horizontale par swipe avec story
/// bullets **en dessous** des cartes (vs au-dessus pour [MarketingCardsCarousel]).
///
/// Layout d'une carte : `Row` blanche arrondie, colonne gauche (pill « STEP X »
/// + titre + CTA accent optionnel) et image arrondie à droite (optionnelle).
///
/// Composition stricte sur atomes / composants DS existants :
/// [AppSectionTitle], `_StepPill` (strictement aligné sur la puce `_EnCoursTag`
/// du module STEPS_MODULE — `DecoratedBox` + `Text` avec l'atome textuel
/// [AppTypography.labelEmphasized] = Figma `label/Emphasized SM`, fond
/// [AppColors.progressTrackLight], texte [AppColors.textPrimary]), `_CtaLink`
/// (composition `Row` + `Text`
/// [AppTypography.itemSupportingBd] + `KalaiIcons.arrowRight` (KALAI), pattern
/// repris de `faq_accordion_module.dart` lignes 138–168 et de
/// [SettingsActionButton]), [DsStorySegmentBar], [AppTypography.itemPrimary],
/// [AppColors.cardBackground] / [AppColors.navBarActivePill] / [AppColors.black]
/// / [AppColors.accent], [AppRadius.xl] / [AppRadius.sm], [AppSpacing],
/// [kModuleHorizontalMargin].
class HowItWorksCarousel extends StatefulWidget {
  /// Titre du module (rendu via [AppSectionTitle]) — ex. « How it works ».
  final String title;

  /// Liste des cartes (stepLabel + titre + image optionnelle + CTA optionnel).
  final List<HowItWorksCarouselItem> items;

  const HowItWorksCarousel({
    required this.title,
    required this.items,
    super.key,
  });

  @override
  State<HowItWorksCarousel> createState() => _HowItWorksCarouselState();
}

class _HowItWorksCarouselState extends State<HowItWorksCarousel> {
  /// Scroll horizontal du `ListView` interne. Permet :
  /// 1. au [_CarouselSnapPhysics] de snapper sur des multiples de `stride` ;
  /// 2. de mettre à jour [_pageIndex] (puce de bullets active) en écoutant
  ///    l'offset courant.
  final ScrollController _scrollController = ScrollController();
  int _pageIndex = 0;

  /// Stride (= `cardWidth + cardGap`) calculé au dernier `build`. Sert au
  /// listener du scroll pour mapper offset → index courant. Recalculé à chaque
  /// `build` car dépend de `MediaQuery.sizeOf(context).width`.
  double _builtStride = 0;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_handleScroll);
  }

  @override
  void dispose() {
    _scrollController.removeListener(_handleScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _handleScroll() {
    if (_builtStride <= 0 || widget.items.length <= 1) return;
    final offset = _scrollController.offset;
    final approx = (offset / _builtStride).round();
    final last = widget.items.length - 1;
    final next = approx.clamp(0, last);
    if (next != _pageIndex) {
      setState(() => _pageIndex = next);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.items.isEmpty) {
      return const SizedBox.shrink();
    }

    final multi = widget.items.length > 1;
    final screenWidth = MediaQuery.sizeOf(context).width;
    final last = widget.items.length - 1;

    // ── Géométrie carrousel "carte avec peek" ──
    //
    // Pattern `ListView` full bleed (et NON `PageView` parent-paddé) : un
    // `PageView` posé dans un `Padding(left: margin)` parent imposerait un
    // `Clip.hardEdge` à `margin px` du bord gauche écran, ce qui couperait
    // visuellement les cartes à `margin` pendant le swipe. Avec un `ListView`
    // full bleed + padding INTERNE, le clip est aux bords écran (0 et W) et
    // le scroll est strictement bord à bord.
    //
    // Mathématique du carrousel :
    //   - `cardWidth   = W − 2·margin`
    //   - `cardGap     = 8` (= 1/2 marge)
    //   - `stride      = cardWidth + cardGap` (pas de scroll entre 2 snaps)
    //   - contenu total = `N·cardWidth + (N−1)·cardGap + 2·margin`
    //                   = `(N−1)·stride + cardWidth + 2·margin`
    //                   = `(N−1)·stride + W` ⇒ `maxScrollExtent = (N−1)·stride`
    //
    // Au snap k :
    //   - bord gauche carte k = `margin` (16 px) ✓
    //   - bord droit carte k = `margin + cardWidth = W − margin` ✓
    //   - bord gauche carte k+1 = `W − margin + cardGap` = `W − 8`
    //     ⇒ peek visible = 8 px ✓
    final cardWidth = screenWidth - 2 * _moduleSideMargin;
    final stride = cardWidth + _cardGap;
    _builtStride = stride;

    // Hauteur du carrousel : `max` des hauteurs intrinsèques requises par
    // chaque item (somme des hauteurs des atomes DS internes : padding + tag +
    // titre 2 lignes + CTA si présent). On aligne toutes les cartes sur la
    // plus grande pour éviter tout saut de layout au swipe.
    final cardHeight = _computeMaxCardHeight();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: _moduleSideMargin),
          child: AppSectionTitle(widget.title),
        ),
        const SizedBox(height: AppSpacing.md),
        SizedBox(
          height: cardHeight,
          // `ListView` full bleed (pas de `Padding` parent) → clip natif aux
          // bords écran. Marges écran (16 px) gérées par `padding` INTERNE de
          // ce `ListView`. Snap par carte via [_CarouselSnapPhysics].
          child: ListView.builder(
            controller: _scrollController,
            scrollDirection: Axis.horizontal,
            physics: _CarouselSnapPhysics(stride: stride),
            padding:
                const EdgeInsets.symmetric(horizontal: _moduleSideMargin),
            itemCount: widget.items.length,
            itemBuilder: (context, index) {
              final item = widget.items[index];
              return Container(
                width: cardWidth,
                // Pas de gap après la dernière carte : c'est le padding
                // INTERNE droit du `ListView` (`_moduleSideMargin`) qui crée
                // la marge écran droite au snap final.
                margin: EdgeInsets.only(right: index == last ? 0.0 : _cardGap),
                child: _HowItWorksCard(item: item),
              );
            },
          ),
        ),
        // Story bullets EN DESSOUS du carousel (différence clé vs
        // [MarketingCardsCarousel] qui les place au-dessus). Largeur :
        // - ≤ 6 bullets : `N × (1/6 × (W - 2·margin))`, barre centrée ;
        // - > 6 bullets : auto-fit sur toute la largeur disponible.
        if (multi) ...[
          const SizedBox(height: AppSpacing.md),
          _buildBulletsBar(screenWidth),
        ],
      ],
    );
  }

  /// Calcule la hauteur intrinsèque maximale parmi tous les items, en
  /// additionnant les hauteurs des atomes DS visibles + paddings internes +
  /// gaps. Les items sans titre ou sans CTA donnent une hauteur plus petite,
  /// mais le carrousel utilise le max pour rester stable au swipe.
  double _computeMaxCardHeight() {
    double maxH = 0;
    for (final item in widget.items) {
      final hasTitle = item.title.trim().isNotEmpty;
      final hasCta = item.ctaLabel != null && item.ctaLabel!.trim().isNotEmpty;
      double h = _cardInternalPadding * 2; // top + bottom = 32
      h += _tagHeight; // 25
      if (hasTitle) {
        h += _cardInternalGap; // 12
        h += _cardTitleLineHeight * _cardTitleMaxLines; // 2 × 20 = 40
      }
      if (hasCta) {
        h += _cardInternalGap; // 12
        h += _ctaLinkHeight; // 18
      }
      if (h > maxH) maxH = h;
    }
    return maxH;
  }

  Widget _buildBulletsBar(double screenWidth) {
    final n = widget.items.length;
    final availableWidth = screenWidth - 2 * _moduleSideMargin;
    final maxSegmentWidth = availableWidth / _maxBulletsAtTargetWidth;
    // Si on a peu de bullets (≤ 6), on plafonne la largeur totale à
    // `N × maxSegmentWidth` ; au-delà, on remplit toute la largeur disponible
    // et c'est `Expanded` interne à [DsStorySegmentBar] qui ajuste les segments.
    final barWidth = n <= _maxBulletsAtTargetWidth
        ? n * maxSegmentWidth
        : availableWidth;
    return Center(
      child: SizedBox(
        width: barWidth,
        child: DsStorySegmentBar(
          segmentCount: n,
          activeIndex: _pageIndex,
          variant: DsStorySegmentBarVariant.onSurface,
        ),
      ),
    );
  }
}

/// Carte d'un item du carrousel [HowItWorksCarousel].
///
/// Layout : carte blanche `AppRadius.xl` (20). Padding interne **16 px**
/// uniquement autour du contenu texte. Si [HowItWorksCarouselItem.imageUrl]
/// est non vide, la carte est une `Row` (texte 70 % à gauche, image 30 % à
/// droite). L'image est rendue **full hauteur** de la carte et **collée au
/// bord droit** : son clip est hérité du `ClipRRect` parent (donc les coins
/// haut-droit et bas-droit sont arrondis comme la carte ; les coins gauches
/// sont droits puisque l'image touche la zone texte). Sans image, la colonne
/// texte prend toute la largeur.
class _HowItWorksCard extends StatelessWidget {
  const _HowItWorksCard({required this.item});

  final HowItWorksCarouselItem item;

  @override
  Widget build(BuildContext context) {
    final hasImage = item.imageUrl != null && item.imageUrl!.trim().isNotEmpty;
    final textColumn = _buildTextColumn();

    final card = ClipRRect(
      borderRadius: BorderRadius.circular(AppRadius.xl),
      child: Container(
        decoration: const BoxDecoration(color: AppColors.cardBackground),
        child: hasImage
            ? Row(
                // `stretch` : l'image étend sa hauteur sur toute la carte.
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(
                    flex: ((1 - _imageWidthFraction) * 100).round(),
                    child: Padding(
                      padding: const EdgeInsets.all(_cardInternalPadding),
                      child: textColumn,
                    ),
                  ),
                  Expanded(
                    flex: (_imageWidthFraction * 100).round(),
                    // Pas de padding ni de ClipRRect interne : l'image va
                    // jusqu'au bord droit de la carte ; le clip parent
                    // arrondit déjà les coins haut-droit / bas-droit.
                    child: CachedNetworkImage(
                      imageUrl: item.imageUrl!,
                      fit: BoxFit.cover,
                      placeholder: (_, __) =>
                          Container(color: AppColors.placeholderBg),
                      errorWidget: (_, __, ___) =>
                          Container(color: AppColors.placeholderBg),
                    ),
                  ),
                ],
              )
            : Padding(
                padding: const EdgeInsets.all(_cardInternalPadding),
                child: textColumn,
              ),
      ),
    );

    if (item.onTap == null) return card;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: item.onTap,
        borderRadius: BorderRadius.circular(AppRadius.xl),
        child: card,
      ),
    );
  }

  Widget _buildTextColumn() {
    final hasCta = item.ctaLabel != null && item.ctaLabel!.trim().isNotEmpty;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisAlignment: MainAxisAlignment.center,
      mainAxisSize: MainAxisSize.min,
      children: [
        _StepPill(label: item.stepLabel),
        const SizedBox(height: _cardInternalGap),
        Text(
          item.title,
          style: AppTypography.itemPrimary.copyWith(color: AppColors.black),
          maxLines: _cardTitleMaxLines,
          overflow: TextOverflow.ellipsis,
        ),
        if (hasCta) ...[
          const SizedBox(height: _cardInternalGap),
          _CtaLink(label: item.ctaLabel!, onTap: item.onCtaTap),
        ],
      ],
    );
  }
}

/// Puce d'étape (« STEP 1 », « ÉTAPE 1 », …) du carrousel
/// [HowItWorksCarousel].
///
/// **Strictement alignée** sur la puce `_EnCoursTag` (« EN COURS ») du module
/// `STEPS_MODULE` (`steps_module.dart` lignes 217-239) — mêmes 3 atomes DS,
/// même padding, même radius. Si la puce d'un module change, l'autre doit
/// suivre.
///
/// Atomes DS :
/// - texte → [AppTypography.labelEmphasized] (Figma `label/Emphasized SM`)
/// - couleur texte → [AppColors.textPrimary]
/// - fond → [AppColors.progressTrackLight] (Figma Gray5 fill)
/// - rayon → [AppRadius.sm]
/// - padding → 6 px horizontal / 4 px vertical
class _StepPill extends StatelessWidget {
  const _StepPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: AppColors.progressTrackLight,
        borderRadius: BorderRadius.circular(AppRadius.sm),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: _stepPillPaddingH,
          vertical: _stepPillPaddingV,
        ),
        child: Text(
          label,
          style: AppTypography.labelEmphasized.copyWith(
            color: AppColors.textPrimary,
          ),
        ),
      ),
    );
  }
}

/// Lien d'action « CTA » d'une carte du carrousel [HowItWorksCarousel] :
/// **texte accent + flèche** (vs un bouton plein), à la manière de l'image
/// Figma de référence (« Call to action → »).
///
/// Composition stricte sur atomes DS — pattern repris de
/// `faq_accordion_module.dart` (lignes 138–168, footer link) et de
/// [SettingsActionButton] :
///
/// - texte → [AppTypography.itemSupportingBd] (14 / w600 / lh 18) ;
/// - couleur → [AppColors.accent] (= [AppColors.indigo] = `#6155F5`) ;
/// - icône → `KalaiIcons.arrowRight` (KALAI), taille 18, même couleur ;
/// - gap interne texte ↔ icône → 6 px ;
/// - clic → [InkWell] avec `borderRadius` arrondi `AppRadius.sm` (ripple
///   propre, hit-area `min`).
class _CtaLink extends StatelessWidget {
  const _CtaLink({required this.label, this.onTap});

  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final row = Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Text(
          label,
          style: AppTypography.itemSupportingBd.copyWith(
            color: AppColors.accent,
          ),
        ),
        const SizedBox(width: 6),
        const KalaiIcon(
          KalaiIcons.arrowRight,
          size: 18,
          color: AppColors.accent,
        ),
      ],
    );
    if (onTap == null) return row;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppRadius.sm),
      child: row,
    );
  }
}

/// `ScrollPhysics` custom : snap par carte (`stride = cardWidth + cardGap`)
/// pour le `ListView` horizontal du carrousel [HowItWorksCarousel].
///
/// Pourquoi pas `PageScrollPhysics` natif : il snap par viewport entier
/// (largeur écran), pas par stride d'une carte. Pour un carrousel à peek
/// (carte ≠ viewport), il faut un snap personnalisé.
///
/// Comportement :
/// - Vélocité < tolerance : snap sur l'index le plus proche (round)
/// - Vélocité forte (gauche/droite) : snap au moins d'un index dans le sens
///   du geste (bias ±0.5 sur la division floue)
/// - L'offset cible est clampé à `[minScrollExtent, maxScrollExtent]` ;
///   `maxScrollExtent` valant exactement `(N−1)·stride`, le snap final
///   aligne précisément la dernière carte sur la marge gauche écran.
class _CarouselSnapPhysics extends ScrollPhysics {
  const _CarouselSnapPhysics({required this.stride, super.parent});

  final double stride;

  @override
  _CarouselSnapPhysics applyTo(ScrollPhysics? ancestor) {
    return _CarouselSnapPhysics(stride: stride, parent: buildParent(ancestor));
  }

  double _targetPixels(ScrollMetrics position, Tolerance tolerance, double velocity) {
    if (stride <= 0) return position.pixels;
    double page = position.pixels / stride;
    if (velocity < -tolerance.velocity) {
      page -= 0.5;
    } else if (velocity > tolerance.velocity) {
      page += 0.5;
    }
    final target = page.roundToDouble() * stride;
    return target.clamp(position.minScrollExtent, position.maxScrollExtent);
  }

  @override
  Simulation? createBallisticSimulation(ScrollMetrics position, double velocity) {
    // Hors range : laisser le parent gérer le rebond (overscroll iOS, …).
    if ((velocity <= 0.0 && position.pixels <= position.minScrollExtent) ||
        (velocity >= 0.0 && position.pixels >= position.maxScrollExtent)) {
      return super.createBallisticSimulation(position, velocity);
    }
    final tolerance = toleranceFor(position);
    final target = _targetPixels(position, tolerance, velocity);
    if (target == position.pixels) return null;
    return ScrollSpringSimulation(
      spring,
      position.pixels,
      target,
      velocity,
      tolerance: tolerance,
    );
  }

  /// Indispensable pour que le snap reste « pageable » (1 swipe = 1 carte
  /// max), même avec un long flick — sinon on saute plusieurs cartes.
  @override
  bool get allowImplicitScrolling => false;
}
