import 'package:flutter/material.dart';

import '../../../../core/config.dart';
import '../../../../core/i18n/tr.dart';
import '../../../../design_system/design_system.dart';
import '../../data/all_transactions_layout_api.dart';
import '../../widgets/transaction_template.dart';
import 'transaction_screen.dart';

/// Élément de liste pour [TransactionListScreen].
class TransactionListItem {
  const TransactionListItem({
    this.transactionId,
    required this.merchant,
    required this.dateTime,
    required this.amount,
    required this.icon,
    required this.iconColor,
    this.cryptoTicker,
    this.isExchangeBuy = false,
    this.exchangeDetail,
  });
  final String? transactionId;
  final String merchant;
  final String dateTime;
  final String amount;
  final IconData icon;
  final Color iconColor;
  final String? cryptoTicker;
  final bool isExchangeBuy;
  final String? exchangeDetail;

  bool get isExchange => cryptoTicker != null;
}

/// Parse une date française "4 mars 2026" ou "4 mars 2026 • 14:37" en [DateTime] (minuit).
DateTime? _parseDateFromDateTime(String dateTime) {
  final part = dateTime.split(' • ').first.trim();
  final parts = part.split(' ');
  if (parts.length < 3) return null;
  final day = int.tryParse(parts[0]);
  final year = int.tryParse(parts[2]);
  if (day == null || year == null) return null;
  const months = {
    'janvier': 1, 'févr.': 2, 'février': 2, 'mars': 3, 'avr.': 4, 'avril': 4,
    'mai': 5, 'juin': 6, 'juil.': 7, 'juillet': 7, 'août': 8, 'sept.': 9,
    'septembre': 9, 'oct.': 10, 'octobre': 10, 'nov.': 11, 'novembre': 11,
    'déc.': 12, 'décembre': 12,
  };
  final month = months[parts[1].toLowerCase()];
  if (month == null) return null;
  return DateTime(year, month, day);
}

String _monthLabel(DateTime d) {
  const names = ['Janv.', 'Févr.', 'Mars', 'Avr.', 'Mai', 'Juin', 'Juil.', 'Août', 'Sept.', 'Oct.', 'Nov.', 'Déc.'];
  return '${names[d.month - 1]} ${d.year}';
}

String _dayLabel(DateTime d) {
  const names = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
  return '${d.day} ${names[d.month - 1]} ${d.year}';
}

class TransactionListScreen extends StatefulWidget {
  const TransactionListScreen({
    super.key,
    required this.transactions,
  });

  final List<TransactionListItem> transactions;

  @override
  State<TransactionListScreen> createState() => _TransactionListScreenState();
}

class _TransactionListScreenState extends State<TransactionListScreen> {
  final AllTransactionsLayoutApi _allTransactionsLayoutApi = AllTransactionsLayoutApi();
  Map<String, dynamic>? _layout;
  ScrollController? _scrollController;
  bool _layoutReloadInFlight = false;
  bool _isRefreshingLayout = false;
  DateTime? _lastLayoutReloadAt;
  static const Duration _layoutReloadMinInterval = Duration(seconds: 2);
  static const double _layoutReloadOverscrollThreshold = -20;
  late List<DateTime> _months;
  List<(String dateLabel, List<TransactionListItem> items)> _sectionsByDay = [];
  int _selectedMonthIndex = 0;

  @override
  void initState() {
    super.initState();
    _scrollController = ScrollController();
    _scrollController?.addListener(_onScrollForLayoutReload);
    _buildMonths();
    _buildSectionsForMonth(_selectedMonthIndex);
    _loadLayout();
  }

  @override
  void reassemble() {
    super.reassemble();
    _loadLayout(forceRefresh: true);
  }

