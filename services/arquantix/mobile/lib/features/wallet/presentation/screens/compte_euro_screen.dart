import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../core/config.dart';
import '../../../../design_system/design_system.dart';
import '../../data/euro_account_api.dart';
import '../../data/euro_account_layout_api.dart';
import '../../domain/models/euro_account_data.dart';
import '../widgets/euro_statement_bottom_sheet.dart';
import 'iban_screen.dart';
import 'transaction_screen.dart';

class CompteEuroScreen extends StatefulWidget {
  const CompteEuroScreen({super.key});

  @override
  State<CompteEuroScreen> createState() => _CompteEuroScreenState();
}

class _CompteEuroScreenState extends State<CompteEuroScreen> {
  static const Color _defaultHeroColor = Color(0xFF0D1B2A);

  final EuroAccountLayoutApi _layoutApi = EuroAccountLayoutApi();
  final EuroAccountApi _euroApi = EuroAccountApi();

  Map<String, dynamic>? _layout;
  EuroAccountData? _euroData;
  bool _isLoading = true;
  String? _loadError;

  @override
  void initState() {
    super.initState();
    _loadAll();
  }

  @override
  void reassemble() {
    super.reassemble();
    _loadAll(forceRefresh: true);
  }

  Future<void> _loadAll({bool forceRefresh = false}) async {
    setState(() {
      _isLoading = true;
      _loadError = null;
    });
    try {
      final results = await Future.wait([
        _layoutApi.getEuroAccountLayout(forceRefresh: forceRefresh),
        _euroApi.fetchEuroAccount(),
      ]);
      if (!mounted) return;
      setState(() {
        _layout = results[0] as Map<String, dynamic>;
        _euroData = results[1] as EuroAccountData;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _loadError = e.toString();
      });
    }
  }

  // --- Layout structure accessors ---

  Map<String, dynamic> get _layoutStructure =>
      _asMap(_layout?['structure']) ?? const <String, dynamic>{};
  Map<String, dynamic> get _headerConfig =>
      _asMap(_layoutStructure['header']) ?? const <String, dynamic>{};
  Map<String, dynamic> get _bodyConfig =>
      _asMap(_layoutStructure['body']) ?? const <String, dynamic>{};
  Map<String, dynamic> get _headerBalanceConfig =>
      _asMap(_headerConfig['balance']) ?? const <String, dynamic>{};
  Map<String, dynamic> get _headerIbanConfig =>
      _asMap(_headerBalanceConfig['iban']) ?? const <String, dynamic>{};
  Map<String, dynamic> get _transactionLatest10Config =>
      _asMap(_bodyConfig['transactionLatest10']) ?? const <String, dynamic>{};

  int get _transactionLimit => _asInt(_transactionLatest10Config['limit'], fallback: 10);
  String get _transactionModuleTitle => _asString(_transactionLatest10Config['title'], fallback: '');

  // --- Real balance from backend ---

  String get _balanceTitle {
    return _asString(_headerBalanceConfig['title'], fallback: 'Euro');
  }

  String get _balanceAmount {
    final account = _euroData?.account;
    if (account == null) {
      return _asString(_headerBalanceConfig['amount'], fallback: '0,00 \u20ac');
    }
    final balance = double.tryParse(account.balance) ?? 0;
    final formatter = NumberFormat.currency(
      locale: 'fr_FR',
      symbol: account.currencySymbol,
      decimalDigits: 2,
    );
    return formatter.format(balance);
  }

  String get _ibanLabel {
    final account = _euroData?.account;
    if (account != null && account.ibanMasked != null && account.ibanMasked!.isNotEmpty) {
      return account.ibanMasked!;
    }
    return _asString(_headerIbanConfig['label'], fallback: '');
  }

  String get _ibanRedirectUrl => _asString(_headerIbanConfig['redirectUrl'], fallback: '');

  List<EuroTransaction> get _limitedTransactions {
    final txs = _euroData?.transactions ?? [];
    final limit = _transactionLimit <= 0 ? 10 : _transactionLimit;
    return txs.take(limit).toList();
  }

  // ─────────────── Build ───────────────

