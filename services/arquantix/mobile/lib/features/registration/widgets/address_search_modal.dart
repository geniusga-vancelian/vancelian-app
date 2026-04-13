import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../design_system/atoms/app_colors.dart';
import '../../../design_system/atoms/app_spacing.dart';
import '../../../design_system/atoms/grabber.dart';
import '../../../design_system/components/app_search_input.dart';
import '../../../design_system/components/app_sheet_list_item.dart';
import '../../../design_system/components/sheet_title_bar.dart';
import '../data/registration_api.dart';
import 'address_autocomplete_field.dart';

/// Bouton fermer de la modale recherche d’adresse — pour les tests (évite l’icône clear du champ).
const ValueKey<String> kAddressSearchModalCloseKey =
    ValueKey<String>('registration_address_search_modal_close');

/// Aligné sur [AppTopNavBar.preferredSize] (toolbar 60 px du flow inscription).
const double _kRegistrationTopNavBarHeight = 60;

/// Fermeture sans choix (swipe / barrière / retour).
sealed class AddressSearchModalResult {
  const AddressSearchModalResult();
}

/// L’utilisateur a choisi la saisie manuelle depuis la modale de recherche.
class AddressSearchModalManual extends AddressSearchModalResult {
  const AddressSearchModalManual();
}

/// Une suggestion Places a été choisie ; [description] alimente le résumé sur le trigger.
class AddressSearchModalPlaceId extends AddressSearchModalResult {
  const AddressSearchModalPlaceId(this.placeId, {this.description});

  final String placeId;
  final String? description;
}

void _modalLog(String message) {
  if (kDebugMode) {
    debugPrint('[AddressSearchModal] $message');
  }
}

String _uxDisallowedMessage(BuildContext context) {
  final fr = Localizations.localeOf(context).languageCode.startsWith('fr');
  return fr
      ? 'La recherche d’adresse n’est pas disponible pour ce pays'
      : 'Address search is not available for this country';
}

/// Bottom sheet style Revolut : vraie barre de recherche, clavier, liste, entrée manuelle.
///
/// [snackBarMessenger] : messager du Scaffold parent (recommandé) pour afficher les SnackBars
/// au même endroit que le reste du flow, plutôt qu’en résolvant le messenger depuis le contexte
/// overlay de la feuille.
Future<AddressSearchModalResult?> showAddressSearchModal({
  required BuildContext context,
  ScaffoldMessengerState? snackBarMessenger,
  required RegistrationApi registrationApi,
  required int minChars,
  required int debounceMs,
  required String residenceIso2,
  required List<String> allowedIso2,
  String? regionHintIso2,
  required String searchLabel,
  required String manualLabel,
}) {
  final messenger =
      snackBarMessenger ?? ScaffoldMessenger.maybeOf(context);
  return showModalBottomSheet<AddressSearchModalResult>(
    context: context,
    isScrollControlled: true,
    isDismissible: true,
    enableDrag: true,
    /// Évite un double inset : la feuille calcule elle-même le haut via [viewPadding.top].
    useSafeArea: false,
    backgroundColor: Colors.transparent,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
    ),
    builder: (ctx) => _AddressSearchModalSheet(
      snackBarMessenger: messenger,
      registrationApi: registrationApi,
      minChars: minChars,
      debounceMs: debounceMs,
      residenceIso2: residenceIso2,
      allowedIso2: allowedIso2,
      regionHintIso2: regionHintIso2,
      searchLabel: searchLabel,
      manualLabel: manualLabel,
    ),
  );
}

class _AddressSearchModalSheet extends StatefulWidget {
  const _AddressSearchModalSheet({
    this.snackBarMessenger,
    required this.registrationApi,
    required this.minChars,
    required this.debounceMs,
    required this.residenceIso2,
    required this.allowedIso2,
    this.regionHintIso2,
    required this.searchLabel,
    required this.manualLabel,
  });

  /// Messager du parent (écran d’inscription) pour SnackBars cohérents avec le flow.
  final ScaffoldMessengerState? snackBarMessenger;

  final RegistrationApi registrationApi;
  final int minChars;
  final int debounceMs;
  final String residenceIso2;
  final List<String> allowedIso2;
  final String? regionHintIso2;
  final String searchLabel;
  final String manualLabel;

  @override
  State<_AddressSearchModalSheet> createState() =>
      _AddressSearchModalSheetState();
}

