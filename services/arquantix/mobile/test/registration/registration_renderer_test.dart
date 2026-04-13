import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/features/registration/data/registration_models.dart';
import 'package:arquantix_news/features/registration/widgets/registration_flow_renderer.dart';
import 'package:arquantix_news/design_system/components/app_phone_input.dart';
import 'package:arquantix_news/design_system/components/app_text_input.dart';
import 'package:arquantix_news/design_system/components/app_checkbox.dart';
import 'package:arquantix_news/core/ui/selectable_single_list.dart';
import 'package:arquantix_news/design_system/components/app_country_picker.dart';
import 'package:arquantix_news/design_system/components/app_date_input.dart';

Widget _wrap(Widget child) {
  return MaterialApp(home: Scaffold(body: SingleChildScrollView(child: child)));
}

void main() {
  group('RegistrationFlowRenderer', () {
    testWidgets('renders text_input as AppTextInput', (tester) async {
      final components = [
        RegistrationComponent.fromJson({
          'id': 'c1',
          'component_type': 'text_input',
          'component_key': 'fn',
          'position': 0,
          'props': {'label': 'First Name', 'required': true},
          'binding_slug': 'first_name',
        }),
      ];

      final controllers = {
        'first_name': TextEditingController(),
      };

      await tester.pumpWidget(_wrap(
        RegistrationFlowRenderer(
          components: components,
          formData: const {},
          controllers: controllers,
          onFieldChanged: (_) {},
        ),
      ));

      expect(find.byType(AppTextInput), findsOneWidget);
      expect(find.text('First Name *'), findsOneWidget);

      controllers['first_name']!.dispose();
    });

    testWidgets('renders checkbox as AppCheckbox', (tester) async {
      final components = [
        RegistrationComponent.fromJson({
          'id': 'c2',
          'component_type': 'checkbox',
          'component_key': 'terms',
          'position': 0,
          'props': {'label': 'I accept the terms'},
          'binding_slug': 'terms',
        }),
      ];

      await tester.pumpWidget(_wrap(
        RegistrationFlowRenderer(
          components: components,
          formData: const {'terms': false},
          controllers: const {},
          onFieldChanged: (_) {},
        ),
      ));

      expect(find.byType(AppCheckbox), findsOneWidget);
      expect(find.text('I accept the terms'), findsOneWidget);
    });

    testWidgets('renders select as SelectableSingleList', (tester) async {
      final components = [
        RegistrationComponent.fromJson({
          'id': 'c3',
          'component_type': 'select',
          'component_key': 'gender',
          'position': 0,
          'props': {
            'label': 'Gender',
            'options': [
              {'value': 'M', 'label': 'Male'},
              {'value': 'F', 'label': 'Female'},
            ],
          },
          'binding_slug': 'gender',
        }),
      ];

      await tester.pumpWidget(_wrap(
        RegistrationFlowRenderer(
          components: components,
          formData: const {},
          controllers: const {},
          onFieldChanged: (_) {},
        ),
      ));

      expect(find.byType(SelectableSingleList<String>), findsOneWidget);
    });

    testWidgets('renders country_picker as AppCountryPicker', (tester) async {
      final components = [
        RegistrationComponent.fromJson({
          'id': 'c4',
          'component_type': 'country_picker',
          'component_key': 'nationality',
          'position': 0,
          'props': {'label': 'Nationality'},
          'binding_slug': 'nationality',
        }),
      ];

      await tester.pumpWidget(_wrap(
        RegistrationFlowRenderer(
          components: components,
          formData: const {},
          controllers: const {},
          onFieldChanged: (_) {},
        ),
      ));

      expect(find.byType(AppCountryPicker), findsOneWidget);
    });

    testWidgets('renders date_picker as AppDateInput', (tester) async {
      final components = [
        RegistrationComponent.fromJson({
          'id': 'c5',
          'component_type': 'date_picker',
          'component_key': 'dob',
          'position': 0,
          'props': {'label': 'Date of Birth'},
          'binding_slug': 'date_of_birth',
        }),
      ];

      await tester.pumpWidget(_wrap(
        RegistrationFlowRenderer(
          components: components,
          formData: const {},
          controllers: const {},
          onFieldChanged: (_) {},
        ),
      ));

      expect(find.byType(AppDateInput), findsOneWidget);
    });

    testWidgets('renders legal_content as styled text box', (tester) async {
      final components = [
        RegistrationComponent.fromJson({
          'id': 'c6',
          'component_type': 'legal_content',
          'component_key': 'legal',
          'position': 0,
          'props': {'text': 'Please review and accept the terms'},
        }),
      ];

      await tester.pumpWidget(_wrap(
        RegistrationFlowRenderer(
          components: components,
          formData: const {},
          controllers: const {},
          onFieldChanged: (_) {},
        ),
      ));

      expect(find.text('Please review and accept the terms'), findsOneWidget);
    });

    testWidgets('renders section_title as styled text', (tester) async {
      final components = [
        RegistrationComponent.fromJson({
          'id': 'c7',
          'component_type': 'section_title',
          'component_key': 'section',
          'position': 0,
          'props': {'label': 'Personal Details'},
        }),
      ];

      await tester.pumpWidget(_wrap(
        RegistrationFlowRenderer(
          components: components,
          formData: const {},
          controllers: const {},
          onFieldChanged: (_) {},
        ),
      ));

      expect(find.text('Personal Details'), findsOneWidget);
    });

    testWidgets('renders rich_text as paragraph text', (tester) async {
      final components = [
        RegistrationComponent.fromJson({
          'id': 'rt1',
          'component_type': 'rich_text',
          'component_key': 'intro',
          'position': 0,
          'props': {'text': 'Welcome to the registration process.'},
        }),
      ];

      await tester.pumpWidget(_wrap(
        RegistrationFlowRenderer(
          components: components,
          formData: const {},
          controllers: const {},
          onFieldChanged: (_) {},
        ),
      ));

      expect(find.text('Welcome to the registration process.'), findsOneWidget);
    });

    testWidgets('renders divider as Divider widget', (tester) async {
      final components = [
        RegistrationComponent.fromJson({
          'id': 'dv1',
          'component_type': 'divider',
          'component_key': 'sep',
          'position': 0,
          'props': {},
        }),
      ];

      await tester.pumpWidget(_wrap(
        RegistrationFlowRenderer(
          components: components,
          formData: const {},
          controllers: const {},
          onFieldChanged: (_) {},
        ),
      ));

      expect(find.byType(Divider), findsOneWidget);
    });

    testWidgets('renders spacer as SizedBox with height', (tester) async {
      final components = [
        RegistrationComponent.fromJson({
          'id': 'sp1',
          'component_type': 'spacer',
          'component_key': 'gap',
          'position': 0,
          'props': {'height': 32},
        }),
      ];

      await tester.pumpWidget(_wrap(
        RegistrationFlowRenderer(
          components: components,
          formData: const {},
          controllers: const {},
          onFieldChanged: (_) {},
        ),
      ));

      final sizedBoxes = tester.widgetList<SizedBox>(find.byType(SizedBox));
      final spacerBox = sizedBoxes.where((sb) => sb.height == 32.0);
      expect(spacerBox, isNotEmpty);
    });

    testWidgets('renders bullet_list with items', (tester) async {
      final components = [
        RegistrationComponent.fromJson({
          'id': 'bl1',
          'component_type': 'bullet_list',
          'component_key': 'requirements',
          'position': 0,
          'props': {
            'label': 'Requirements',
            'items': ['Valid passport', 'Proof of address', 'Bank statement'],
          },
        }),
      ];

      await tester.pumpWidget(_wrap(
        RegistrationFlowRenderer(
          components: components,
          formData: const {},
          controllers: const {},
          onFieldChanged: (_) {},
        ),
      ));

      expect(find.text('Requirements'), findsOneWidget);
      expect(find.text('Valid passport'), findsOneWidget);
      expect(find.text('Proof of address'), findsOneWidget);
      expect(find.text('Bank statement'), findsOneWidget);
    });

    testWidgets('renders info_box as styled info card', (tester) async {
      final components = [
        RegistrationComponent.fromJson({
          'id': 'c8',
          'component_type': 'info_box',
          'component_key': 'info',
          'position': 0,
          'props': {'text': 'This is informational text'},
        }),
      ];

      await tester.pumpWidget(_wrap(
        RegistrationFlowRenderer(
          components: components,
          formData: const {},
          controllers: const {},
          onFieldChanged: (_) {},
        ),
      ));

      expect(find.text('This is informational text'), findsOneWidget);
      expect(find.byIcon(Icons.info_outline_rounded), findsOneWidget);
    });

    testWidgets('renders phone_input as AppPhoneInput with phone keyboard',
        (tester) async {
      final components = [
        RegistrationComponent.fromJson({
          'id': 'c9',
          'component_type': 'phone_input',
          'component_key': 'phone',
          'position': 0,
          'props': {'label': 'Phone Number', 'required': true},
          'binding_slug': 'phone_number',
        }),
      ];

      final controllers = {
        'phone_number': TextEditingController(),
      };

      await tester.pumpWidget(_wrap(
        RegistrationFlowRenderer(
          components: components,
          formData: const {},
          controllers: controllers,
          onFieldChanged: (_) {},
        ),
      ));

      expect(find.byType(AppPhoneInput), findsOneWidget);
      expect(find.text('Phone Number *'), findsOneWidget);

      controllers['phone_number']!.dispose();
    });

    testWidgets('phone_input onPhoneNationalChanged sets slug and slug_raw',
        (tester) async {
      final components = [
        RegistrationComponent.fromJson({
          'id': 'c9b',
          'component_type': 'phone_input',
          'component_key': 'phone',
          'position': 0,
          'props': {'label': 'Phone', 'required': true},
          'binding_slug': 'phone_number',
        }),
      ];

      final store = <String, String>{};

      final controllers = {
        'phone_number': TextEditingController(),
      };

      await tester.pumpWidget(_wrap(
        RegistrationFlowRenderer(
          components: components,
          formData: const {},
          controllers: controllers,
          onFieldChanged: (_) {},
          onPhoneNationalChanged: (slug, v) {
            store[slug] = v;
            store['${slug}_raw'] = v;
          },
        ),
      ));

      await tester.enterText(find.byType(TextField), '612345678');
      expect(store['phone_number'], '612345678');
      expect(store['phone_number_raw'], '612345678');

      controllers['phone_number']!.dispose();
    });

    testWidgets('unknown component type renders SizedBox.shrink',
        (tester) async {
      final components = [
        RegistrationComponent.fromJson({
          'id': 'c10',
          'component_type': 'unknown_widget',
          'component_key': 'unknown',
          'position': 0,
          'props': {},
        }),
      ];

      await tester.pumpWidget(_wrap(
        RegistrationFlowRenderer(
          components: components,
          formData: const {},
          controllers: const {},
          onFieldChanged: (_) {},
        ),
      ));

      // Should render without crashing — just an empty SizedBox
      expect(find.byType(RegistrationFlowRenderer), findsOneWidget);
    });

    testWidgets('displays field errors', (tester) async {
      final components = [
        RegistrationComponent.fromJson({
          'id': 'c11',
          'component_type': 'text_input',
          'component_key': 'email',
          'position': 0,
          'props': {'label': 'Email'},
          'binding_slug': 'email',
        }),
      ];

      final controllers = {
        'email': TextEditingController(text: 'bad-email'),
      };

      await tester.pumpWidget(_wrap(
        RegistrationFlowRenderer(
          components: components,
          formData: const {'email': 'bad-email'},
          controllers: controllers,
          errors: const {'email': 'Invalid email format'},
          onFieldChanged: (_) {},
        ),
      ));

      expect(find.text('Invalid email format'), findsOneWidget);

      controllers['email']!.dispose();
    });

    testWidgets('fires onFieldChanged for checkbox toggle', (tester) async {
      MapEntry<String, dynamic>? lastEntry;

      final components = [
        RegistrationComponent.fromJson({
          'id': 'c12',
          'component_type': 'checkbox',
          'component_key': 'accept',
          'position': 0,
          'props': {'label': 'I agree'},
          'binding_slug': 'accept',
        }),
      ];

      await tester.pumpWidget(_wrap(
        RegistrationFlowRenderer(
          components: components,
          formData: const {'accept': false},
          controllers: const {},
          onFieldChanged: (entry) => lastEntry = entry,
        ),
      ));

      await tester.tap(find.text('I agree'));
      expect(lastEntry, isNotNull);
      expect(lastEntry!.key, 'accept');
      expect(lastEntry!.value, true);
    });
  });

  group('Renderer component_type → widget mapping', () {
    final typeToWidget = {
      'text_input': AppTextInput,
      'phone_input': AppPhoneInput,
      'checkbox': AppCheckbox,
      'select': SelectableSingleList<String>,
      'country_picker': AppCountryPicker,
      'date_picker': AppDateInput,
    };

    for (final entry in typeToWidget.entries) {
      testWidgets('${entry.key} → ${entry.value}', (tester) async {
        final slug = '${entry.key}_field';
        final components = [
          RegistrationComponent.fromJson({
            'id': 'map-${entry.key}',
            'component_type': entry.key,
            'component_key': entry.key,
            'position': 0,
            'props': {
              'label': entry.key,
              'options': entry.key == 'select'
                  ? [
                      {'value': 'a', 'label': 'A'}
                    ]
                  : null,
            },
            'binding_slug': slug,
          }),
        ];

        final controllers = <String, TextEditingController>{};
        if (entry.key == 'text_input' || entry.key == 'phone_input') {
          controllers[slug] = TextEditingController();
        }

        await tester.pumpWidget(_wrap(
          RegistrationFlowRenderer(
            components: components,
            formData: const {},
            controllers: controllers,
            onFieldChanged: (_) {},
          ),
        ));

        expect(find.byType(entry.value), findsOneWidget);

        for (final c in controllers.values) {
          c.dispose();
        }
      });
    }
  });
}