  @override
  Widget build(BuildContext context) {
    if (_isLoading) return const _EuroAccountShimmer();

    if (_loadError != null) {
      return Scaffold(
        backgroundColor: AppColors.pageBackground,
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.xl),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.error_outline_rounded, size: 48,
                    color: AppColors.textSecondary.withValues(alpha: 0.8)),
                const SizedBox(height: AppSpacing.lg),
                Text('Impossible de charger le Compte Euro.',
                  textAlign: TextAlign.center,
                  style: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary)),
                const SizedBox(height: AppSpacing.xl),
                TextButton.icon(
                  onPressed: () => _loadAll(forceRefresh: true),
                  icon: const Icon(Icons.refresh_rounded),
                  label: const Text('R\u00e9essayer'),
                  style: TextButton.styleFrom(foregroundColor: AppColors.accent),
                ),
              ],
            ),
          ),
        ),
      );
    }

    if (_layoutStructure.isEmpty) {
      return const Scaffold(
        body: Center(child: Text('Layout Compte Euro invalide ou vide.')),
      );
    }

    final txs = _limitedTransactions;
    final contentModules = <Widget>[
      if (txs.isNotEmpty)
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: TransactionListCard(
            items: txs.map(_buildTransactionItem).toList(),
          ),
        ),
    ];

    final heroActionsIban = _buildHeroSubtitleIban();
    final heroActionsBelow = _buildActionButtons();

    return LayoutPageLevel3(
      heroBackground: _buildEuroHeroBackground(),
      heroOverlay: HeroOverlayConfig.none,
      title: _balanceTitle,
      subtitle: _balanceAmount,
      subtitleStyle: AppTypography.heroAmount.copyWith(color: Colors.white),
      heroActions: heroActionsIban,
      heroActionsBelowFullBleed: heroActionsBelow,
      leadingType: AppTopNavBarLeading.back,
      onLeadingTap: () => Navigator.of(context).pop(),
      onRefresh: () => _loadAll(forceRefresh: true),
      content: contentModules,
    );
  }

  void _openIbanScreen() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => const IbanScreen()),
    );
  }

  void _openStatementSheet() {
    EuroStatementBottomSheet.show(context);
  }

  Widget? _buildHeroSubtitleIban() {
    final label = _ibanLabel;
    if (label.isEmpty) return null;
    final style = AppTypography.bodySmall.copyWith(color: Colors.white70);
    return GestureDetector(
      onTap: _openIbanScreen,
      child: Text(label, style: style, textAlign: TextAlign.center),
    );
  }

  Widget? _buildActionButtons() {
    final raw = _asList(_headerConfig['action_buttons']);
    if (raw.isEmpty) return null;

    final items = <CircleButtonItem>[];
    for (final action in raw) {
      final map = action is Map ? action.cast<String, dynamic>() : null;
      final key = _asString(map?['key'] ?? action, fallback: '').toLowerCase();
      if (key.isEmpty) continue;
      final label = _asString(map?['label'], fallback: '');
      final icon = _iconFromKey(_asString(map?['icon'], fallback: ''));
      final redirectUrl = _asString(map?['redirectUrl'], fallback: '');
      if (label.isEmpty || icon == null) continue;

      final isIbanButton = key == 'iban' || key == 'rib';
      final isStatementButton = key == 'statement' ||
          key == 'statements' ||
          key == 'releve' ||
          key == 'releves';
      if (!isIbanButton && !isStatementButton && redirectUrl.isEmpty) continue;

      items.add(
        CircleButtonItem(
          icon: icon,
          label: label,
          onTap: isIbanButton
              ? _openIbanScreen
              : isStatementButton
                  ? _openStatementSheet
                  : () => _openLink(redirectUrl),
          isPrimary: items.isEmpty,
        ),
      );
    }

    if (items.isEmpty) return null;
    return CircleButtonRow(items: items);
  }

  // ─────────────── Hero background (aligné dashboard / registration partial) ───────────────

  Widget _buildEuroHeroBackground() {
    return const DecoratedBox(
      decoration: DashboardHeaderGradient.decoration,
      child: SizedBox.expand(),
    );
  }

  // ─────────────── Transaction mapping ───────────────

  static final _amountFormatter = NumberFormat('#,##0.00', 'fr_FR');

  TransactionListItemData _buildTransactionItem(EuroTransaction tx) {
    final isCredit = tx.direction == 'credit';
    final amount = double.tryParse(tx.amount) ?? 0;
    final sign = isCredit ? '+' : '-';
    final formattedAmount = '$sign${_amountFormatter.format(amount)} ${tx.currencySymbol}';
    final badgeStatus = _badgeFromStatus(tx.status);
    final kind = tx.transactionKind;
    final isExchange = kind == 'exchange_buy' || kind == 'exchange_sell';
    final isBuy = kind == 'exchange_buy';

    Widget? leadingWidget;
    String title = tx.title;
    String subtitle = tx.subtitle;

    if (isExchange) {
      final cryptoTicker = _extractCryptoTicker(tx.subtitle);
      if (cryptoTicker != null) {
        final logoUrl = Config.resolveLogoUrl(
          '/media/crypto_logos/${cryptoTicker.toLowerCase()}.png',
        );
        leadingWidget = TransactionSwapAvatar(
          fromTicker: isBuy ? 'EUR' : cryptoTicker,
          toTicker: isBuy ? cryptoTicker : 'EUR',
          fromLogoUrl: isBuy ? null : logoUrl,
          toLogoUrl: isBuy ? logoUrl : null,
          fromIcon: isBuy ? Icons.euro_rounded : null,
          toIcon: isBuy ? null : Icons.euro_rounded,
        );
        title = isBuy
            ? 'EUR → $cryptoTicker'
            : '$cryptoTicker → EUR';
        subtitle = _formatDateLabel(tx.createdAt);
      }
    }

    if (leadingWidget != null) {
      return TransactionListItemData(
        leadingWidget: leadingWidget,
        badgeStatus: badgeStatus,
        title: title,
        subtitle: subtitle,
        amount: formattedAmount,
        secondaryAmount: _formatDateLabel(tx.createdAt),
        onTap: () => _openTransactionDetail(tx, formattedAmount, badgeStatus),
      );
    }

    return TransactionListItemData(
      icon: _iconForTxKind(kind, tx.transactionType, badgeStatus),
      iconColor: Colors.white,
      avatarBackgroundColor: _colorForTxKind(kind, tx.transactionType, isCredit, badgeStatus),
      badgeStatus: badgeStatus,
      title: title,
      subtitle: subtitle,
      amount: formattedAmount,
      secondaryAmount: _formatDateLabel(tx.createdAt),
      onTap: () => _openTransactionDetail(tx, formattedAmount, badgeStatus),
    );
  }

  void _openTransactionDetail(EuroTransaction tx, String formattedAmount, TransactionBadgeStatus badge) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => TransactionScreen(
          transactionId: tx.id,
          merchant: tx.title,
          dateTime: _formatFullDateTime(tx.createdAt),
          amount: formattedAmount,
          icon: _iconForTxKind(tx.transactionKind, tx.transactionType, badge),
          iconColor: _colorForTxKind(tx.transactionKind, tx.transactionType, tx.direction == 'credit', badge),
        ),
      ),
    );
  }

  /// Extracts the crypto ticker from a subtitle like "Buy 0.001 BTC @ 60000..."
  static String? _extractCryptoTicker(String subtitle) {
    final parts = subtitle.split(' ');
    if (parts.length >= 3) {
      final candidate = parts[2].toUpperCase();
      if (candidate.length >= 2 && candidate.length <= 6 &&
          RegExp(r'^[A-Z0-9]+$').hasMatch(candidate)) {
        return candidate;
      }
    }
    return null;
  }

  static TransactionBadgeStatus _badgeFromStatus(String status) {
    switch (status) {
      case 'completed':
        return TransactionBadgeStatus.completed;
      case 'pending':
      case 'processing':
        return TransactionBadgeStatus.pending;
      case 'failed':
      case 'reversed':
      case 'cancelled':
        return TransactionBadgeStatus.cancelled;
      default:
        return TransactionBadgeStatus.completed;
    }
  }

  static Color _amountColor(bool isCredit, TransactionBadgeStatus badge) {
    if (badge == TransactionBadgeStatus.cancelled) return const Color(0xFFDC2626);
    if (badge == TransactionBadgeStatus.pending) return const Color(0xFFF59E0B);
    return isCredit ? const Color(0xFF059669) : const Color(0xFF374151);
  }

  static IconData _iconForTxKind(String? kind, String type, TransactionBadgeStatus badge) {
    if (badge == TransactionBadgeStatus.pending) return Icons.schedule_rounded;
    if (badge == TransactionBadgeStatus.cancelled) return Icons.error_outline_rounded;

    if (kind != null) {
      switch (kind) {
        case 'bank_transfer_in':
          return Icons.account_balance_rounded;
        case 'bank_transfer_out':
          return Icons.outbox_rounded;
        case 'internal_transfer':
          return Icons.swap_horiz_rounded;
        case 'exchange_buy':
        case 'exchange_sell':
          return Icons.swap_horiz_rounded;
      }
    }
    switch (type) {
      case 'deposit':
        return Icons.account_balance_rounded;
      case 'withdrawal':
        return Icons.outbox_rounded;
      case 'transfer_internal':
        return Icons.swap_horiz_rounded;
      default:
        return Icons.receipt_long_rounded;
    }
  }

  static Color _colorForTxKind(String? kind, String type, bool isCredit, TransactionBadgeStatus badge) {
    if (badge == TransactionBadgeStatus.pending) return const Color(0xFFF59E0B);
    if (badge == TransactionBadgeStatus.cancelled) return const Color(0xFFDC2626);

    if (kind != null) {
      switch (kind) {
        case 'bank_transfer_in':
          return const Color(0xFF3B82F6);
        case 'bank_transfer_out':
          return const Color(0xFF0EA5E9);
        case 'internal_transfer':
          return const Color(0xFF8B5CF6);
        case 'exchange_buy':
          return const Color(0xFF22C55E);
        case 'exchange_sell':
          return const Color(0xFFF97316);
      }
    }
    switch (type) {
      case 'deposit':
        return const Color(0xFF3B82F6);
      case 'withdrawal':
        return const Color(0xFF0EA5E9);
      case 'transfer_internal':
        return const Color(0xFF8B5CF6);
      default:
        return isCredit ? const Color(0xFF22C55E) : const Color(0xFF64748B);
    }
  }

  static const _frenchMonths = [
    'janvier', 'f\u00e9vrier', 'mars', 'avril', 'mai', 'juin',
    'juillet', 'ao\u00fbt', 'septembre', 'octobre', 'novembre', 'd\u00e9cembre',
  ];

  static String _formatDateLabel(DateTime dt) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final txDay = DateTime(dt.year, dt.month, dt.day);
    final diff = today.difference(txDay).inDays;

    if (diff == 0) return "Aujourd'hui";
    if (diff == 1) return 'Hier';
    if (diff < 7) return 'Il y a $diff jours';
    return DateFormat('dd/MM/yyyy').format(dt);
  }

  static String _formatFullDateTime(DateTime dt) {
    final hh = dt.hour.toString().padLeft(2, '0');
    final mm = dt.minute.toString().padLeft(2, '0');
    return '${dt.day} ${_frenchMonths[dt.month - 1]} ${dt.year} \u2022 $hh:$mm';
  }

  // ─────────────── Helpers ───────────────

  Future<void> _openLink(String url) async {
    final normalized = url.trim();
    if (normalized.isEmpty) return;
    final uri = Uri.tryParse(normalized);
    if (uri == null) return;
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  IconData? _iconFromKey(String key) {
    switch (key.trim().toLowerCase()) {
      case 'add':
      case 'add_rounded':
        return Icons.add_rounded;
      case 'remove':
      case 'remove_rounded':
        return Icons.remove_rounded;
      case 'account_balance':
      case 'account_balance_rounded':
        return Icons.account_balance_rounded;
      case 'description':
      case 'description_rounded':
        return Icons.description_rounded;
      case 'trending_up':
      case 'trending_up_rounded':
        return Icons.trending_up_rounded;
      case 'savings':
      case 'savings_rounded':
        return Icons.savings_rounded;
      case 'article':
      case 'article_outlined':
        return Icons.article_outlined;
      case 'description_outlined':
        return Icons.description_outlined;
      default:
        return null;
    }
  }

  Map<String, dynamic>? _asMap(dynamic value) {
    if (value is Map<String, dynamic>) return value;
    if (value is Map) {
      final casted = <String, dynamic>{};
      for (final entry in value.entries) {
        casted[entry.key.toString()] = entry.value;
      }
      return casted;
    }
    return null;
  }

  List<dynamic> _asList(dynamic value) {
    if (value is List) return value;
    return const [];
  }

  String _asString(dynamic value, {required String fallback}) {
    final out = (value ?? '').toString().trim();
    return out.isEmpty ? fallback : out;
  }

  int _asInt(dynamic value, {required int fallback}) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) {
      final parsed = int.tryParse(value.trim());
      if (parsed != null) return parsed;
    }
    return fallback;
  }

}

