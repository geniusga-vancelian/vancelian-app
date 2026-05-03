import 'dart:async';

import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../../news/presentation/screens/article_detail_screen.dart';
import '../../data/help_api.dart';
import '../../domain/models/help_center_models.dart';
import 'help_widgets.dart';

/// Titres de collection sur fond page, cartes blanches [ListCardModule] par groupe.
class HelpSearchGroupedArticleList extends StatelessWidget {
  const HelpSearchGroupedArticleList({
    super.key,
    required this.results,
    required this.onArticleTap,
  });

  final List<HelpSearchResultItem> results;
  final void Function(HelpSearchResultItem hit) onArticleTap;

  @override
  Widget build(BuildContext context) {
    final order = <String>[];
    final bySlug = <String, List<HelpSearchResultItem>>{};
    for (final r in results) {
      bySlug.putIfAbsent(r.collectionSlug, () {
        order.add(r.collectionSlug);
        return <HelpSearchResultItem>[];
      });
      bySlug[r.collectionSlug]!.add(r);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var i = 0; i < order.length; i++) ...[
          if (i > 0) const SizedBox(height: AppSpacing.lg),
          Padding(
            padding: const EdgeInsets.only(
              left: AppSpacing.xs,
              bottom: AppSpacing.sm,
            ),
            child: Text(
              bySlug[order[i]]!.first.collectionTitle,
              style: AppTypography.sectionTitle.copyWith(
                color: AppColors.textPrimary,
              ),
            ),
          ),
          ListCardModule(
            items: bySlug[order[i]]!
                .map(
                  (r) => ListCardItem(
                    title: r.question,
                    showChevron: true,
                    onTap: () => onArticleTap(r),
                  ),
                )
                .toList(),
          ),
        ],
      ],
    );
  }
}

/// Panneau de recherche Help : pas de shimmer ; résultats précédents conservés
/// tant que la nouvelle requête n’a pas répondu ; [ListCard] titre + chevron.
///
/// Le corps « normal » reste affiché tant que le champ est vide (même focus).
/// Dès la première lettre : fondu rapide vers le panneau recherche ; si tout est
/// effacé avec le focus conservé : fondu vers le corps initial.
///
/// Données : [HelpApi.searchHelpArticles] → `/api/help/search` (voir [minChars]).
class HelpDualSearchBody extends StatefulWidget {
  const HelpDualSearchBody({
    super.key,
    required this.controller,
    required this.focusNode,
    required this.helpApi,
    required this.normalBody,
    this.collectionSlug,
    this.categorySlug,
    this.minChars = 3,
    this.debounceMs = 280,
  });

  final TextEditingController controller;
  final FocusNode focusNode;
  final HelpApi helpApi;
  final Widget normalBody;
  final String? collectionSlug;
  final String? categorySlug;
  final int minChars;
  final int debounceMs;

  @override
  State<HelpDualSearchBody> createState() => _HelpDualSearchBodyState();
}

class _HelpDualSearchBodyState extends State<HelpDualSearchBody> {
  static const Duration _fadeInSmooth = Duration(milliseconds: 125);
  static const Duration _fadeOutFast = Duration(milliseconds: 85);

  Timer? _debounce;
  bool _searchRequestPending = false;
  String? _error;
  List<HelpSearchResultItem> _results = const [];

  /// Affiche le panneau recherche (et masque le corps liste) seulement après
  /// au moins un caractère — le focus seul ne remplace pas le contenu.
  bool get _searchUiVisible => widget.controller.text.trim().isNotEmpty;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onQueryChanged);
    widget.focusNode.addListener(_onFocusChanged);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onQueryChanged);
    widget.focusNode.removeListener(_onFocusChanged);
    _debounce?.cancel();
    super.dispose();
  }

  void _clearSearchState() {
    _debounce?.cancel();
    _searchRequestPending = false;
    _error = null;
    _results = const [];
  }

  void _onFocusChanged() {
    if (!_searchUiVisible) {
      _clearSearchState();
    }
    setState(() {});
  }

  void _onQueryChanged() {
    _debounce?.cancel();
    if (!_searchUiVisible) {
      _clearSearchState();
      setState(() {});
      return;
    }
    final q = widget.controller.text.trim();
    if (q.length < widget.minChars) {
      _clearSearchState();
      setState(() {});
      return;
    }
    setState(() {});
    _debounce = Timer(Duration(milliseconds: widget.debounceMs), () {
      _runSearch(q);
    });
  }

  Future<void> _runSearch(String q) async {
    if (!mounted) return;
    setState(() {
      _searchRequestPending = true;
      _error = null;
    });
    try {
      final list = await widget.helpApi.searchHelpArticles(
        query: q,
        collectionSlug: widget.collectionSlug,
        categorySlug: widget.categorySlug,
      );
      if (!mounted || widget.controller.text.trim() != q) return;
      setState(() {
        _searchRequestPending = false;
        _results = list;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _searchRequestPending = false;
        _error = e.toString();
        _results = const [];
      });
    }
  }

  Widget _buildOverlayPane(BuildContext context) {
    final q = widget.controller.text.trim();
    if (q.length < widget.minChars) {
      return const SizedBox.shrink();
    }

    if (_error != null &&
        !_searchRequestPending &&
        _results.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.xl),
        child: Text(
          _error!,
          style:
              AppTypography.bodyMedium.copyWith(color: AppColors.errorText),
        ),
      );
    }

    // Pas de shimmer : pendant la requête on garde l’affichage précédent ; premier
    // chargement → zone vide jusqu’à la réponse.
    if (_searchRequestPending && _results.isEmpty) {
      return const SizedBox.shrink();
    }

    if (!_searchRequestPending && _results.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: AppSpacing.xxl),
        child: HelpEmptyResults(),
      );
    }

    return HelpSearchGroupedArticleList(
      results: _results,
      onArticleTap: (hit) {
        Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => ArticleDetailScreen.help(
              collectionSlug: hit.collectionSlug,
              categorySlug: hit.categorySlug,
              articleSlug: hit.slug,
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final searchOn = _searchUiVisible;
    return Stack(
      alignment: Alignment.topCenter,
      clipBehavior: Clip.none,
      children: [
        IgnorePointer(
          ignoring: searchOn,
          child: AnimatedOpacity(
            opacity: searchOn ? 0.0 : 1.0,
            duration: searchOn ? _fadeOutFast : _fadeInSmooth,
            curve: searchOn ? Curves.easeIn : Curves.easeOut,
            child: widget.normalBody,
          ),
        ),
        IgnorePointer(
          ignoring: !searchOn,
          child: AnimatedOpacity(
            opacity: searchOn ? 1.0 : 0.0,
            duration: searchOn ? _fadeInSmooth : _fadeOutFast,
            curve: searchOn ? Curves.easeOut : Curves.easeIn,
            child: _buildOverlayPane(context),
          ),
        ),
      ],
    );
  }
}
