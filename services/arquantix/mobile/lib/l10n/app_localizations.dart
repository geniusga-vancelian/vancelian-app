import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_fr.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
      : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('fr')
  ];

  /// Activation journey card title on home
  ///
  /// In en, this message translates to:
  /// **'Finish setting up'**
  String get activationJourneyHeadline;

  /// Activation journey card subtitle on home
  ///
  /// In en, this message translates to:
  /// **'The new era on investment in a few steps'**
  String get activationJourneySubtitle;

  /// No description provided for @activationHeroHeadline.
  ///
  /// In en, this message translates to:
  /// **'Your investment\'s new home'**
  String get activationHeroHeadline;

  /// Subtitle under hero title on pre-deposit home header
  ///
  /// In en, this message translates to:
  /// **'everyone can easily invest in a single tap'**
  String get activationPreDepositHeroTagline;

  /// No description provided for @activationHeroSubtitleVerify.
  ///
  /// In en, this message translates to:
  /// **'Complete your profile to unlock your account.'**
  String get activationHeroSubtitleVerify;

  /// No description provided for @activationHeroSubtitleDeposit.
  ///
  /// In en, this message translates to:
  /// **'Add funds to start investing.'**
  String get activationHeroSubtitleDeposit;

  /// No description provided for @activationHeroSubtitleInvest.
  ///
  /// In en, this message translates to:
  /// **'Explore opportunities and build your portfolio.'**
  String get activationHeroSubtitleInvest;

  /// No description provided for @exclusiveOfferInvestUnavailableTitle.
  ///
  /// In en, this message translates to:
  /// **'Investment unavailable'**
  String get exclusiveOfferInvestUnavailableTitle;

  /// No description provided for @exclusiveOfferInvestUnavailableBodyFunded.
  ///
  /// In en, this message translates to:
  /// **'This offer has reached its funding target.'**
  String get exclusiveOfferInvestUnavailableBodyFunded;

  /// No description provided for @exclusiveOfferInvestUnavailableBodyOther.
  ///
  /// In en, this message translates to:
  /// **'This offer is not open for investment at the moment.'**
  String get exclusiveOfferInvestUnavailableBodyOther;

  /// No description provided for @exclusiveOfferClose.
  ///
  /// In en, this message translates to:
  /// **'Close'**
  String get exclusiveOfferClose;

  /// No description provided for @exclusiveOfferInvestCtaDefault.
  ///
  /// In en, this message translates to:
  /// **'Invest'**
  String get exclusiveOfferInvestCtaDefault;

  /// No description provided for @exclusiveOfferDocuments.
  ///
  /// In en, this message translates to:
  /// **'Documents'**
  String get exclusiveOfferDocuments;

  /// No description provided for @exclusiveOfferGallery.
  ///
  /// In en, this message translates to:
  /// **'Gallery'**
  String get exclusiveOfferGallery;

  /// No description provided for @exclusiveOfferVideosTitle.
  ///
  /// In en, this message translates to:
  /// **'Videos'**
  String get exclusiveOfferVideosTitle;

  /// No description provided for @exclusiveOfferVideoItemTitle.
  ///
  /// In en, this message translates to:
  /// **'Video {videoNumber}'**
  String exclusiveOfferVideoItemTitle(int videoNumber);

  /// No description provided for @exclusiveOfferFaqDefaultTitle.
  ///
  /// In en, this message translates to:
  /// **'FAQ'**
  String get exclusiveOfferFaqDefaultTitle;

  /// No description provided for @exclusiveOfferModalInfoDefaultTitle.
  ///
  /// In en, this message translates to:
  /// **'Information'**
  String get exclusiveOfferModalInfoDefaultTitle;

  /// No description provided for @exclusiveOfferFaqArticleLoadError.
  ///
  /// In en, this message translates to:
  /// **'Could not load this article.'**
  String get exclusiveOfferFaqArticleLoadError;

  /// No description provided for @exclusiveOfferFaqArticleEmptyFallback.
  ///
  /// In en, this message translates to:
  /// **'No content available.'**
  String get exclusiveOfferFaqArticleEmptyFallback;

  /// No description provided for @exclusiveOfferFaqModalClose.
  ///
  /// In en, this message translates to:
  /// **'Close'**
  String get exclusiveOfferFaqModalClose;

  /// No description provided for @exclusiveOfferStepsMilestoneDay.
  ///
  /// In en, this message translates to:
  /// **'Step {stepNumber}'**
  String exclusiveOfferStepsMilestoneDay(int stepNumber);

  /// No description provided for @exclusiveOfferStepsCountLabel.
  ///
  /// In en, this message translates to:
  /// **'{count} steps'**
  String exclusiveOfferStepsCountLabel(int count);

  /// No description provided for @exclusiveOfferVirtualTourEmbedInvalid.
  ///
  /// In en, this message translates to:
  /// **'Unable to display the virtual tour: invalid or unsupported URL.'**
  String get exclusiveOfferVirtualTourEmbedInvalid;

  /// No description provided for @exclusiveOfferVirtualTourOpenBrowser.
  ///
  /// In en, this message translates to:
  /// **'Open in browser'**
  String get exclusiveOfferVirtualTourOpenBrowser;

  /// Reading time of an article (e.g. "5 min read")
  ///
  /// In en, this message translates to:
  /// **'{count} min read'**
  String articleReadingTimeMinutes(int count);

  /// Prefix placed before the article author's name (e.g. "By Gael Itier")
  ///
  /// In en, this message translates to:
  /// **'By'**
  String get articleAuthorByPrefix;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'fr'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'fr':
      return AppLocalizationsFr();
  }

  throw FlutterError(
      'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
      'an issue with the localizations generation tool. Please file an issue '
      'on GitHub with a reproducible sample app and the gen-l10n configuration '
      'that was used.');
}
