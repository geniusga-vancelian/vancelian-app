import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../design_system/design_system.dart';
import '../../../../ui/components/line_chart_module.dart';
import '../../../favorites/data/favorites_api.dart';
import '../../../wallet/presentation/screens/wallet_statistics_screen.dart';
import '../../domain/models/placement_position.dart';

class PlacementDetailScreen extends StatefulWidget {
  const PlacementDetailScreen({super.key, required this.position});

  final PlacementPosition position;

  @override
  State<PlacementDetailScreen> createState() => _PlacementDetailScreenState();
}

class _PlacementDetailScreenState extends State<PlacementDetailScreen> {
  final FavoritesApi _favoritesApi = FavoritesApi();
  bool _isFavorite = false;
  String? _favoriteId;

  PlacementPosition get position => widget.position;

  static final _eurFormatter = NumberFormat.currency(
    locale: 'fr_FR',
    symbol: '€',
    decimalDigits: 2,
  );

  @override
  void initState() {
    super.initState();
    _loadFavoriteStatus();
  }

  Future<void> _loadFavoriteStatus() async {
    try {
      final favs = await _favoritesApi.fetchFavorites(entityType: 'exclusive_offer');
      if (!mounted) return;
      final match = favs.where((f) => f.entityId == position.projectId).toList();
      setState(() {
        _isFavorite = match.isNotEmpty;
        _favoriteId = match.isNotEmpty ? match.first.id : null;
      });
    } catch (_) {}
  }

