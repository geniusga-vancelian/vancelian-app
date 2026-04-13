// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get activationJourneyHeadline => 'Finish setting up';

  @override
  String get activationJourneySubtitle =>
      'The new era on investment in a few steps';

  @override
  String get activationHeroHeadline => 'Your investment\'s new home';

  @override
  String get activationPreDepositHeroTagline =>
      'everyone can easily invest in a single tap';

  @override
  String get activationHeroSubtitleVerify =>
      'Complete your profile to unlock your account.';

  @override
  String get activationHeroSubtitleDeposit => 'Add funds to start investing.';

  @override
  String get activationHeroSubtitleInvest =>
      'Explore opportunities and build your portfolio.';
}
