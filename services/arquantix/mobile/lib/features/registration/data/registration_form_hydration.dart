import 'registration_models.dart';

/// Construit la carte formulaire client à partir de [state.collectedData] et des
/// valeurs par défaut des composants de l’écran courant.
///
/// **Pourquoi tout `collectedData` ?** Les écrans ne listent que leur
/// `binding_slug` principal (ex. `address_line_1` pour `address_step`). Les
/// champs collectés aux écrans précédents (`country_of_residence`, etc.)
/// doivent rester disponibles dans le même map pour les composites et la
/// validation du CTA.
Map<String, dynamic> hydrateRegistrationFormData(
  RegistrationSessionState state,
) {
  final formData = Map<String, dynamic>.from(state.collectedData);
  final screen = state.screen;
  if (screen == null) return formData;

  for (final comp in screen.components) {
    final slug = comp.bindingSlug;
    if (slug == null) continue;
    final p = comp.props;

    if (comp.componentType == 'country_picker') {
      final empty = formData[slug] == null ||
          (formData[slug] is String && (formData[slug] as String).isEmpty);
      if (empty) {
        final d = p['default_country'] as String?;
        if (d != null && d.isNotEmpty) {
          formData[slug] = d;
        }
      }
    }

    if (comp.componentType == 'phone_input') {
      final ccKey = '${slug}_country_code';
      final emptyCc = formData[ccKey] == null ||
          (formData[ccKey] is String && (formData[ccKey] as String).isEmpty);
      if (emptyCc) {
        final cc = p['default_phone_country'] as String?;
        if (cc != null && cc.isNotEmpty) {
          formData[ccKey] = cc;
          formData['${slug}_country_iso2'] = cc;
        }
      }
      final filledCc = formData[ccKey];
      if (filledCc is String &&
          filledCc.isNotEmpty &&
          (formData['${slug}_country_iso2'] == null ||
              (formData['${slug}_country_iso2'] as String?)?.isEmpty == true)) {
        formData['${slug}_country_iso2'] = filledCc;
      }
      final rawKey = '${slug}_raw';
      final hasSlug = formData[slug] != null &&
          (formData[slug] is! String ||
              (formData[slug] as String).trim().isNotEmpty);
      if (hasSlug &&
          (formData[rawKey] == null ||
              (formData[rawKey] is String &&
                  (formData[rawKey] as String).trim().isEmpty))) {
        formData[rawKey] = formData[slug];
      }
    }
  }

  return formData;
}
