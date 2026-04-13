import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/features/registration/data/registration_models.dart';

void main() {
  group('RegistrationComponent.fromJson', () {
    test('parses all fields correctly', () {
      final json = {
        'id': 'comp-1',
        'component_type': 'text_input',
        'component_key': 'first_name_input',
        'position': 1,
        'props': {
          'label': 'First Name',
          'required': true,
          'placeholder': 'Enter first name',
        },
        'binding_slug': 'first_name',
        'field_definition_id': 'fd-1',
        'validation': {'type': 'required'},
      };
      final comp = RegistrationComponent.fromJson(json);

      expect(comp.id, 'comp-1');
      expect(comp.componentType, 'text_input');
      expect(comp.componentKey, 'first_name_input');
      expect(comp.position, 1);
      expect(comp.label, 'First Name');
      expect(comp.isRequired, true);
      expect(comp.placeholder, 'Enter first name');
      expect(comp.bindingSlug, 'first_name');
      expect(comp.fieldDefinitionId, 'fd-1');
      expect(comp.validationRule, isNotNull);
    });

    test('handles missing/null fields gracefully', () {
      final json = <String, dynamic>{
        'component_type': 'checkbox',
      };
      final comp = RegistrationComponent.fromJson(json);

      expect(comp.id, '');
      expect(comp.componentType, 'checkbox');
      expect(comp.componentKey, '');
      expect(comp.position, 0);
      expect(comp.label, '');
      expect(comp.isRequired, false);
      expect(comp.placeholder, isNull);
      expect(comp.bindingSlug, isNull);
      expect(comp.fieldDefinitionId, isNull);
    });

    test('parses options list', () {
      final json = {
        'component_type': 'select',
        'props': {
          'options': [
            {'value': 'FR', 'label': 'France'},
            {'value': 'DE', 'label': 'Germany'},
          ],
        },
      };
      final comp = RegistrationComponent.fromJson(json);
      expect(comp.options.length, 2);
      expect(comp.options[0]['value'], 'FR');
    });
  });

  group('RegistrationScreen.fromJson', () {
    test('parses screen with components', () {
      final json = {
        'id': 'scr-1',
        'screen_key': 'personal_info_form',
        'title': 'Your Information',
        'subtitle': 'Fill in your details',
        'layout_type': 'form',
        'components': [
          {
            'id': 'c1',
            'component_type': 'text_input',
            'component_key': 'first_name',
            'position': 0,
            'props': {'label': 'First Name'},
            'binding_slug': 'first_name',
          },
          {
            'id': 'c2',
            'component_type': 'text_input',
            'component_key': 'last_name',
            'position': 1,
            'props': {'label': 'Last Name'},
            'binding_slug': 'last_name',
          },
        ],
      };
      final screen = RegistrationScreen.fromJson(json);

      expect(screen.id, 'scr-1');
      expect(screen.screenKey, 'personal_info_form');
      expect(screen.title, 'Your Information');
      expect(screen.subtitle, 'Fill in your details');
      expect(screen.layoutType, 'form');
      expect(screen.components.length, 2);
      expect(screen.components[0].componentType, 'text_input');
    });

    test('handles empty components list', () {
      final json = {
        'id': 'scr-2',
        'screen_key': 'empty',
        'title': 'Empty',
      };
      final screen = RegistrationScreen.fromJson(json);
      expect(screen.components, isEmpty);
    });

    test('parses interaction screen and payload', () {
      final json = {
        'id': 'scr-ix',
        'screen_key': 'sms_confirm',
        'title': 'Confirm your mobile number',
        'layout_type': 'form',
        'screen_type': 'interaction',
        'interaction_type': 'phone_verification_sms',
        'interaction_config': {
          'source_field_slug': 'phone_number',
          'verified_flag_slug': 'phone_verified',
          'purpose': 'verify_phone',
        },
        'interaction_payload': {
          'challenge_ready': false,
          'purpose': 'verify_phone',
          'resend_after_seconds': 30,
        },
        'components': [],
      };
      final screen = RegistrationScreen.fromJson(json);
      expect(screen.screenType, 'interaction');
      expect(screen.interactionType, 'phone_verification_sms');
      expect(screen.interactionConfig?['source_field_slug'], 'phone_number');
      expect(screen.interactionPayload?['challenge_ready'], false);
      expect(screen.interactionPayload?['resend_after_seconds'], 30);
    });
  });

  group('RegistrationStep.fromJson', () {
    test('parses all fields', () {
      final json = {
        'id': 'step-1',
        'step_key': 'personal_info',
        'title': 'Personal Information',
        'description': 'Tell us about yourself',
        'is_blocking': true,
        'status': 'in_progress',
      };
      final step = RegistrationStep.fromJson(json);

      expect(step.id, 'step-1');
      expect(step.stepKey, 'personal_info');
      expect(step.title, 'Personal Information');
      expect(step.description, 'Tell us about yourself');
      expect(step.isBlocking, true);
      expect(step.status, 'in_progress');
    });

    test('defaults is_blocking to true', () {
      final step = RegistrationStep.fromJson({'id': 'x'});
      expect(step.isBlocking, true);
    });
  });

  group('RegistrationStepState.fromJson', () {
    test('parses step state', () {
      final json = {
        'step_id': 'step-1',
        'status': 'completed',
        'started_at': '2026-03-25T10:00:00',
        'completed_at': '2026-03-25T10:05:00',
      };
      final state = RegistrationStepState.fromJson(json);

      expect(state.stepId, 'step-1');
      expect(state.status, 'completed');
      expect(state.startedAt, isNotNull);
      expect(state.completedAt, isNotNull);
    });
  });

  group('RegistrationSessionState.fromJson', () {
    test('parses full API response', () {
      final json = {
        'session_id': 'sess-abc123',
        'status': 'in_progress',
        'flow_version': 1,
        'progress_percent': 33,
        // Premier écran du step courant (souvent false au milieu d’un step)
        'is_first_screen': false,
        'is_last_screen': false,
        'current_step': {
          'id': 'step-1',
          'step_key': 'personal_info',
          'title': 'Personal Information',
          'is_blocking': true,
          'status': 'in_progress',
        },
        'current_step_status': 'in_progress',
        'screen': {
          'id': 'scr-1',
          'screen_key': 'personal_info_form',
          'title': 'Your Information',
          'layout_type': 'form',
          'components': [
            {
              'id': 'c1',
              'component_type': 'text_input',
              'component_key': 'fn',
              'position': 0,
              'props': {'label': 'First Name', 'required': true},
              'binding_slug': 'first_name',
            },
          ],
        },
        'collected_data': {
          'first_name': 'Gael',
          'last_name': 'Dupont',
        },
        'step_states': [
          {'step_id': 'step-1', 'status': 'in_progress'},
          {'step_id': 'step-2', 'status': 'not_started'},
        ],
      };

      final session = RegistrationSessionState.fromJson(json);

      expect(session.sessionId, 'sess-abc123');
      expect(session.status, 'in_progress');
      expect(session.flowVersion, 1);
      expect(session.progressPercent, 33);
      expect(session.isLastScreen, false);
      expect(session.isFirstScreen, false);
      expect(session.isCompleted, false);
      expect(session.currentStep, isNotNull);
      expect(session.currentStep!.stepKey, 'personal_info');
      expect(session.currentStepStatus, 'in_progress');
      expect(session.screen, isNotNull);
      expect(session.screen!.components.length, 1);
      expect(session.collectedData['first_name'], 'Gael');
      expect(session.stepStates.length, 2);
    });

    test('isFirstScreen true when progress 0', () {
      final session = RegistrationSessionState.fromJson({
        'session_id': 'x',
        'status': 'in_progress',
        'progress_percent': 0,
      });
      expect(session.isFirstScreen, true);
    });

    test('isFirstScreen suit is_first_screen même si progress > 0', () {
      final session = RegistrationSessionState.fromJson({
        'session_id': 'x',
        'status': 'in_progress',
        'progress_percent': 35,
        'is_first_screen': true,
      });
      expect(session.isFirstScreen, true);
    });

    test('isCompleted true when status completed', () {
      final session = RegistrationSessionState.fromJson({
        'session_id': 'x',
        'status': 'completed',
      });
      expect(session.isCompleted, true);
    });

    test('handles null screen and step gracefully', () {
      final session = RegistrationSessionState.fromJson({
        'session_id': 'x',
        'status': 'in_progress',
      });
      expect(session.screen, isNull);
      expect(session.currentStep, isNull);
      expect(session.stepStates, isEmpty);
      expect(session.collectedData, isEmpty);
    });
  });
}
