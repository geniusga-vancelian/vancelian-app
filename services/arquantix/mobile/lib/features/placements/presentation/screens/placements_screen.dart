import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../design_system/design_system.dart';
import '../../../../ui/components/line_chart_module.dart';
import '../../../offers/data/offers_repository.dart';
import '../../../offers/domain/models/offer_project.dart';
import '../../../offers/presentation/screens/offers_screen.dart';
import '../../data/placements_api.dart';
import '../../domain/models/placement_position.dart';
import 'placement_detail_screen.dart';

class PlacementsScreen extends StatefulWidget {
  const PlacementsScreen({super.key});

  @override
  State<PlacementsScreen> createState() => _PlacementsScreenState();
}

class _PlacementsScreenState extends State<PlacementsScreen> {
  final PlacementsApi _api = const PlacementsApi();
  final OffersRepository _offersRepo = OffersRepository();

  PlacementsData? _earnData;
  List<PlacementPosition> _positions = [];
  bool _isLoading = true;
  String? _loadError;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load({bool forceRefresh = false}) async {
    setState(() {
      _isLoading = true;
      _loadError = null;
    });
    try {
      final results = await Future.wait([
        _api.fetchEarnPositions(),
        _offersRepo.getProjects(),
      ]);
      if (!mounted) return;
      final earn = results[0] as PlacementsData;
      final projects = results[1] as List<OfferProject>;
      setState(() {
        _earnData = earn;
        _positions = _buildPositions(earn, projects);
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _loadError = 'Impossible de charger les placements';
      });
    }
  }

  List<PlacementPosition> _buildPositions(
    PlacementsData earn,
    List<OfferProject> projects,
  ) {
    final result = <PlacementPosition>[];
    final projectById = <String, OfferProject>{};
    for (final project in projects) {
      projectById[project.id] = project;
    }

    for (final earnPos in earn.positions) {
      final pid = earnPos.projectId;
      if (pid == null || pid.isEmpty) {
        // Fallback: position sans project_id → affichage générique
        result.add(PlacementPosition(
          projectId: earnPos.asset,
          poolId: earnPos.poolId,
          lendingPoolProductId: earnPos.lendingPoolProductId,
          projectTitle: earnPos.asset,
          projectCategory: '',
          lendingAsset: earnPos.asset.toUpperCase(),
          totalSupplied: earnPos.totalSupplied,
          accruedInterest: earnPos.accruedInterest,
          totalValue: earnPos.totalValue,
          valueEur: earnPos.valueEur,
          apy: earnPos.apy,
          status: 'active',
        ));
        continue;
      }

      final project = projectById[pid];
      result.add(PlacementPosition(
        projectId: pid,
        poolId: earnPos.poolId,
        lendingPoolProductId: earnPos.lendingPoolProductId,
        projectTitle: project?.title ?? earnPos.asset,
        projectCategory: project?.category ?? '',
        projectImageUrl: project?.imageUrl,
        lendingAsset: earnPos.asset.toUpperCase(),
        totalSupplied: earnPos.totalSupplied,
        accruedInterest: earnPos.accruedInterest,
        totalValue: earnPos.totalValue,
        valueEur: earnPos.valueEur,
        apy: project?.apy ?? earnPos.apy,
        status: project?.lendingStatus ?? 'active',
        durationMonths: project?.durationMonths,
        raised: project?.raised,
        target: project?.target,
        investorsCount: project?.investorsCount,
        progress: project?.progress,
      ));
    }

    result.sort((a, b) => b.valueEur.compareTo(a.valueEur));
    return result;
  }

  static final _eurFormatter = NumberFormat.currency(
    locale: 'fr_FR',
    symbol: '€',
    decimalDigits: 2,
  );