class _AddressSearchModalSheetState extends State<_AddressSearchModalSheet> {
  late final TextEditingController _controller;
  late final ScrollController _resultsScrollController;
  Timer? _debounce;
  List<Map<String, String>> _predictions = [];
  bool _loading = false;
  String? _uxHint;
  String? _errorText;
  /// Incrémenté à chaque requête ; évite d’appliquer une réponse obsolète (ordre réseau).
  int _autocompleteSeq = 0;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController();
    _resultsScrollController = ScrollController();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _controller.dispose();
    _resultsScrollController.dispose();
    super.dispose();
  }

  void _showSnack(String message) {
    if (!mounted) return;
    final m = widget.snackBarMessenger ??
        ScaffoldMessenger.maybeOf(context) ??
        ScaffoldMessenger.of(context);
    m.showSnackBar(
      SnackBar(
        content: Text(message),
        behavior: SnackBarBehavior.floating,
        margin: const EdgeInsets.all(AppSpacing.md),
      ),
    );
  }

  Future<void> _fetchPredictions(String q) async {
    _modalLog('fetchPredictions q="$q"');
    final seq = ++_autocompleteSeq;
    setState(() {
      _loading = true;
      _uxHint = null;
      _errorText = null;
    });
    final allowed = widget.allowedIso2;
    final merged = allowedCountriesForPlacesQuery(
      allowedFromStep: allowed,
      residenceIso2: widget.residenceIso2,
    );
    final r = await widget.registrationApi.addressAutocomplete(
      q,
      countryIso2: widget.residenceIso2,
      region: allowed.length == 1
          ? allowed.first
          : widget.regionHintIso2 ?? widget.residenceIso2,
      allowedCountriesIso2: merged,
    );
    if (!mounted || seq != _autocompleteSeq) return;
    setState(() {
      _loading = false;
      if (r.isRateLimited) {
        _predictions = [];
        final wait = r.retryAfterSeconds;
        final msg = wait != null && wait > 0
            ? 'Trop de recherches d’adresse. Réessayez dans ~${wait}s.'
            : 'Trop de recherches d’adresse. Patientez un instant.';
        _errorText = msg;
        _showSnack(msg);
        return;
      }
      if (r.isSuccess && r.data != null) {
        final raw = r.data!['predictions'];
        if (raw is List) {
          _predictions = raw
              .whereType<Map>()
              .map(
                (e) => Map<String, String>.from(
                  e.map((k, v) => MapEntry('$k', '$v')),
                ),
              )
              .where(
                (m) =>
                    (m['description'] ?? '').isNotEmpty &&
                    (m['place_id'] ?? '').isNotEmpty,
              )
              .toList();
          if (_predictions.isEmpty && q.trim().length >= widget.minChars) {
            _uxHint =
                'Reformulez votre recherche ou utilisez l’option ci-dessous.';
          }
        } else {
          _predictions = [];
        }
      } else {
        _predictions = [];
        if (r.errorCode == 'country_not_in_allowed_list') {
          _errorText = _uxDisallowedMessage(context);
        } else {
          _errorText =
              (r.errorMessage != null && r.errorMessage!.trim().isNotEmpty)
                  ? r.errorMessage!.trim()
                  : 'Impossible de charger les suggestions. Réessayez plus tard.';
        }
      }
    });
    if (!mounted || seq != _autocompleteSeq) return;
    if (_predictions.isNotEmpty && _resultsScrollController.hasClients) {
      _resultsScrollController.jumpTo(0);
    }
  }

  void _onChanged(String q) {
    _debounce?.cancel();
    if (q.trim().length < widget.minChars) {
      _autocompleteSeq++;
      setState(() {
        _predictions = [];
        _uxHint = null;
        _errorText = null;
        _loading = false;
      });
      return;
    }
    _debounce = Timer(Duration(milliseconds: widget.debounceMs), () {
      if (!mounted) return;
      _fetchPredictions(q);
    });
    // Dès minChars atteint : afficher tout de suite le lien manuel (sans attendre le réseau).
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final mq = MediaQuery.of(context);
    final keyboardBottom = mq.viewInsets.bottom;
    final topInset = mq.viewPadding.top;
    final bottomInset = mq.viewPadding.bottom;

    /// Haut de feuille = bas de la barre supérieure du flow (safe area + 60 px comme [AppTopNavBar]).
    final sheetTopInset = topInset + _kRegistrationTopNavBarHeight;
    final sheetHeight = mq.size.height - sheetTopInset;

    /// Empêche le clavier de redimensionner la colonne (glitch) : [viewInsets] ignorés pour
    /// la colonne ; le clavier est géré par le padding bas de la liste uniquement.
    return SizedBox(
      height: sheetHeight,
      child: ClipRRect(
        borderRadius: const BorderRadius.vertical(top: Radius.circular(32)),
        child: ColoredBox(
          color: AppColors.cardBackground,
          child: MediaQuery(
            data: mq.copyWith(viewInsets: EdgeInsets.zero),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Grabber(),
                SheetTitleBar(
                  title: widget.searchLabel,
                  leadingButton: SheetCircleButton.leading(
                    key: kAddressSearchModalCloseKey,
                    onTap: () => Navigator.of(context).pop(),
                  ),
                ),
                const SizedBox(height: AppSpacing.s6),
                Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
                  child: Semantics(
                    label: widget.searchLabel,
                    textField: true,
                    child: AppSearchInput(
                      placeholder: widget.searchLabel,
                      controller: _controller,
                      variant: AppSearchInputVariant.gray,
                      autofocus: true,
                      isLoading: _loading,
                      textFieldKey: const ValueKey<String>(
                        'registration_address_search_modal_field',
                      ),
                      onChanged: _onChanged,
                    ),
                  ),
                ),
                const SizedBox(height: AppSpacing.sm),
                Expanded(
                  child: ListView(
                    controller: _resultsScrollController,
                    keyboardDismissBehavior:
                        ScrollViewKeyboardDismissBehavior.onDrag,
                    padding: EdgeInsets.only(
                      left: AppSpacing.sm,
                      right: AppSpacing.sm,
                      bottom:
                          keyboardBottom + bottomInset + AppSpacing.sm,
                    ),
                    children: _buildSheetListChildren(context),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// Même gabarit que [CircleFlag] côté pays : cercle 36 + icône lieu.
  Widget _addressListLeadingIcon() {
    return const SizedBox(
      width: 36,
      height: 36,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: AppColors.pageBackground,
          shape: BoxShape.circle,
        ),
        child: Center(
          child: Icon(
            Icons.location_on_outlined,
            size: 22,
            color: AppColors.gray,
          ),
        ),
      ),
    );
  }

  Widget _manualEntryRow(BuildContext context, VoidCallback onManual) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.sm + AppSpacing.lg,
          AppSpacing.sm,
          AppSpacing.sm + AppSpacing.lg,
          AppSpacing.md,
        ),
        child: TextButton(
          style: TextButton.styleFrom(
            padding: EdgeInsets.zero,
            minimumSize: Size.zero,
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            alignment: Alignment.centerLeft,
            foregroundColor: AppColors.indigo,
          ),
          onPressed: onManual,
          child: Text(
            widget.manualLabel,
            style: GoogleFonts.inter(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              height: 20 / 14,
              color: AppColors.indigo,
            ),
            textAlign: TextAlign.start,
          ),
        ),
      ),
    );
  }

  List<Widget> _buildSheetListChildren(BuildContext context) {
    final q = _controller.text.trim();
    final meetsMin = q.length >= widget.minChars;
    void popManual() {
      Navigator.of(context).pop(const AddressSearchModalManual());
    }

    if (!meetsMin) {
      return [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.lg,
            AppSpacing.lg,
            AppSpacing.sm,
          ),
          child: Text(
            widget.searchLabel,
            style: GoogleFonts.inter(
              fontSize: 13,
              color: AppColors.gray,
            ),
          ),
        ),
      ];
    }

    final children = <Widget>[_manualEntryRow(context, popManual)];

    if (_errorText != null) {
      children.add(
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                Icons.error_outline_rounded,
                size: 20,
                color: AppColors.errorText.withValues(alpha: 0.9),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Text(
                  _errorText!,
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    height: 1.35,
                    color: AppColors.errorText,
                  ),
                ),
              ),
            ],
          ),
        ),
      );
      return children;
    }

    for (final pr in _predictions) {
      final ts = _predictionTitleSubtitle(pr);
      final subtitle = ts.$2.isNotEmpty ? ts.$2 : null;
      final placeId = pr['place_id'] ?? '';
      children.add(
        AppSheetListItem(
          title: ts.$1,
          subtitle: subtitle,
          leading: _addressListLeadingIcon(),
          selected: false,
          showChevron: true,
          onTap: placeId.isEmpty
              ? null
              : () {
                  Navigator.of(context).pop(
                    AddressSearchModalPlaceId(
                      placeId,
                      description: pr['description'],
                    ),
                  );
                },
        ),
      );
    }

    if (_uxHint != null && !_loading && _predictions.isEmpty) {
      children.add(
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.md,
            AppSpacing.lg,
            AppSpacing.lg,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Aucun résultat',
                style: GoogleFonts.inter(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: Colors.black,
                ),
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(
                _uxHint!,
                style: GoogleFonts.inter(
                  fontSize: 13,
                  height: 1.35,
                  color: AppColors.gray,
                ),
              ),
            ],
          ),
        ),
      );
    }

    return children;
  }
}

/// Titre / sous-titre type Figma à partir de la réponse proxy (description ou champs structurés).
(String, String) _predictionTitleSubtitle(Map<String, String> pr) {
  final main = pr['main_text']?.trim();
  final sec = pr['secondary_text']?.trim();
  if (main != null && main.isNotEmpty) {
    return (main, (sec != null && sec.isNotEmpty) ? sec : '');
  }
  final d = (pr['description'] ?? '').trim();
  final idx = d.indexOf(',');
  if (idx > 0 && idx < d.length - 1) {
    return (d.substring(0, idx).trim(), d.substring(idx + 1).trim());
  }
  return (d, '');
}
