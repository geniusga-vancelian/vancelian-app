/// Legacy helper: combines [dialCode] with national digits (client-side E.164).
///
/// **Registration:** do not use for submit validity — the API normalizes with
/// libphonenumber from `{slug}_raw` + `{slug}_country_code`. Kept for tests or
/// non-registration display helpers.
///
/// Combines [dialCode] (e.g. `+33`) with the national digits from the text field.
///
/// - Strips spaces, dots, dashes, parentheses from [rawNational].
/// - If the value already starts with `+`, returns it unchanged (aside from
///   whitespace stripping in the national part).
/// - If the national part starts with `0`, removes that leading zero before
///   prepending the dial code (e.g. `0651624864` + `+33` → `+33651624864`).
String normalizePhoneFieldToE164(String rawNational, String dialCode) {
  var t = rawNational.trim().replaceAll(RegExp(r'[\s.\-()]'), '');
  if (t.isEmpty) return '';
  if (t.startsWith('+')) {
    return t;
  }
  if (t.startsWith('0')) {
    t = t.substring(1);
  }
  if (t.isEmpty) return '';
  final dc = dialCode.startsWith('+') ? dialCode : '+$dialCode';
  return '$dc$t';
}