  Future<void> _toggleFavorite() async {
    if (_isFavorite && _favoriteId != null) {
      final ok = await _favoritesApi.removeFavorite(_favoriteId!);
      if (ok && mounted) {
        setState(() {
          _isFavorite = false;
          _favoriteId = null;
        });
      }
    } else {
      final result = await _favoritesApi.addFavorite(
        entityType: 'exclusive_offer',
        entityId: position.projectId,
      );
      if (result.isSuccess && result.favorite != null && mounted) {
        setState(() {
          _isFavorite = true;
          _favoriteId = result.favorite!.id;
        });
      } else if (!result.isSuccess && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result.messageForUser()),
            duration: const Duration(seconds: 3),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final totalValue = position.valueEur + position.accruedInterest;
    final statusColor = _colorForStatus(position.status);

    return LayoutPageLevel2(
      heroFallbackColor: _heroColorForStatus(position.status),
      heroBackground: _buildHeroBackground(),
      title: position.projectTitle,
      subtitle: _eurFormatter.format(totalValue),
      subtitleStyle: AppTypography.heroAmount.copyWith(color: Colors.white),
      heroActions: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: statusColor,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            '${position.apy.toStringAsFixed(1)}% APR · ${position.statusLabel}',
            style: AppTypography.bodySmall.copyWith(color: Colors.white70),
          ),
        ],
      ),
      heroFullBleed: LineChartModule(
        data: _buildPerformanceCurve(),
        height: 80,
        lineColor: Colors.white,
      ),
      heroActionsBelowFullBleed: CircleButtonRow(
        items: [
          CircleButtonItem(
            icon: Icons.add_rounded,
            label: 'Invest',
            onTap: () {},
            isPrimary: true,
          ),
          CircleButtonItem(
            icon: Icons.arrow_downward_rounded,
            label: 'Withdraw',
            onTap: () {},
          ),
        ],
      ),
      leadingType: AppTopNavBarLeading.back,
      onLeadingTap: () => Navigator.of(context).pop(),
      navBarActions: [
        AppTopNavBarAction(
          icon: Icons.bar_chart_rounded,
          onPressed: () {
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => WalletStatisticsScreen(
                  asset: position.lendingAsset,
                  assetName: position.projectTitle,
                  portfolioScope: 'placement',
                  portfolioId: position.projectId,
                ),
              ),
            );
          },
        ),
        AppTopNavBarAction(
          icon: _isFavorite ? Icons.star_rounded : Icons.star_outline,
          iconColor: _isFavorite ? const Color(0xFFFFB800) : null,
          onPressed: _toggleFavorite,
        ),
      ],
      onRefresh: _loadFavoriteStatus,
      content: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: _buildPositionSummary(),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: _buildMetrics(),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: _buildPoolInfo(),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: _buildStatusSection(),
        ),
      ],
    );
  }

  List<double> _buildPerformanceCurve() {
    final base = position.valueEur;
    final total = base + position.accruedInterest;
    const points = 30;
    final rng = math.Random(position.projectId.hashCode);
    final curve = <double>[];
    for (var i = 0; i < points; i++) {
      final t = i / (points - 1);
      final linear = base + (total - base) * t;
      final noise = (rng.nextDouble() - 0.5) * base * 0.005;
      curve.add(linear + noise);
    }
    return curve;
  }

  Widget _buildHeroBackground() {
    final bgColor = _heroColorForStatus(position.status);
    final imageUrl = position.projectImageUrl;

    return Stack(
      fit: StackFit.expand,
      children: [
        Container(color: bgColor),
        if (imageUrl != null)
          Opacity(
            opacity: 0.55,
            child: Image.network(
              imageUrl,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => const SizedBox.shrink(),
            ),
          ),
        const DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.bottomLeft,
              end: Alignment.topRight,
              colors: [
                Color(0xCC000000),
                Color(0x4D000000),
                Colors.transparent,
              ],
              stops: [0.0, 0.5, 1.0],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildPositionSummary() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Ma position',
            style: AppTypography.titleSmall.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 16),
          _buildSummaryRow(
            'Montant investi',
            _eurFormatter.format(position.valueEur),
          ),
          const SizedBox(height: 12),
          _buildSummaryRow(
            'Intérêts accumulés',
            '+${_eurFormatter.format(position.accruedInterest)}',
            valueColor: position.accruedInterest > 0
                ? const Color(0xFF059669)
                : null,
          ),
          const Divider(height: 24),
          _buildSummaryRow(
            'Valeur totale',
            _eurFormatter.format(position.valueEur + position.accruedInterest),
            isBold: true,
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryRow(
    String label,
    String value, {
    Color? valueColor,
    bool isBold = false,
  }) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: AppTypography.bodyMedium.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        Text(
          value,
          style: AppTypography.bodyMedium.copyWith(
            color: valueColor ?? AppColors.textPrimary,
            fontWeight: isBold ? FontWeight.w700 : FontWeight.w500,
          ),
        ),
      ],
    );
  }

  Widget _buildMetrics() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Métriques',
            style: AppTypography.titleSmall.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              _buildMetricChip(
                'APR',
                '${position.apy.toStringAsFixed(1)}%',
                const Color(0xFF059669),
              ),
              const SizedBox(width: 12),
              if (position.durationMonths != null)
                _buildMetricChip(
                  'Durée',
                  '${position.durationMonths} mois',
                  const Color(0xFF3B82F6),
                ),
              const SizedBox(width: 12),
              _buildMetricChip(
                'Statut',
                position.statusLabel,
                _colorForStatus(position.status),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMetricChip(String label, String value, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          children: [
            Text(
              value,
              style: AppTypography.titleSmall.copyWith(
                color: color,
                fontWeight: FontWeight.w700,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: AppTypography.labelSmall.copyWith(
                color: AppColors.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPoolInfo() {
    final raised = position.raised;
    final target = position.target;
    final investors = position.investorsCount;

    if (raised == null && target == null && investors == null) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Informations pool',
            style: AppTypography.titleSmall.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 16),
          if (raised != null && target != null && target > 0) ...[
            _buildSummaryRow(
              'Montant levé',
              '${_formatCompact(raised)} / ${_formatCompact(target)} €',
            ),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: (position.progress ?? 0) / 100.0,
                backgroundColor: AppColors.textSecondary.withValues(alpha: 0.1),
                valueColor: AlwaysStoppedAnimation<Color>(
                  _colorForStatus(position.status),
                ),
                minHeight: 6,
              ),
            ),
            const SizedBox(height: 12),
          ],
          if (investors != null)
            _buildSummaryRow('Investisseurs', '$investors'),
          if (position.lendingAsset.isNotEmpty) ...[
            const SizedBox(height: 12),
            _buildSummaryRow('Asset pool', position.lendingAsset),
          ],
        ],
      ),
    );
  }

  Widget _buildStatusSection() {
    String message;
    IconData icon;
    Color color;

    switch (position.status) {
      case 'fundraising':
        message = 'En attente d\'activation — la levée de fonds est en cours.';
        icon = Icons.hourglass_top_rounded;
        color = const Color(0xFF3B82F6);
        break;
      case 'active':
        message = 'Votre placement génère des intérêts quotidiennement.';
        icon = Icons.trending_up_rounded;
        color = const Color(0xFF059669);
        break;
      case 'repaid':
        message = 'Cette offre est terminée. Votre capital a été remboursé.';
        icon = Icons.check_circle_rounded;
        color = const Color(0xFF6B7280);
        break;
      default:
        message = 'Statut : ${position.status}';
        icon = Icons.info_outline_rounded;
        color = AppColors.textSecondary;
    }

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 28),
          const SizedBox(width: 16),
          Expanded(
            child: Text(
              message,
              style: AppTypography.bodyMedium.copyWith(
                color: AppColors.textPrimary,
              ),
            ),
          ),
        ],
      ),
    );
  }

  static String _formatCompact(double value) {
    if (value >= 1000000) {
      return '${(value / 1000000).toStringAsFixed(1)}M';
    }
    if (value >= 1000) {
      return '${(value / 1000).toStringAsFixed(0)}k';
    }
    return value.toStringAsFixed(0);
  }

  static Color _heroColorForStatus(String status) {
    switch (status) {
      case 'active':
        return const Color(0xFF0A2E1A);
      case 'fundraising':
        return const Color(0xFF0D1B3A);
      case 'repaid':
        return const Color(0xFF1F2937);
      default:
        return const Color(0xFF0A2E1A);
    }
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
}
