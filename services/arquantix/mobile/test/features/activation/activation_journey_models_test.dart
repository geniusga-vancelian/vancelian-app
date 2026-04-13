import 'package:flutter_test/flutter_test.dart';

import 'package:arquantix_news/features/activation/domain/activation_journey_models.dart';

void main() {
  group('ActivationJourney v3', () {
    test('parse locked vs available vs in_progress', () {
      expect(ActivationStageUxStatus.parse('locked'), ActivationStageUxStatus.locked);
      expect(ActivationStageUxStatus.parse('available'), ActivationStageUxStatus.available);
      expect(ActivationStageUxStatus.parse('in_progress'), ActivationStageUxStatus.inProgress);
      expect(ActivationStageUxStatus.parse('completed'), ActivationStageUxStatus.completed);
      expect(ActivationStageUxStatus.parse('unknown_status'), ActivationStageUxStatus.locked);
    });

    test('fromJson activation_complete + completion_message', () {
      final j = ActivationJourney.fromJson({
        'config_version': 3,
        'show_module': false,
        'activation_complete': true,
        'completion_message': 'Tout est en place',
        'weighted_progress_percent': 100,
        'headline': 'H',
        'hero_subtitle': 'S',
        'remaining_steps_message': '',
        'stages': [],
      });
      expect(j.configVersion, 3);
      expect(j.showModule, false);
      expect(j.activationComplete, true);
      expect(j.completionMessage, 'Tout est en place');
      expect(j.weightedProgressPercent, 100);
    });

    test('primary CTA when deposit is next (available)', () {
      final j = ActivationJourney.fromJson({
        'config_version': 3,
        'show_module': true,
        'weighted_progress_percent': 70,
        'headline': 'Trois étapes pour investir en toute confiance',
        'hero_subtitle': '',
        'remaining_steps_message': 'Plus que 2 étapes',
        'primary_cta_label': 'Alimenter mon compte',
        'primary_cta_target_route': 'deposit',
        'stages': [
          {
            'key': 'account_verification',
            'id': 'account_verification',
            'status': 'completed',
            'weight': 0.7,
            'is_next_step': false,
            'title': 'Vérifier',
            'subtitle': '',
            'cta_label': 'Terminé',
            'target_route': 'registration_resume',
          },
          {
            'key': 'first_deposit',
            'id': 'first_deposit',
            'status': 'available',
            'weight': 0.2,
            'is_next_step': true,
            'title': 'Dépôt',
            'subtitle': '',
            'cta_label': 'Ajouter des fonds',
            'target_route': 'deposit',
          },
          {
            'key': 'first_investment',
            'id': 'first_investment',
            'status': 'locked',
            'weight': 0.1,
            'is_next_step': false,
            'title': 'Invest',
            'subtitle': '',
            'cta_label': 'Commencer',
            'target_route': 'invest_crypto',
          },
        ],
      });
      expect(j.primaryCtaLabel, 'Alimenter mon compte');
      expect(j.primaryCtaTargetRoute, 'deposit');
      final deposit = j.stages.firstWhere((s) => s.key == 'first_deposit');
      expect(deposit.uxStatus, ActivationStageUxStatus.available);
      expect(deposit.isNextStep, true);
    });
  });
}
