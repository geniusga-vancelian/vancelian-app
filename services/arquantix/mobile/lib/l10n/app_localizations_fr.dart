// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for French (`fr`).
class AppLocalizationsFr extends AppLocalizations {
  AppLocalizationsFr([String locale = 'fr']) : super(locale);

  @override
  String get activationJourneyHeadline => 'Finalisez votre installation';

  @override
  String get activationJourneySubtitle =>
      'La nouvelle ère de l’investissement en quelques étapes';

  @override
  String get activationHeroHeadline =>
      'Le nouveau foyer de vos investissements';

  @override
  String get activationPreDepositHeroTagline =>
      'Investir en un seul geste, simplement.';

  @override
  String get activationHeroSubtitleVerify =>
      'Complétez votre profil pour activer votre compte.';

  @override
  String get activationHeroSubtitleDeposit =>
      'Ajoutez des fonds pour commencer à investir.';

  @override
  String get activationHeroSubtitleInvest =>
      'Découvrez les opportunités et constituez votre portefeuille.';

  @override
  String get exclusiveOfferInvestUnavailableTitle =>
      'Investissement indisponible';

  @override
  String get exclusiveOfferInvestUnavailableBodyFunded =>
      'Cette offre a atteint son objectif de financement.';

  @override
  String get exclusiveOfferInvestUnavailableBodyOther =>
      'Cette offre n\'est pas ouverte à l\'investissement pour le moment.';

  @override
  String get exclusiveOfferClose => 'Fermer';

  @override
  String get exclusiveOfferInvestCtaDefault => 'Investir';

  @override
  String get exclusiveOfferDocuments => 'Documents';

  @override
  String get exclusiveOfferGallery => 'Galerie';

  @override
  String get exclusiveOfferVideosTitle => 'Vidéos';

  @override
  String exclusiveOfferVideoItemTitle(int videoNumber) {
    return 'Vidéo $videoNumber';
  }

  @override
  String get exclusiveOfferFaqDefaultTitle => 'FAQ';

  @override
  String get exclusiveOfferModalInfoDefaultTitle => 'Information';

  @override
  String get exclusiveOfferFaqArticleLoadError =>
      'Impossible de charger le contenu de cet article.';

  @override
  String get exclusiveOfferFaqArticleEmptyFallback =>
      'Aucun contenu disponible.';

  @override
  String get exclusiveOfferFaqModalClose => 'Fermé';

  @override
  String exclusiveOfferStepsMilestoneDay(int stepNumber) {
    return 'Étape $stepNumber';
  }

  @override
  String exclusiveOfferStepsCountLabel(int count) {
    return '$count étapes';
  }

  @override
  String articleReadingTimeMinutes(int count) {
    return '$count min de lecture';
  }

  @override
  String get articleAuthorByPrefix => 'Par';
}