// ─────────────── Shimmer Loading ───────────────

class _EuroAccountShimmer extends StatefulWidget {
  const _EuroAccountShimmer();

  @override
  State<_EuroAccountShimmer> createState() => _EuroAccountShimmerState();
}

class _EuroAccountShimmerState extends State<_EuroAccountShimmer>
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
    final topPad = MediaQuery.paddingOf(context).top;
    final navBarHeight = topPad + kToolbarHeight;
    final heroHeight = navBarHeight + AppSpacing.pageEdge
        + 42 + AppSpacing.sm + 22
        + LayoutPageLevel3.gapAmountToSubtitle + 40
        + 2 * LayoutPageLevel3.marginBelowBalance
        + 70 + AppSpacing.s10;

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      body: AnimatedBuilder(
        animation: _animation,
        builder: (context, _) {
          return SingleChildScrollView(
            physics: const NeverScrollableScrollPhysics(),
            child: Column(
              children: [
                _buildHeroShimmer(heroHeight, topPad, screen.width),
                _buildContentShimmer(screen.width),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildHeroShimmer(double height, double topPad, double width) {
    return Container(
      width: width,
      height: height,
      decoration: const BoxDecoration(
        color: _CompteEuroScreenState._defaultHeroColor,
      ),
      child: SafeArea(
        bottom: false,
        child: Column(
          children: [
            // Nav bar placeholder
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.lg,
                vertical: AppSpacing.sm,
              ),
              child: Row(
                children: [
                  _shimmerCircle(40, light: true),
                  const Spacer(),
                  _shimmerCircle(40, light: true),
                ],
              ),
            ),
            const Spacer(),
            // Title placeholder ("Euro")
            _shimmerRect(width: 80, height: 28, light: true, radius: 8),
            const SizedBox(height: AppSpacing.md),
            // Balance placeholder ("3 345,00 €")
            _shimmerRect(width: 200, height: 32, light: true, radius: 8),
            const SizedBox(height: AppSpacing.lg),
            // IBAN placeholder
            _shimmerRect(width: 140, height: 16, light: true, radius: 6),
            const SizedBox(height: AppSpacing.xl),
            // Action buttons row
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 40),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: List.generate(4, (_) => _buildActionButtonShimmer()),
              ),
            ),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButtonShimmer() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        _shimmerCircle(52, light: true),
        const SizedBox(height: AppSpacing.sm),
        _shimmerRect(width: 48, height: 10, light: true, radius: 4),
      ],
    );
  }

  Widget _buildContentShimmer(double width) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 0),
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
          children: List.generate(5, (i) => _buildTransactionShimmer(i)),
        ),
      ),
    );
  }

  Widget _buildTransactionShimmer(int index) {
    final widths = [120.0, 100.0, 140.0, 110.0, 90.0];
    final subWidths = [80.0, 70.0, 100.0, 85.0, 75.0];
    final amountWidths = [72.0, 64.0, 80.0, 68.0, 56.0];
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
              _shimmerRect(
                width: amountWidths[index % amountWidths.length],
                height: 14,
                light: false,
                radius: 4,
              ),
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
