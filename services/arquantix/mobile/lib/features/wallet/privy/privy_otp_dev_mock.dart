/// Mock OTP Privy en local (code fixe, pas d’e-mail Privy) — dart-define depuis `.env.flutter`.
class PrivyOtpDevMock {
  PrivyOtpDevMock._();

  static const bool _enabled = bool.fromEnvironment(
    'PORTAL_PRIVY_OTP_DEV_MOCK_ENABLED',
    defaultValue: false,
  );

  static const String _fixedCodeRaw = String.fromEnvironment(
    'PORTAL_PRIVY_OTP_DEV_FIXED_CODE',
    defaultValue: '111111',
  );

  static bool get isEnabled => _enabled;

  static String? get fixedCode {
    if (!_enabled) return null;
    final code = _fixedCodeRaw.trim();
    if (code.length != 6 || !RegExp(r'^\d{6}$').hasMatch(code)) return null;
    return code;
  }

  static bool isMockCode(String code) {
    final expected = fixedCode;
    if (expected == null) return false;
    return code.trim() == expected;
  }

  static String stubExternalSubject(String email) {
    return 'local-dev:${email.trim().toLowerCase()}';
  }

  static String stubAccessToken(String email) {
    return 'stub:${stubExternalSubject(email)}';
  }

  /// Hex 40 caractères déterministe (aligné web `privyOtpDevMock.ts`).
  static String _deterministicHex40(String input) {
    final norm = input.trim().toLowerCase();
    var state = norm.codeUnits.fold<int>(
      0,
      (acc, unit) => (acc * 65599 + unit) & 0x7fffffff,
    );
    final buffer = StringBuffer();
    while (buffer.length < 40) {
      state = (state * 1103515245 + 12345) & 0x7fffffff;
      buffer.write(state.toRadixString(16).padLeft(8, '0'));
    }
    return buffer.toString().substring(0, 40);
  }

  /// Adresse EVM mock unique par e-mail — pas de wallet Privy prod.
  static String mockWalletAddress(String email) {
    return '0x${_deterministicHex40(email)}';
  }

  static String mockWalletId(String email) {
    return 'local_mock_${_deterministicHex40(email).substring(0, 16)}';
  }
}
