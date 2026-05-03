import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../data/academy_api.dart';
import '../../domain/models/academy_center_models.dart';
import 'academy_articles_screen.dart';
import 'academy_widgets.dart';

class AcademyCategoriesScreen extends StatefulWidget {
  const AcademyCategoriesScreen({
    super.key,
    required this.collectionSlug,
    required this.collectionTitle,
  });

  final String collectionSlug;
  final String collectionTitle;

  @override
  State<AcademyCategoriesScreen> createState() => _AcademyCategoriesScreenState();
}

class _AcademyCategoriesScreenState extends State<AcademyCategoriesScreen> {
  final AcademyApi _api = AcademyApi();
  final TextEditingController _searchController = TextEditingController();
  bool _loading = true;
  String? _error;
  List<AcademyCategoryItem> _categories = const [];

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
      final response =
          await _api.getCategories(collectionSlug: widget.collectionSlug);
      if (!mounted) return;
      setState(() {
        _categories = response.categories;
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

  List<AcademyCategoryItem> get _filtered {
    final q = _searchController.text.trim().toLowerCase();
    if (q.isEmpty) return _categories;
    return _categories.where((item) {
      final base =
          '${item.title} ${item.description ?? ''}'.toLowerCase();
      return base.contains(q);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return PageSimpleNavBarTopTitlePageContent(
      pageTitle: widget.collectionTitle,
      onBackTap: () => Navigator.of(context).pop(),
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
      return SizedBox(
        height: 220,
        child: Center(
          child: Text(
            _error!,
            style: AppTypography.bodyMedium
                .copyWith(color: AppColors.errorText),
          ),
        ),
      );
    }
    return AcademyChevronCardList(
      items: _filtered
          .map(
            (c) => AcademyChevronCardItem(
              title: c.title,
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => AcademyArticlesScreen(
                      collectionSlug: widget.collectionSlug,
                      collectionTitle: widget.collectionTitle,
                      categorySlug: c.slug,
                      categoryTitle: c.title,
                    ),
                  ),
                );
              },
            ),
          )
          .toList(),
    );
  }
}
