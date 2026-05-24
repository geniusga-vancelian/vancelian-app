import 'package:flutter/material.dart';

import '../../../../core/locale_preference.dart';
import '../../../landing_preview/presentation/screens/landing_page_preview_screen.dart';

/// Écran générique « page CMS » embarqué dans le shell de l'app Flutter.
///
/// Cible : items de la tab bar dont la `target` CMS est `cms_page` (slug d'une
/// page créée via le builder admin landing-pages, ou tout futur builder qui
/// expose `/api/mobile/flutter/landing-pages/[slug]`).
///
/// Réutilise [LandingPagePreviewScreen] comme moteur de rendu (déjà câblé sur
/// l'ensemble des modules), avec deux différences clés vs preview admin :
/// - `controlsEnabled: false` : pas de barre de contrôle slug (UI runtime pur).
/// - `useDraft: false` : on consomme la version **publiée** uniquement
///   (le brouillon reste réservé à la preview admin).
///
/// Écoute [LocalePreference] : un changement de langue dans le profil force le
/// remount via `ValueKey(slug + locale)` → recharge transparente du contenu.
class CmsPageScreen extends StatefulWidget {
  const CmsPageScreen({super.key, required this.slug});

  final String slug;

  @override
  State<CmsPageScreen> createState() => _CmsPageScreenState();
}

class _CmsPageScreenState extends State<CmsPageScreen> {
  @override
  void initState() {
    super.initState();
    LocalePreference.instance.addListener(_onLocaleChanged);
  }

  @override
  void dispose() {
    LocalePreference.instance.removeListener(_onLocaleChanged);
    super.dispose();
  }

  void _onLocaleChanged() {
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final locale = LocalePreference.instance.locale;
    return LandingPagePreviewScreen(
      key: ValueKey('cms_page:${widget.slug}:$locale'),
      initialSlug: widget.slug,
      controlsEnabled: false,
      useDraft: false,
    );
  }
}
