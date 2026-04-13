import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/features/registration/data/registration_form_hydration.dart';
import 'package:arquantix_news/features/registration/data/registration_models.dart';

void main() {
  group('hydrateRegistrationFormData', () {
    test(
      'inclut country_of_residence depuis collectedData même si l’écran courant est address_step seul',
      () {
        final state = RegistrationSessionState(
          sessionId: 's1',
          status: 'in_progress',
          flowVersion: 1,
          progressPercent: 0.5,
          isLastScreen: false,
          collectedData: <String, dynamic>{
            'country_of_residence': 'BE',
          },
          screen: RegistrationScreen(
            id: 'scr_addr',
            screenKey: 'home_address',
            title: 'Home address',
            subtitle: 'Enter your address',
            layoutType: 'form',
            components: [
              RegistrationComponent(
                id: 'c_addr',
                componentType: 'address_step',
                componentKey: 'addr',
                position: 0,
                props: const <String, dynamic>{},
                bindingSlug: 'address_line_1',
              ),
            ],
          ),
          stepStates: const [],
        );

        final fd = hydrateRegistrationFormData(state);

        expect(fd['country_of_residence'], 'BE');
      },
    );

    test('country_picker sur l’écran courant applique default_country si vide', () {
      final state = RegistrationSessionState(
        sessionId: 's2',
        status: 'in_progress',
        flowVersion: 1,
        progressPercent: 0.1,
        isLastScreen: false,
        collectedData: <String, dynamic>{},
        screen: RegistrationScreen(
          id: 'scr_c',
          screenKey: 'country',
          title: 'Country',
          layoutType: 'form',
          components: [
            RegistrationComponent(
              id: 'c1',
              componentType: 'country_picker',
              componentKey: 'co',
              position: 0,
              props: const <String, dynamic>{
                'default_country': 'FR',
              },
              bindingSlug: 'country_of_residence',
            ),
          ],
        ),
        stepStates: const [],
      );

      final fd = hydrateRegistrationFormData(state);
      expect(fd['country_of_residence'], 'FR');
    });
  });
}
