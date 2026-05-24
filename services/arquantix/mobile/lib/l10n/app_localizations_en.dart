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

  @override
  String get exclusiveOfferInvestUnavailableTitle => 'Investment unavailable';

  @override
  String get exclusiveOfferInvestUnavailableBodyFunded =>
      'This offer has reached its funding target.';

  @override
  String get exclusiveOfferInvestUnavailableBodyOther =>
      'This offer is not open for investment at the moment.';

  @override
  String get exclusiveOfferClose => 'Close';

  @override
  String get exclusiveOfferInvestCtaDefault => 'Invest';

  @override
  String get exclusiveOfferDocuments => 'Documents';

  @override
  String get exclusiveOfferGallery => 'Gallery';

  @override
  String get exclusiveOfferVideosTitle => 'Videos';

  @override
  String exclusiveOfferVideoItemTitle(int videoNumber) {
    return 'Video $videoNumber';
  }

  @override
  String get exclusiveOfferFaqDefaultTitle => 'FAQ';

  @override
  String get exclusiveOfferModalInfoDefaultTitle => 'Information';

  @override
  String get exclusiveOfferFaqArticleLoadError =>
      'Could not load this article.';

  @override
  String get exclusiveOfferFaqArticleEmptyFallback => 'No content available.';

  @override
  String get exclusiveOfferFaqModalClose => 'Close';

  @override
  String exclusiveOfferStepsMilestoneDay(int stepNumber) {
    return 'Step $stepNumber';
  }

  @override
  String exclusiveOfferStepsCountLabel(int count) {
    return '$count steps';
  }

  @override
  String get exclusiveOfferVirtualTourEmbedInvalid =>
      'Unable to display the virtual tour: invalid or unsupported URL.';

  @override
  String get exclusiveOfferVirtualTourOpenBrowser => 'Open in browser';

  @override
  String articleReadingTimeMinutes(int count) {
    return '$count min read';
  }

  @override
  String get articleAuthorByPrefix => 'By';
}