  @override
  Widget build(BuildContext context) {
    if (_isLoading) return const _PlacementsShimmer();

    if (_loadError != null) {
      return Scaffold(
        backgroundColor: AppColors.pageBackground,
        appBar: AppBar(
          title: const Text('Placements'),
          backgroundColor: const Color(0xFF0A2E1A),
          foregroundColor: Colors.white,
        ),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline,
                  size: 48, color: Colors.grey),
              const SizedBox(height: AppSpacing.md),
              Text(_loadError!, style: AppTypography.bodyMedium),
              const SizedBox(height: AppSpacing.lg),
              ElevatedButton(
                  onPressed: _load, child: const Text('Réessayer'),
              ),
            ],
          ),
        ),
      );
    }

    return _buildPage();
  }

  Widget _buildPage() {
    final totalValue = _earnData?.totalValueEur ?? 0;
    final totalLabel = _eurFormatter.format(totalValue);
    final countLabel = _positions.isEmpty
        ? 'Aucun placement'
        : '${_positions.length} placement${_positions.length > 1 ? 's' : ''}';

    final List<Widget> contentModules = [];

    if (_positions.isEmpty) {
      contentModules.add(_buildEmptyState());
    } else {
      contentModules.add(
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: TransactionListCard(
            items: _positions.map(_buildPositionItem).toList(),
          ),
        ),
      );
    }

    return LayoutPageLevel1(
      heroFallbackColor: const Color(0xFF0A2E1A),
      heroOverlay: const HeroOverlayConfig(
        tintOpacity: 0,
        gradientStartOpacity: 0.60,
        gradientEndOpacity: 0,
      ),
      title: 'Placements',
      subtitle: totalLabel,
      subtitleStyle: AppTypography.heroAmount.copyWith(color: Colors.white),
      heroActions: Text(
        countLabel,
        style: AppTypography.bodySmall.copyWith(color: Colors.white70),
        textAlign: TextAlign.center,
      ),
      heroFullBleed: LineChartModule(
        data: _buildPortfolioSparkline(),
        height: 80,
        lineColor: Colors.white,
      ),
      heroActionsBelowFullBleed: CircleButtonRow(
        items: const [
          CircleButtonItem(
            icon: Icons.add_rounded,
            label: 'Investir',
            isPrimary: true,
          ),
          CircleButtonItem(
            icon: Icons.savings_rounded,
            label: 'Épargner',
          ),
          CircleButtonItem(
            icon: Icons.bar_chart_rounded,
            label: 'Statistiques',
          ),
        ],
      ),
      leadingType: AppTopNavBarLeading.back,
      onLeadingTap: () => Navigator.of(context).pop(),
      navBarActions: const [
        AppTopNavBarAction(icon: Icons.bar_chart_rounded),
      ],
      onRefresh: () => _load(forceRefresh: true),
      content: contentModules,
    );
  }

  Widget _buildEmptyState() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 48, horizontal: 24),
        decoration: BoxDecoration(
          color: AppColors.cardBackground,
          borderRadius: BorderRadius.circular(24),
          boxShadow: [
            BoxShadow(
              color: AppColors.textPrimary.withValues(alpha: 0.06),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.savings_outlined,
                size: 56,
                color: AppColors.textSecondary.withValues(alpha: 0.5),
              ),
              const SizedBox(height: 16),
              Text(
                'Aucun placement',
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.textSecondary,
                  fontWeight: FontWeight.w600,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                'Investissez dans une offre exclusive pour commencer à générer du rendement.',
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () {
                    Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => const OffersScreen(),
                      ),
                    );
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF059669),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  child: const Text('Explorer les offres'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  TransactionListItemData _buildPositionItem(PlacementPosition pos) {
    final valueLabel = _eurFormatter.format(pos.valueEur);
    final interestLabel = pos.accruedInterest > 0
        ? '+${_eurFormatter.format(pos.accruedInterest)}'
        : null;

    return TransactionListItemData(
      imageUrl: pos.projectImageUrl,
      icon: pos.projectImageUrl == null
          ? _iconForCategory(pos.projectCategory)
          : null,
      iconColor: Colors.white,
      avatarBackgroundColor: _colorForStatus(pos.status),
      title: pos.projectTitle,
      subtitle: '${pos.apy.toStringAsFixed(1)}% APR · ${pos.statusLabel}',
      amount: valueLabel,
      secondaryAmount: interestLabel,
      secondaryAmountColor:
          pos.accruedInterest > 0 ? const Color(0xFF059669) : null,
      onTap: () {
        Navigator.of(context)
            .push(
              MaterialPageRoute(
                builder: (_) => PlacementDetailScreen(position: pos),
              ),
            )
            .then((_) {
          if (mounted) _load(forceRefresh: true);
        });
      },
    );
  }

  List<double> _buildPortfolioSparkline() {
    final base = _earnData?.totalValueEur ?? 0;
    final interest = _earnData?.totalAccruedInterestEur ?? 0;
    final total = base + interest;
    if (total <= 0) return List.filled(30, 0);
    const points = 30;
    final rng = math.Random(42);
    final curve = <double>[];
    for (var i = 0; i < points; i++) {
      final t = i / (points - 1);
      final linear = (base - interest) + (total - (base - interest)) * t;
      final noise = (rng.nextDouble() - 0.5) * base * 0.004;
      curve.add(linear + noise);
    }
    return curve;
  }

  static Color _colorForStatus(String status) {
    switch (status) {
      case 'active':
        return const Color(0xFF059669);
      case 'fundraising':
        return const Color(0xFF3B82F6);
      case 'repaid':
        return const Color(0xFF6B7280);
      default:
        return const Color(0xFF059669);
    }
  }

  static IconData _iconForCategory(String category) {
    final lower = category.toLowerCase();
    if (lower.contains('real estate') || lower.contains('immobilier')) {
      return Icons.apartment_rounded;
    }
    if (lower.contains('energy') || lower.contains('énergie')) {
      return Icons.bolt_rounded;
    }
    if (lower.contains('tech')) {
      return Icons.memory_rounded;
    }
    return Icons.trending_up_rounded;
  }
}

// ─────────────── Shimmer Loading ───────────────

class _PlacementsShimmer extends StatefulWidget {
  const _PlacementsShimmer();

  @override
  State<_PlacementsShimmer> createState() => _PlacementsShimmerState();
}

class _PlacementsShimmerState extends State<_PlacementsShimmer>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat(reverse: true);
    _animation = CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final screen = MediaQuery.sizeOf(context);
    final heroHeight = screen.height * 0.70;

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      body: AnimatedBuilder(
        animation: _animation,
        builder: (context, _) {
          return SingleChildScrollView(
            physics: const NeverScrollableScrollPhysics(),
            child: Column(
              children: [
                _buildHeroShimmer(heroHeight, screen.width),
                Transform.translate(
                  offset: const Offset(0, -AppSpacing.lg),
                  child: _buildContentShimmer(),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildHeroShimmer(double height, double width) {
    return Container(
      width: width,
      height: height,
      decoration: const BoxDecoration(color: Color(0xFF0A2E1A)),
      child: SafeArea(
        bottom: false,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.lg,
                vertical: AppSpacing.sm,
              ),
              child: Row(
                children: [
                  _shimmerCircle(40, light: true),
                  const Spacer(),
                ],
              ),
            ),
            const Spacer(),
            _shimmerRect(width: 100, height: 28, light: true, radius: 8),
            const SizedBox(height: AppSpacing.md),
            _shimmerRect(width: 180, height: 32, light: true, radius: 8),
            const SizedBox(height: AppSpacing.lg),
            _shimmerRect(width: 120, height: 14, light: true, radius: 6),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  Widget _buildContentShimmer() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.cardBackground,
          borderRadius: BorderRadius.circular(24),
          boxShadow: [
            BoxShadow(
              color: AppColors.textPrimary.withValues(alpha: 0.06),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Column(
            children: List.generate(3, (i) => _buildRowShimmer(i)),
          ),
        ),
      ),
    );
  }

  Widget _buildRowShimmer(int index) {
    final widths = [120.0, 100.0, 110.0];
    final subWidths = [140.0, 120.0, 130.0];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          _shimmerCircle(44, light: false),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _shimmerRect(
                  width: widths[index % widths.length],
                  height: 14,
                  light: false,
                  radius: 4,
                ),
                const SizedBox(height: 6),
                _shimmerRect(
                  width: subWidths[index % subWidths.length],
                  height: 12,
                  light: false,
                  radius: 4,
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              _shimmerRect(width: 72, height: 14, light: false, radius: 4),
              const SizedBox(height: 6),
              _shimmerRect(width: 60, height: 12, light: false, radius: 4),
            ],
          ),
        ],
      ),
    );
  }

  Widget _shimmerRect({
    required double width,
    required double height,
    required bool light,
    double radius = 4,
  }) {
    final t = _animation.value;
    final baseAlpha = light ? 0.08 : 0.04;
    final peakAlpha = light ? 0.22 : 0.10;
    final alpha = baseAlpha + (peakAlpha - baseAlpha) * t;
    final color = light
        ? Colors.white.withValues(alpha: alpha)
        : AppColors.textSecondary.withValues(alpha: alpha);
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(radius),
      ),
    );
  }

  Widget _shimmerCircle(double size, {required bool light}) {
    final t = _animation.value;
    final baseAlpha = light ? 0.08 : 0.04;
    final peakAlpha = light ? 0.22 : 0.10;
    final alpha = baseAlpha + (peakAlpha - baseAlpha) * t;
    final color = light
        ? Colors.white.withValues(alpha: alpha)
        : AppColors.textSecondary.withValues(alpha: alpha);
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(shape: BoxShape.circle, color: color),
    );
  }
}
