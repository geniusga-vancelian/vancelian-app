import 'remote_strings_service.dart';

/// Pont entre le service d'overrides remote et les strings ARB compilées.
///
/// Pattern explicite façon `i18next` : on passe **toujours** la valeur ARB
/// compilée en `fallback`. Si un override remote existe pour [key], il est
/// utilisé ; sinon on retourne le `fallback` (zero-crash garanti).
///
/// Usage typique dans un widget :
/// ```dart
/// final l10n = AppLocalizations.of(context)!;
/// Text(
///   tr(
///     key: 'module.exclusive_offer.cta.invest',
///     fallback: l10n.exclusiveOfferInvestCtaDefault,
///   ),
/// );
/// ```
///
/// Pour les strings sans équivalent ARB (entièrement nouveaux), passer
/// directement la valeur EN comme `fallback`.
///
/// **Réactivité** : le widget englobant doit être un descendant de
/// `ListenableBuilder(listenable: RemoteStringsService.instance, ...)` (déjà
/// branché dans `App` via `Listenable.merge`).
String tr({required String key, required String fallback}) {
  final override = RemoteStringsService.instance.lookup(key);
  if (override != null && override.isNotEmpty) return override;
  return fallback;
}

/// Variante avec interpolation simple `{name}` → valeur. ICU n'est pas
/// requis ici (le pluriel/select reste géré par l'ARB compilé). Utile pour
/// remplacer un placeholder dans un override remote.
String trInterp({
  required String key,
  required String fallback,
  Map<String, String> args = const {},
}) {
  var s = tr(key: key, fallback: fallback);
  args.forEach((k, v) {
    s = s.replaceAll('{$k}', v);
  });
  return s;
}
