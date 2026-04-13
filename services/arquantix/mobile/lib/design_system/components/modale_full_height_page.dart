import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'app_page_title.dart';
import 'app_top_nav_bar.dart';

/// Modale full-height avec comportement de page standard:
/// - top navbar DS
/// - bouton "Fermer" à gauche
/// - contenu libre dans le body.
class ModaleFullHeightPage extends StatefulWidget {
  const ModaleFullHeightPage({
    super.key,
    required this.child,
    this.title,
    this.onCloseTap,
    this.closeLabel = 'Fermer',
    this.actions = const [],
    this.horizontalPadding = const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
    this.contentBottomPadding = AppSpacing.xxl,
    this.titleToContentSpacing = AppSpacing.md,
    this.fadeStartOffset = 24,
    this.fadeEndOffset = 64,
    this.navBarTitleTextStyle,
    this.contentInWhiteModule = false,
    this.contentModulePadding = const EdgeInsets.all(AppSpacing.lg),
    this.contentModuleRadius = 24,
  });

  final Widget child;
  final String? title;
  final VoidCallback? onCloseTap;
  final String closeLabel;
  final List<AppTopNavBarAction> actions;
  final EdgeInsets horizontalPadding;
  final double contentBottomPadding;
  final double titleToContentSpacing;
  final double fadeStartOffset;
  final double fadeEndOffset;
  final TextStyle? navBarTitleTextStyle;
  final bool contentInWhiteModule;
  final EdgeInsets contentModulePadding;
  final double contentModuleRadius;

  static Future<T?> show<T>(
    BuildContext context, {
    required Widget child,
    String? title,
    VoidCallback? onCloseTap,
    String closeLabel = 'Fermer',
    List<AppTopNavBarAction> actions = const [],
    bool contentInWhiteModule = false,
    EdgeInsets contentModulePadding = const EdgeInsets.all(AppSpacing.lg),
    double contentModuleRadius = 24,
  }) {
    return showGeneralDialog<T>(
      context: context,
      barrierDismissible: true,
      barrierLabel: closeLabel,
      barrierColor: Colors.black.withValues(alpha: 0.5),
      transitionDuration: const Duration(milliseconds: 260),
      pageBuilder: (context, animation, secondaryAnimation) {
        return ModaleFullHeightPage(
          title: title,
          onCloseTap: onCloseTap,
          closeLabel: closeLabel,
          actions: actions,
          contentInWhiteModule: contentInWhiteModule,
          contentModulePadding: contentModulePadding,
          contentModuleRadius: contentModuleRadius,
          child: child,
        );
      },
      transitionBuilder: (context, animation, secondaryAnimation, dialogChild) {
        final curved = CurvedAnimation(
          parent: animation,
          curve: Curves.easeOutCubic,
          reverseCurve: Curves.easeInCubic,
        );
        return SlideTransition(
          position: Tween<Offset>(
            begin: const Offset(0, 1),
            end: Offset.zero,
          ).animate(curved),
          child: dialogChild,
        );
      },
    );
  }

  @override
  State<ModaleFullHeightPage> createState() => _ModaleFullHeightPageState();
}

class _ModaleFullHeightPageState extends State<ModaleFullHeightPage> {
  final ScrollController _scrollController = ScrollController();
  double _navTitleOpacity = 0;
  double _dragOffset = 0;
  bool _isDraggingToDismiss = false;
  static const double _dismissThreshold = 120;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    final offset = _scrollController.hasClients ? _scrollController.offset : 0.0;
    final next = ((offset - widget.fadeStartOffset) /
            (widget.fadeEndOffset - widget.fadeStartOffset))
        .clamp(0.0, 1.0);
    if ((next - _navTitleOpacity).abs() > 0.02) {
      setState(() => _navTitleOpacity = next);
    }
  }

  bool _handleScrollNotification(ScrollNotification notification) {
    final atTop =
        notification.metrics.pixels <= notification.metrics.minScrollExtent + 0.5;

    if (notification is OverscrollNotification &&
        atTop &&
        notification.overscroll < 0) {
      // Pull-down sur contenu en haut: on "rabaisse" la modale.
      final next = (_dragOffset + (-notification.overscroll)).clamp(0.0, 220.0);
      if ((next - _dragOffset).abs() > 0.5) {
        setState(() {
          _dragOffset = next;
          _isDraggingToDismiss = true;
        });
      }
      return true;
    }

    if (notification is ScrollEndNotification && _dragOffset > 0) {
      if (_dragOffset >= _dismissThreshold) {
        Navigator.of(context).pop();
      } else {
        setState(() {
          _dragOffset = 0;
          _isDraggingToDismiss = false;
        });
      }
      return true;
    }

    if (!atTop && _dragOffset > 0) {
      setState(() {
        _dragOffset = 0;
        _isDraggingToDismiss = false;
      });
    }
    return false;
  }

  @override
  Widget build(BuildContext context) {
    final hasTitle = (widget.title ?? '').trim().isNotEmpty;
    final content = widget.contentInWhiteModule
        ? Container(
            decoration: BoxDecoration(
              color: AppColors.cardBackground,
              borderRadius: BorderRadius.circular(widget.contentModuleRadius),
              boxShadow: [
                BoxShadow(
                  color: AppColors.textPrimary.withValues(alpha: 0.06),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            padding: widget.contentModulePadding,
            child: widget.child,
          )
        : widget.child;
    return Transform.translate(
      offset: Offset(0, _dragOffset),
      child: Scaffold(
        backgroundColor: AppColors.pageBackground,
        appBar: AppTopNavBar(
          leadingType: AppTopNavBarLeading.close,
          onCloseTap: widget.onCloseTap,
          closeLabel: widget.closeLabel,
          title: hasTitle ? widget.title : null,
          centerTitle: false,
          actions: widget.actions,
          titleTextStyle: widget.navBarTitleTextStyle ??
              AppTypography.paragraph.copyWith(
                color: AppColors.textPrimary,
                fontSize: 15,
                fontWeight: FontWeight.w600,
              ),
          titleOpacity: hasTitle ? _navTitleOpacity : 0,
        ),
        body: SafeArea(
          top: false,
          child: Padding(
            padding: widget.horizontalPadding,
            child: NotificationListener<ScrollNotification>(
              onNotification: _handleScrollNotification,
              child: ListView(
                controller: _scrollController,
                physics: const BouncingScrollPhysics(
                  parent: AlwaysScrollableScrollPhysics(),
                ),
                padding: EdgeInsets.only(bottom: widget.contentBottomPadding),
                children: [
                  const SizedBox(height: AppSpacing.md),
                  if (hasTitle) ...[
                    AppPageTitle(widget.title!),
                    SizedBox(height: widget.titleToContentSpacing),
                  ],
                  content,
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
