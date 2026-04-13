import '../../core/phone_e164.dart';
import '../../design_system/components/app_phone_input.dart';

/// Vérification client avant la modale de confirmation (l’API reste la référence).
bool isRegistrationPhoneFormatValid(String rawNational, String isoAlpha2) {
  final raw = rawNational.trim();
  if (raw.isEmpty) return false;

  final iso = isoAlpha2.toUpperCase();
  if (iso.length != 2) return false;

  final dial = phoneDialCodeForIso(iso);
  final e164 = normalizePhoneFieldToE164(raw, dial);
  if (e164.isEmpty || !e164.startsWith('+')) return false;

  var digits = e164.substring(1).replaceAll(RegExp(r'\D'), '');
  if (digits.length < 8 || digits.length > 15) return false;

  final cc = dial.replaceAll(RegExp(r'\D'), '');
  if (cc.isEmpty || !digits.startsWith(cc)) return false;

  final nsn = digits.substring(cc.length);
  if (nsn.length < 4) return false;

  switch (iso) {
    case 'FR':
      return nsn.length == 9 && (nsn.startsWith('6') || nsn.startsWith('7'));
    default:
      return nsn.length <= 12;
  }
}
