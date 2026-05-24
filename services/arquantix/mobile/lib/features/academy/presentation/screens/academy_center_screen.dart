import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../data/academy_api.dart';
import '../../domain/models/academy_center_models.dart';
import 'academy_categories_screen.dart';
import 'academy_widgets.dart';

/// Écran d'entrée du module Academy : liste des collections publiées.
/// Symétrique à [HelpCenterScreen] mais avec un set d'icônes orienté
/// pédagogie (school, library, lightbulb…).
class AcademyCenterScreen extends StatefulWidget {
  const AcademyCenterScreen({super.key, this.onBack});

  final VoidCallback? onBack;

  @override
  State<AcademyCenterScreen> createState() => _AcademyCenterScreenState();
}

class _AcademyCenterScreenState extends State<AcademyCenterScreen> {
  final AcademyApi _api = AcademyApi();
  final TextEditingController _searchController = TextEditingController();
  bool _loading = true;
  String? _error;
  List<AcademyCollectionItem> _collections = const [];

  @override
  void initState() {
    super.initState();
    _load();
    _searchController.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final collections = await _api.getCollections();
      if (!mounted) return;
      setState(() {
        _collections = collections;
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

  List<AcademyCollectionItem> get _filtered {
    final q = _searchController.text.trim().toLowerCase();
    if (q.isEmpty) return _collections;
    return _collections.where((item) {
      final base =
          '${item.title} ${item.subtitle ?? ''} ${item.description ?? ''}'
              .toLowerCase();
      return base.contains(q);
    }).toList();
  }

  /// Mapping `iconKey` → `IconData` orienté **pédagogie / academy**.
  /// Si l'icône n'est pas reconnue, fallback sur le slug puis sur
  /// `Icons.school_outlined` (cohérent avec le défaut côté admin/backend).
  IconData _iconForCollection(AcademyCollectionItem item) {
    final iconKey = (item.iconKey ?? '').trim().toLowerCase();
    switch (iconKey) {
      case 'school':
      case 'academy':
      case 'graduation':
      case 'graduation-cap':
        return Icons.school_rounded;
      case 'library':
      case 'book':
      case 'books':
        return Icons.library_books_rounded;
      case 'lightbulb':
      case 'idea':
        return Icons.lightbulb_outline_rounded;
      case 'play':
      case 'video':
        return Icons.play_circle_outline_rounded;
      case 'compass':
      case 'guide':
        return Icons.explore_outlined;
      case 'trending-up':
      case 'investment':
        return Icons.trending_up_rounded;
      case 'shield':
      case 'security':
        return Icons.shield_rounded;
      case 'help-circle':
      case 'help':
        return Icons.help_outline_rounded;
      case 'article':
      case 'file-text':
        return Icons.article_outlined;
      default:
        final normalized = item.slug.toLowerCase();
        if (normalized.contains('debut') ||
            normalized.contains('start') ||
            normalized.contains('basics')) {
          return Icons.school_rounded;
        }
        if (normalized.contains('crypto') ||
            normalized.contains('blockchain')) {
          return Icons.currency_bitcoin_rounded;
        }
        if (normalized.contains('strateg') ||
            normalized.contains('expert')) {
          return Icons.auto_graph_rounded;
        }
        if (normalized.contains('invest')) {
          return Icons.trending_up_rounded;
        }
        return Icons.school_outlined;
    }
  }

  @override
  Widget build(BuildContext context) {
    return PageSimpleNavBarTopTitlePageContent(
      pageTitle: 'Academy',
      onBackTap: widget.onBack,
      onRefresh: _load,
      content: [
        AcademySearchBar(controller: _searchController),
        const SizedBox(height: AppSpacing.xxl),
        _buildBody(),
      ],
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const SizedBox(
        height: 220,
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (_error != null) {
      return _buildError(_error!);
    }
    return AcademyChevronCardList(
      items: _filtered
          .map(
            (item) => AcademyChevronCardItem(
              title: item.title,
              leadingIcon: _iconForCollection(item),
              leadingBackgroundColor:
                  AppColors.textPrimary.withValues(alpha: 0.06),
              leadingIconColor: AppColors.textPrimary,
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => AcademyCategoriesScreen(
                      collectionSlug: item.slug,
                      collectionTitle: item.title,
                    ),
                  ),
                );
              },
            ),
          )
          .toList(),
    );
  }

  Widget _buildError(String msg) {
    return SizedBox(
      height: 220,
      child: Center(
        child: Text(
          msg,
          style:
              AppTypography.bodyMedium.copyWith(color: AppColors.errorText),
        ),
      ),
    );
  }
}
