import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

class NewsTransactionsListItem {
  const NewsTransactionsListItem({
    required this.title,
    required this.dateLabel,
    required this.authorName,
    this.tags = const [],
    this.onTap,
  });

  final String title;
  final String dateLabel;
  final String authorName;
  final List<String> tags;
  final VoidCallback? onTap;
}

/// Module DS « News Card » — carte blanche avec onglets pilule + articles.
///
/// Reproduit le composant Figma : barre d'onglets intégrée dans la carte,
/// articles avec titre (max 2 lignes) + métadonnées (date | auteur).
class NewsTransactionsListModule extends StatefulWidget {
  const NewsTransactionsListModule({
    super.key,
    required this.items,
    this.title,
    this.description,
    this.maxItems = 10,
  });

  final List<NewsTransactionsListItem> items;
  final String? title;
  final String? description;
  final int maxItems;

  @override
  State<NewsTransactionsListModule> createState() =>
      _NewsTransactionsListModuleState();
}

class _NewsTransactionsListModuleState
    extends State<NewsTransactionsListModule> {
  static const String _allTag = '__all__';
  String _selectedTag = _allTag;

  List<_TagOption> _buildTagOptions() {
    final labels = <String>{};
    for (final item in widget.items) {
      for (final tag in item.tags) {
        final normalized = tag.trim();
        if (normalized.isNotEmpty) labels.add(normalized);
      }
    }
    final sorted = labels.toList()..sort((a, b) => a.compareTo(b));
    return [
      const _TagOption(id: _allTag, label: 'Tous'),
      ...sorted.map((tag) => _TagOption(id: tag, label: tag)),
    ];
  }

  List<NewsTransactionsListItem> _filteredItems(List<_TagOption> options) {
    final effectiveMax = widget.maxItems.clamp(1, 10);
    if (_selectedTag == _allTag) {
      return widget.items.take(effectiveMax).toList(growable: false);
    }
    final selectedExists = options.any((o) => o.id == _selectedTag);
    if (!selectedExists) {
      return widget.items.take(effectiveMax).toList(growable: false);
    }
    return widget.items
        .where((item) => item.tags.any((tag) => tag.trim() == _selectedTag))
        .take(effectiveMax)
        .toList(growable: false);
  }

  @override
  Widget build(BuildContext context) {
    if (widget.items.isEmpty) return const SizedBox.shrink();

    final hasTitle = (widget.title ?? '').trim().isNotEmpty;
    final hasDescription = (widget.description ?? '').trim().isNotEmpty;
    final tagOptions = _buildTagOptions();
    final visibleItems = _filteredItems(tagOptions);
    final showTabs = tagOptions.length > 1;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (hasTitle) ...[
          Padding(
            padding:
                const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
            child: Text(
              widget.title!.trim(),
              style: AppTypography.titleLarge.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          if (hasDescription) ...[
            const SizedBox(height: AppSpacing.xs),
            Padding(
              padding:
                  const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
              child: Text(
                widget.description!.trim(),
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ),
          ],
          const SizedBox(height: AppSpacing.md),
        ],
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: Container(
            decoration: BoxDecoration(
              color: AppColors.cardBackground,
              borderRadius: BorderRadius.circular(16),
              boxShadow: const [
                BoxShadow(
                  color: Color(0x1F000000),
                  blurRadius: 20,
                  spreadRadius: -10,
                ),
              ],
            ),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (showTabs) ...[
                    _PillTabBar(
                      options: tagOptions,
                      selectedId: _selectedTag,
                      onChanged: (id) => setState(() => _selectedTag = id),
                    ),
                    const SizedBox(height: 16),
                  ],
                  for (var i = 0; i < visibleItems.length; i++) ...[
                    _NewsLineItem(item: visibleItems[i]),
                    if (i < visibleItems.length - 1)
                      const SizedBox(height: 16),
                  ],
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

// ─────────────── Pill Tab Bar (sliding animation) ───────────────

class _PillTabBar extends StatefulWidget {
  const _PillTabBar({
    required this.options,
    required this.selectedId,
    required this.onChanged,
  });

  final List<_TagOption> options;
  final String selectedId;
  final ValueChanged<String> onChanged;

  @override
  State<_PillTabBar> createState() => _PillTabBarState();
}

class _PillTabBarState extends State<_PillTabBar> {
  static const double _height = 32;
  static const double _outerPad = 2;
  static const double _innerH = _height - _outerPad * 2;
  static const double _pillHPad = 12;
  static const double _pillRadius = 9999;

  static const _labelStyle = TextStyle(
    fontFamily: 'Inter',
    fontSize: 13,
    fontWeight: FontWeight.w600,
    letterSpacing: -0.08,
    height: 1.0,
  );

  final List<GlobalKey> _keys = [];
  final Map<int, _TabMetrics> _metrics = {};

  @override
  void initState() {
    super.initState();
    _syncKeys();
    WidgetsBinding.instance.addPostFrameCallback((_) => _measure());
  }

  @override
  void didUpdateWidget(covariant _PillTabBar old) {
    super.didUpdateWidget(old);
    if (old.options.length != widget.options.length) {
      _syncKeys();
      WidgetsBinding.instance.addPostFrameCallback((_) => _measure());
    }
  }

  void _syncKeys() {
    while (_keys.length < widget.options.length) {
      _keys.add(GlobalKey());
    }
  }

  void _measure() {
    final parentBox = context.findRenderObject() as RenderBox?;
    if (parentBox == null) return;
    final parentOffset = parentBox.localToGlobal(Offset.zero);

    for (var i = 0; i < widget.options.length; i++) {
      final box =
          _keys[i].currentContext?.findRenderObject() as RenderBox?;
      if (box == null) continue;
      final pos = box.localToGlobal(Offset.zero);
      _metrics[i] = _TabMetrics(
        left: pos.dx - parentOffset.dx,
        width: box.size.width,
      );
    }
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final selectedIdx = widget.options
        .indexWhere((o) => o.id == widget.selectedId)
        .clamp(0, widget.options.length - 1);

    final activeMetrics = _metrics[selectedIdx];

    return Container(
      height: _height,
      decoration: BoxDecoration(
        color: const Color(0xFFF2F2F7),
        borderRadius: BorderRadius.circular(_pillRadius),
      ),
      padding: const EdgeInsets.all(_outerPad),
      child: Stack(
        children: [
          if (activeMetrics != null)
            AnimatedPositioned(
              duration: const Duration(milliseconds: 250),
              curve: Curves.easeInOut,
              left: activeMetrics.left - _outerPad,
              width: activeMetrics.width,
              top: 0,
              bottom: 0,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(_pillRadius),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0x0D000000),
                      blurRadius: 4,
                      offset: Offset(0, 1),
                    ),
                  ],
                ),
              ),
            ),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                for (var i = 0; i < widget.options.length; i++)
                  GestureDetector(
                    key: _keys[i],
                    onTap: () {
                      widget.onChanged(widget.options[i].id);
                      WidgetsBinding.instance
                          .addPostFrameCallback((_) => _measure());
                    },
                    behavior: HitTestBehavior.opaque,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: _pillHPad,
                        vertical: 0,
                      ),
                      child: SizedBox(
                        height: _innerH,
                        child: Center(
                          child: TweenAnimationBuilder<Color?>(
                            tween: ColorTween(
                              end: i == selectedIdx
                                  ? AppColors.textPrimary
                                  : const Color(0xFF8E8E93),
                            ),
                            duration: const Duration(milliseconds: 250),
                            curve: Curves.easeInOut,
                            builder: (_, color, __) => Text(
                              widget.options[i].label,
                              style: _labelStyle.copyWith(color: color),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TabMetrics {
  const _TabMetrics({required this.left, required this.width});
  final double left;
  final double width;
}

// ─────────────── Article Row ───────────────

class _NewsLineItem extends StatelessWidget {
  const _NewsLineItem({required this.item});

  final NewsTransactionsListItem item;

  @override
  Widget build(BuildContext context) {
    final child = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          item.title,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: AppTypography.itemPrimary.copyWith(
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Text(
              item.dateLabel,
              style: AppTypography.itemSupporting.copyWith(
                color: const Color(0xFF8E8E93),
              ),
            ),
            const SizedBox(width: 4),
            SizedBox(
              width: 1,
              height: 12,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.12),
                ),
              ),
            ),
            const SizedBox(width: 4),
            Expanded(
              child: Text(
                item.authorName,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: AppTypography.itemSupporting.copyWith(
                  color: const Color(0xFF8E8E93),
                ),
              ),
            ),
          ],
        ),
      ],
    );

    if (item.onTap == null) return child;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: item.onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 2),
          child: child,
        ),
      ),
    );
  }
}

class _TagOption {
  const _TagOption({required this.id, required this.label});

  final String id;
  final String label;
}