  @override
  void didUpdateWidget(TransactionListScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.transactions != widget.transactions) {
      _buildMonths();
      _buildSectionsForMonth(_selectedMonthIndex);
    }
  }

  @override
  void dispose() {
    _scrollController?.removeListener(_onScrollForLayoutReload);
    _scrollController?.dispose();
    super.dispose();
  }

  void _onScrollForLayoutReload() {
    final controller = _scrollController;
    if (controller == null || !controller.hasClients) return;
    if (_layoutReloadInFlight) return;

    final now = DateTime.now();
    if (_lastLayoutReloadAt != null &&
        now.difference(_lastLayoutReloadAt!) < _layoutReloadMinInterval) {
      return;
    }

    final pixels = controller.position.pixels;
    if (pixels <= _layoutReloadOverscrollThreshold) {
      _layoutReloadInFlight = true;
      _lastLayoutReloadAt = now;
      if (!_isRefreshingLayout && mounted) {
        setState(() => _isRefreshingLayout = true);
      }
      _loadLayout(forceRefresh: true).whenComplete(() {
        _layoutReloadInFlight = false;
        if (mounted && _isRefreshingLayout) {
          setState(() => _isRefreshingLayout = false);
        }
      });
    }
  }

  Future<void> _loadLayout({bool forceRefresh = false}) async {
    try {
      final layout = await _allTransactionsLayoutApi.getAllTransactionsLayout(
        forceRefresh: forceRefresh,
      );
      if (!mounted) return;
      setState(() {
        _layout = layout;
        _buildMonths();
        _buildSectionsForMonth(_selectedMonthIndex);
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _layout = null;
        _buildMonths();
        _buildSectionsForMonth(_selectedMonthIndex);
      });
    }
  }

  Map<String, dynamic>? _asMap(dynamic value) {
    if (value is Map<String, dynamic>) return value;
    return null;
  }

  Map<String, dynamic>? get _layoutStructure => _asMap(_layout?['structure']);
  Map<String, dynamic>? get _headerConfig => _asMap(_layoutStructure?['header']);
  Map<String, dynamic>? get _tabsConfig => _asMap(_layoutStructure?['tabs']);
  Map<String, dynamic>? get _bodyConfig => _asMap(_layoutStructure?['body']);
  Map<String, dynamic>? get _tabsAppearance => _asMap(_tabsConfig?['appearance']);
  Map<String, dynamic>? get _tabsBackgroundBlur => _asMap(_tabsAppearance?['backgroundBlur']);

  String get _pageTitle {
    final headerCenter = _asMap(_headerConfig?['center']);
    final fromCenter = (headerCenter?['title'] ?? '').toString().trim();
    if (fromCenter.isNotEmpty) return fromCenter;
    final fromHeader = (_headerConfig?['title'] ?? '').toString().trim();
    if (fromHeader.isNotEmpty) return fromHeader;
    /// Démo Stratégie 1 : `screen.transactions.title` overridable depuis
    /// `/admin/i18n/ui-strings`, sinon fallback EN compilé.
    return tr(key: 'screen.transactions.title', fallback: 'All transactions');
  }

  bool get _showMonthTabs {
    final mode = (_tabsConfig?['mode'] ?? '').toString().trim().toLowerCase();
    final source = (_tabsConfig?['source'] ?? '').toString().trim().toLowerCase();
    if (_tabsConfig == null) return true;
    return mode == 'filter' && source == 'transaction_months';
  }

  bool get _filterBySelectedMonth {
    final raw = _bodyConfig?['filterBySelectedTab'];
    if (raw is bool) return raw;
    return true;
  }

  String get _defaultTabSelection {
    final behavior = _asMap(_tabsConfig?['behavior']);
    return (behavior?['default'] ?? '').toString().trim().toLowerCase();
  }

  double _asDouble(dynamic value, {required double fallback}) {
    if (value is num) return value.toDouble();
    if (value is String) {
      final parsed = double.tryParse(value.trim());
      if (parsed != null) return parsed;
    }
    return fallback;
  }

  Color? _parseHexColor(String? raw) {
    if (raw == null) return null;
    final value = raw.trim();
    if (value.isEmpty) return null;
    var hex = value.startsWith('#') ? value.substring(1) : value;
    if (hex.length == 6) hex = 'FF$hex';
    if (hex.length != 8) return null;
    final parsed = int.tryParse(hex, radix: 16);
    if (parsed == null) return null;
    return Color(parsed);
  }

  bool get _tabsBlurEnabled {
    final enabled = _tabsBackgroundBlur?['enabled'];
    if (enabled is bool) return enabled;
    if (enabled is String) return enabled.trim().toLowerCase() == 'true';
    return false;
  }

  double get _tabsBlurSigmaX => _asDouble(_tabsBackgroundBlur?['sigmaX'], fallback: 14);
  double get _tabsBlurSigmaY => _asDouble(_tabsBackgroundBlur?['sigmaY'], fallback: 14);
  double get _tabsBlurRadius => _asDouble(_tabsBackgroundBlur?['borderRadius'], fallback: 16);
  double get _tabsPaddingVertical =>
      _asDouble(_tabsBackgroundBlur?['paddingVertical'], fallback: 10);
  double get _tabsPaddingHorizontal =>
      _asDouble(_tabsBackgroundBlur?['paddingHorizontal'], fallback: 12);

  Color get _tabsTintColor {
    final base = _parseHexColor(_tabsBackgroundBlur?['tintColor']?.toString()) ?? Colors.white;
    final opacity = _asDouble(_tabsBackgroundBlur?['tintOpacity'], fallback: 0.55).clamp(0.0, 1.0);
    return base.withValues(alpha: opacity);
  }

  Color get _tabsBorderColor {
    final base = _parseHexColor(_tabsBackgroundBlur?['borderColor']?.toString()) ?? Colors.white;
    final opacity = _asDouble(_tabsBackgroundBlur?['borderOpacity'], fallback: 0.35).clamp(0.0, 1.0);
    return base.withValues(alpha: opacity);
  }

  Widget _buildMonthTabs() {
    final tabs = SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: EdgeInsets.symmetric(
        vertical: _tabsPaddingVertical,
        horizontal: _tabsPaddingHorizontal,
      ),
      child: Row(
        children: List.generate(_months.length, (i) {
          return AppFilterChip(
            label: _monthLabel(_months[i]),
            selected: i == _selectedMonthIndex,
            onTap: () => _onMonthSelected(i),
          );
        }),
      ),
    );

    if (!_tabsBlurEnabled) {
      return SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: Row(
          children: List.generate(_months.length, (i) {
            return AppFilterChip(
              label: _monthLabel(_months[i]),
              selected: i == _selectedMonthIndex,
              onTap: () => _onMonthSelected(i),
            );
          }),
        ),
      );
    }

    return BlurredFilterBar.apple(
      borderRadius: _tabsBlurRadius,
      sigmaX: _tabsBlurSigmaX,
      sigmaY: _tabsBlurSigmaY,
      tintColor: _tabsTintColor,
      tintOpacity: 1,
      borderColor: _tabsBorderColor,
      borderOpacity: 1,
      padding: EdgeInsets.zero,
      child: tabs,
    );
  }

  int _resolveDefaultMonthIndex() {
    if (_months.isEmpty) return 0;
    if (_defaultTabSelection != 'current_month') return 0;
    final now = DateTime.now();
    final idx = _months.indexWhere((m) => m.year == now.year && m.month == now.month);
    return idx >= 0 ? idx : 0;
  }

  void _buildMonths() {
    final monthSet = <DateTime>{};
    for (final t in widget.transactions) {
      final d = _parseDateFromDateTime(t.dateTime);
      if (d != null) monthSet.add(DateTime(d.year, d.month));
    }
    _months = monthSet.toList()..sort((a, b) => b.compareTo(a));
    if (_months.isEmpty) _months.add(DateTime.now());
    _selectedMonthIndex = _resolveDefaultMonthIndex();
  }

  void _buildSectionsForMonth(int monthIndex) {
    if (_months.isEmpty || monthIndex < 0 || monthIndex >= _months.length) {
      _sectionsByDay = [];
      return;
    }
    final selectedMonth = _months[monthIndex];
    final inMonth = _filterBySelectedMonth
        ? widget.transactions.where((t) {
            final d = _parseDateFromDateTime(t.dateTime);
            return d != null && d.year == selectedMonth.year && d.month == selectedMonth.month;
          }).toList()
        : widget.transactions.toList();
    inMonth.sort((a, b) {
      final da = _parseDateFromDateTime(a.dateTime);
      final db = _parseDateFromDateTime(b.dateTime);
      if (da == null && db == null) return 0;
      if (da == null) return 1;
      if (db == null) return -1;
      return db.compareTo(da);
    });
    final byDay = <DateTime, List<TransactionListItem>>{};
    for (final t in inMonth) {
      final d = _parseDateFromDateTime(t.dateTime)!;
      final day = DateTime(d.year, d.month, d.day);
      byDay.putIfAbsent(day, () => []).add(t);
    }
    final dayKeys = byDay.keys.toList()..sort((a, b) => b.compareTo(a));
    _sectionsByDay = dayKeys.map((d) => (_dayLabel(d), byDay[d]!)).toList();
  }

  void _onMonthSelected(int index) {
    setState(() {
      _selectedMonthIndex = index;
      _buildSectionsForMonth(index);
    });
  }

  TransactionListItemData _mapToDs(TransactionListItem t) {
    final onTap = () => Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => TransactionScreen(
          transactionId: t.transactionId,
          merchant: t.merchant,
          dateTime: t.dateTime,
          amount: t.amount,
          icon: t.icon,
          iconColor: t.iconColor,
        ),
      ),
    );

    if (t.isExchange && t.cryptoTicker != null) {
      final ticker = t.cryptoTicker!;
      final logoUrl = Config.resolveLogoUrl(
        '/media/crypto_logos/${ticker.toLowerCase()}.png',
      );
      return TransactionListItemData(
        leadingWidget: TransactionSwapAvatar(
          fromTicker: t.isExchangeBuy ? 'EUR' : ticker,
          toTicker: t.isExchangeBuy ? ticker : 'EUR',
          fromLogoUrl: t.isExchangeBuy ? null : logoUrl,
          toLogoUrl: t.isExchangeBuy ? logoUrl : null,
          fromIcon: t.isExchangeBuy ? Icons.euro_rounded : null,
          toIcon: t.isExchangeBuy ? null : Icons.euro_rounded,
        ),
        title: t.merchant,
        subtitle: t.dateTime,
        amount: t.amount,
        secondaryAmount: t.exchangeDetail,
        secondaryAmountColor: AppColors.textMuted,
        onTap: onTap,
      );
    }

    return TransactionListItemData(
      icon: t.icon,
      iconColor: Colors.white,
      avatarBackgroundColor: t.iconColor,
      title: t.merchant,
      subtitle: t.dateTime,
      amount: t.amount,
      onTap: onTap,
    );
  }

  @override
  Widget build(BuildContext context) {
    return TransactionTemplate(
      title: _pageTitle,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            curve: Curves.easeOut,
            height: _isRefreshingLayout ? 24 : 0,
            child: _isRefreshingLayout
                ? const Center(
                    child: SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                  )
                : const SizedBox.shrink(),
          ),
          if (_showMonthTabs)
            _buildMonthTabs(),
          SizedBox(height: _showMonthTabs ? AppSpacing.lg : AppSpacing.md),
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.only(bottom: 24),
              itemCount: _sectionsByDay.length,
              itemBuilder: (context, i) {
                final section = _sectionsByDay[i];
                return Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.xl),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Padding(
                        padding: const EdgeInsets.only(left: 4, bottom: AppSpacing.sm),
                        child: Text(section.$1, style: AppTypography.title2),
                      ),
                      TransactionListCard(
                        itemSpacing: AppSpacing.lg,
                        items: section.$2.map(_mapToDs).toList(),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
