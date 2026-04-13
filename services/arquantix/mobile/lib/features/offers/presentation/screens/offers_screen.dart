import 'package:flutter/material.dart';

import '../../../../core/profile_leading_preference.dart';
import '../../../../design_system/design_system.dart';
import '../../../profile/presentation/screens/profile_screen.dart';
import '../../data/offers_api.dart';
import '../../data/offers_layout_api.dart';
import '../../data/offers_repository.dart';
import '../../domain/models/offer_project.dart';
import 'exclusive_offer_detail_screen.dart';

/// Page "Investir" : LayoutPageLevel2 sans bouton CTA.
/// Body = un module blanc regroupant les accès produits (lignes), puis What's Hot.
class OffersScreen extends StatefulWidget {
  const OffersScreen({super.key});

  @override
  State<OffersScreen> createState() => _OffersScreenState();
}

class _OffersScreenState extends State<OffersScreen> {
  final OffersRepository _repository = OffersRepository();
  final OffersApi _api = OffersApi();
  final OffersLayoutApi _offersLayoutApi = OffersLayoutApi();
  bool _loading = true;
  String? _error;
  List<OfferProject> _projects = const [];
  String? _heroImageUrl;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait([
        _repository.getProjects(),
        _api.getInvestmentCategories(),
        _offersLayoutApi.getOffersLayout().catchError((_) => <String, dynamic>{}),
      ]);
      final layout = results[2] as Map<String, dynamic>;
      final heroUrl = (layout['structure']
              as Map<String, dynamic>?)?['header']
          ?['background']?['imageUrl'] as String?;
      setState(() {
        _projects = results[0] as List<OfferProject>;
        _heroImageUrl = (heroUrl ?? '').trim().isNotEmpty ? heroUrl : null;
        _loading = false;
        _error = null;
      });
    } catch (e) {
      setState(() {
        _loading = false;
        _error = e.toString();
      });
    }
  }

  ExclusiveOfferCarouselItem _toCarouselItem(OfferProject p, int index) {
    return ExclusiveOfferCarouselItem(
      cacheKey: p.id,
      imageUrl: p.imageUrl,
      category: p.category,
      title: p.title,
      description: (p.description ?? '').trim().isNotEmpty
          ? p.description!.trim()
          : (p.shortDescription ?? ''),
      progress: p.progressRatio,
      raisedAmount: p.raisedFormatted,
      investorsCount: p.investorsCount ?? 0,
      annualizedReturnPercent: p.apy,
      targetDurationMonths: p.durationMonths,
      targetAmountLabel: p.hasLendingData ? '${p.targetFormatted} €' : null,
      isLiked: false,
      onTap: () => _openExclusiveOffer(p),
      onInvestTap: () => _openExclusiveOfferInvest(p),
      onLikeTap: () {},
    );
  }

  void _openExclusiveOffer(OfferProject project) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => ExclusiveOfferDetailScreen(project: project),
      ),
    );
  }

  void _openExclusiveOfferInvest(OfferProject project) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => ExclusiveOfferDetailScreen(
          project: project,
          autoStartInvest: true,
        ),
      ),
    );
  }

  /// Aligné sur le DS — Settings / ListItem **Variante 2** (showcase) : [IconContainer] neutre,
  /// titre + sous-titre + valeur à droite + chevron ; pas de séparateurs (gap du [SettingsCard]).
  static const List<_ProductOptionData> _investOptions = [
    _ProductOptionData(
      title: 'Épargne rémunérée',
      description: 'Jusqu\'à 9% APY, disponible à tout moment.',
      value: '9% max',
      icon: Icons.savings_rounded,
      heroColor: Color(0xFF3B82F6),
    ),
    _ProductOptionData(
      title: 'Offres exclusives',
      description: 'Projets sélectionnés jusqu\'à 13% APR.',
      value: '13% APR',
      icon: Icons.home_rounded,
      heroColor: Color(0xFF6366F1),
    ),
    _ProductOptionData(
      title: 'Gestion déléguée',
      description: 'Stratégie sur mesure par nos gérants.',
      value: 'Sur mesure',
      icon: Icons.trending_up_rounded,
      heroColor: Color(0xFFF59E0B),
    ),
    _ProductOptionData(
      title: 'Acheter des crypto',
      description: 'Plus de 50 cryptoactifs disponibles.',
      value: '50+ actifs',
      icon: Icons.currency_bitcoin_rounded,
      heroColor: Color(0xFFEAB308),
    ),
    _ProductOptionData(
      title: 'Thématiques',
      description: 'Paniers DeFi, Layer 2, métavers…',
      value: 'Paniers',
      icon: Icons.pie_chart_rounded,
      heroColor: Color(0xFF22C55E),
    ),
  ];

  @override
  Widget build(BuildContext context) {
    if (_loading && _projects.isEmpty) {
      return const Scaffold(
        backgroundColor: AppColors.pageBackground,
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (_error != null && _projects.isEmpty) {
      return Scaffold(
        backgroundColor: AppColors.pageBackground,
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(_error!, style: AppTypography.meta, textAlign: TextAlign.center),
              const SizedBox(height: AppSpacing.lg),
              TextButton.icon(
                onPressed: _load,
                icon: const Icon(Icons.refresh, size: 20),
                label: const Text('Réessayer'),
              ),
            ],
          ),
        ),
      );
    }

    const hPad = EdgeInsets.symmetric(horizontal: AppSpacing.xl);

    return ListenableBuilder(
      listenable: ProfileLeadingPreference.instance,
      builder: (context, _) {
        return LayoutPageLevel2(
      heroHeightFraction: 0.70,
      heroFallbackColor: _investOptions.first.heroColor,
      heroOverlay: HeroOverlayConfig.none,
      heroImageUrl: _heroImageUrl,
      title: 'Investir',
      leadingType: AppTopNavBarLeading.profile,
      onLeadingTap: () {
        Navigator.of(context).push(
          MaterialPageRoute<void>(builder: (_) => const ProfileScreen()),
        );
      },
      profileInitials: ProfileLeadingPreference.instance.initials,
      navBarActions: const [
        AppTopNavBarAction(icon: Icons.bar_chart_rounded),
        AppTopNavBarAction(icon: Icons.notifications_outlined),
      ],
      onRefresh: _load,
      moduleSpacing: AppSpacing.s10,
      content: [
        Padding(
          padding: hPad,
          child: SettingsCard(
            children: [
              for (final o in _investOptions)
                SettingsListItem(
                  leading: IconContainer(
                    borderRadius: 100,
                    child: Icon(o.icon, size: 16, color: const Color(0xFF8E8E93)),
                  ),
                  title: o.title,
                  subtitle: o.description,
                  value: o.value,
                  showChevron: true,
                  onTap: () {},
                ),
            ],
          ),
        ),

        // ── What's Hot (full-width, le carousel gère ses paddings) ──
        if (_projects.isNotEmpty)
          ExclusiveOffersCarousel(
            title: "What's Hot",
            withDescription: true,
            items: _projects
                .asMap()
                .entries
                .map((e) => _toCarouselItem(e.value, e.key))
                .toList(),
          ),
      ],
    );
      },
    );
  }
}

class _ProductOptionData {
  const _ProductOptionData({
    required this.title,
    this.description,
    required this.value,
    required this.icon,
    required this.heroColor,
  });
  final String title;
  final String? description;
  final String value;
  final IconData icon;
  /// Couleur de secours du hero uniquement (hors liste).
  final Color heroColor;
}
