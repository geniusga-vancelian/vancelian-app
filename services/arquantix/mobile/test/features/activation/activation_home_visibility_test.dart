import 'package:flutter_test/flutter_test.dart';

import 'package:arquantix_news/features/activation/domain/activation_journey_models.dart';
import 'package:arquantix_news/features/activation/presentation/activation_home_visibility.dart';
import 'package:arquantix_news/features/profile/data/mobile_app_profile.dart';

ActivationJourney _journey({
  required bool showModule,
  required List<Map<String, dynamic>> stageMaps,
}) {
  return ActivationJourney.fromJson({
    'config_version': 3,
    'show_module': showModule,
    'weighted_progress_percent': 70,
    'headline': 'H',
    'hero_subtitle': 'S',
    'remaining_steps_message': '',
    'stages': stageMaps,
  });
}

void main() {
  test('My accounts hidden until first_deposit completed', () {
    final aj = _journey(
      showModule: true,
      stageMaps: [
        {
          'key': 'account_verification',
          'id': 'account_verification',
          'status': 'completed',
          'weight': 0.7,
          'is_next_step': false,
          'title': '',
          'subtitle': '',
          'cta_label': '',
          'target_route': 'registration_resume',
        },
        {
          'key': 'first_deposit',
          'id': 'first_deposit',
          'status': 'available',
          'weight': 0.2,
          'is_next_step': true,
          'title': '',
          'subtitle': '',
          'cta_label': '',
          'target_route': 'deposit',
        },
        {
          'key': 'first_investment',
          'id': 'first_investment',
          'status': 'locked',
          'weight': 0.1,
          'is_next_step': false,
          'title': '',
          'subtitle': '',
          'cta_label': '',
          'target_route': 'invest_crypto',
        },
      ],
    );
    final p = MobileAppProfile(
      initials: 'A',
      email: 'a@b.c',
      activationJourney: aj,
    );
    expect(shouldShowMyAccountsCard(p), false);
    expect(
      shouldShowMyAccountsCard(p, hasEuroCashAccount: true),
      true,
    );
    expect(shouldShowActivationModuleCard(p), true);
  });

  test('After first_deposit completed: accounts visible, activation hidden', () {
    final aj = _journey(
      showModule: true,
      stageMaps: [
        {
          'key': 'account_verification',
          'id': 'account_verification',
          'status': 'completed',
          'weight': 0.7,
          'is_next_step': false,
          'title': '',
          'subtitle': '',
          'cta_label': '',
          'target_route': 'registration_resume',
        },
        {
          'key': 'first_deposit',
          'id': 'first_deposit',
          'status': 'completed',
          'weight': 0.2,
          'is_next_step': false,
          'title': '',
          'subtitle': '',
          'cta_label': '',
          'target_route': 'deposit',
        },
        {
          'key': 'first_investment',
          'id': 'first_investment',
          'status': 'available',
          'weight': 0.1,
          'is_next_step': true,
          'title': '',
          'subtitle': '',
          'cta_label': '',
          'target_route': 'invest_crypto',
        },
      ],
    );
    final p = MobileAppProfile(
      initials: 'A',
      email: 'a@b.c',
      activationJourney: aj,
    );
    expect(shouldShowMyAccountsCard(p), true);
    expect(shouldShowActivationModuleCard(p), false);
  });
}
