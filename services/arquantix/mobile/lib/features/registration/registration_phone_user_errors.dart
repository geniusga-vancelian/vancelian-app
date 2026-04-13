/// Maps backend `error_code` for phone validation to user-facing copy (English).
/// API may also send `message`; the app uses this map for consistent UX.
class RegistrationPhoneUserErrors {
  RegistrationPhoneUserErrors._();

  static String titleForCode(String? code) {
    switch (code) {
      case 'invalid_phone_number':
        return 'Invalid phone number';
      case 'phone_number_not_mobile':
        return 'Unsupported number';
      case 'unsupported_phone_country':
        return 'Unsupported phone number';
      case 'phone_country_mismatch':
        return 'Country code mismatch';
      default:
        return 'Invalid phone number';
    }
  }

  static String messageForCode(String? code) {
    switch (code) {
      case 'invalid_phone_number':
        return 'Please enter a valid mobile number.';
      case 'unsupported_phone_country':
        return 'This phone number is not supported for your jurisdiction.';
      case 'phone_country_mismatch':
        return 'The phone number does not match the selected country.';
      case 'phone_number_not_mobile':
        return 'Please use a mobile number that can receive SMS codes.';
      default:
        return 'Please enter a valid mobile number.';
    }
  }

  static String primaryButtonLabelForCode(String? code) => 'Got it';
}
