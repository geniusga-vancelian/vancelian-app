import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/design_system/components/app_country_picker.dart';
import 'package:arquantix_news/design_system/components/app_text_input.dart';
import 'package:arquantix_news/features/registration/data/registration_api.dart';
import 'package:arquantix_news/features/registration/data/registration_models.dart';
import 'package:arquantix_news/features/registration/widgets/address_search_modal.dart';
import 'package:arquantix_news/features/registration/widgets/registration_address_step.dart';

class _FakeAddressRegistrationApi extends RegistrationApi {
  _FakeAddressRegistrationApi() : super(baseUrl: 'http://test.local');

  String? lastAutocompleteCountryIso2;
  List<String>? lastAutocompleteAllowedCountries;
  String? lastDetailsPlaceId;
  int autocompleteCallCount = 0;

  bool returnPredictions = false;

  @override
  Future<ApiResult<Map<String, dynamic>>> addressAutocomplete(
    String q, {
    String? region,
    List<String>? allowedCountriesIso2,
    String? countryIso2,
  }) async {
    autocompleteCallCount++;
    lastAutocompleteCountryIso2 = countryIso2;
    lastAutocompleteAllowedCountries = allowedCountriesIso2;
    if (!returnPredictions) {
      return const ApiResult(
        statusCode: 200,
        data: {'predictions': <dynamic>[]},
      );
    }
    return ApiResult(
      statusCode: 200,
      data: {
        'predictions': <Map<String, dynamic>>[
          {
            'description': 'Rue du Test 1, 1000 Bruxelles',
            'place_id': 'place_test_1',
          },
        ],
      },
    );
  }

  @override
  Future<ApiResult<Map<String, dynamic>>> addressDetails(
    String placeId, {
    List<String>? allowedCountriesIso2,
    String? countryIso2,
  }) async {
    lastDetailsPlaceId = placeId;
    return ApiResult(
      statusCode: 200,
      data: <String, dynamic>{
        'address_line_1': 'Rue du Test 1',
        'postal_code': '1000',
        'city': 'Bruxelles',
        'country': 'BE',
        'google_place_id': placeId,
      },
    );
  }
}

Widget _wrap(Widget child) {
  return MaterialApp(
    home: Scaffold(
      body: SingleChildScrollView(child: child),
    ),
  );
}

RegistrationComponent _addressStepComponent({
  String id = 'addr-1',
  bool searchEnabled = true,
}) {
  return RegistrationComponent.fromJson({
    'id': id,
    'component_type': 'address_step',
    'component_key': 'address',
    'position': 0,
    'props': <String, dynamic>{
      'search_enabled': searchEnabled,
      'search_min_chars': 2,
      'address_line_2_optional': true,
    },
  });
}

RegistrationComponent _addressStepWithAllowedCountries(
  List<dynamic> allowedCountries, {
  String id = 'addr-allowed',
}) {
  return RegistrationComponent.fromJson({
    'id': id,
    'component_type': 'address_step',
    'component_key': 'address',
    'position': 0,
    'props': <String, dynamic>{
      'search_enabled': true,
      'search_min_chars': 2,
      'address_line_2_optional': true,
      'allowed_countries': allowedCountries,
    },
  });
}

class _FakeAutocompleteNotInAllowed extends _FakeAddressRegistrationApi {
  @override
  Future<ApiResult<Map<String, dynamic>>> addressAutocomplete(
    String q, {
    String? region,
    List<String>? allowedCountriesIso2,
    String? countryIso2,
  }) async {
    autocompleteCallCount++;
    lastAutocompleteCountryIso2 = countryIso2;
    return const ApiResult<Map<String, dynamic>>(
      statusCode: 422,
      errorCode: 'country_not_in_allowed_list',
      errorMessage: 'country is not included in allowed_countries.',
    );
  }
}

Map<String, TextEditingController> _makeControllers() => {
      'address_line_1': TextEditingController(),
      'address_line_2': TextEditingController(),
      'postal_code': TextEditingController(),
      'city': TextEditingController(),
    };

Map<String, FocusNode> _makeFocusNodes() => {
      'address_line_1': FocusNode(),
      'address_line_2': FocusNode(),
      'postal_code': FocusNode(),
      'city': FocusNode(),
    };

void _disposeAll(
  Map<String, TextEditingController> c,
  Map<String, FocusNode> f,
) {
  for (final x in c.values) {
    x.dispose();
  }
  for (final x in f.values) {
    x.dispose();
  }
}

Future<void> _openAddressSearchModalSheet(WidgetTester tester) async {
  await tester.tap(
    find.byKey(const ValueKey<String>('registration_address_search_trigger')),
  );
  await tester.pumpAndSettle();
}

/// Saisie min. dans la modale pour afficher le lien « manuel », puis tap.
Future<void> _openModalAndChooseManualEntry(WidgetTester tester) async {
  await _openAddressSearchModalSheet(tester);
  await tester.enterText(
    find.byKey(
      const ValueKey<String>('registration_address_search_modal_field'),
    ),
    'xx',
  );
  await tester.pumpAndSettle();
  await tester.tap(find.textContaining("Mon adresse n'est pas ici"));
  await tester.pumpAndSettle();
}

/// Enveloppe avec [formData] mutable pour simuler le flow (didUpdateWidget).
class _AddressStepHarness extends StatefulWidget {
  const _AddressStepHarness({
    required this.initialFormData,
    required this.comp,
    required this.api,
    this.onFormPatch,
  });

  final Map<String, dynamic> initialFormData;
  final RegistrationComponent comp;
  final RegistrationApi api;
  final void Function(Map<String, dynamic>)? onFormPatch;

  @override
  State<_AddressStepHarness> createState() => _AddressStepHarnessState();
}

class _AddressStepHarnessState extends State<_AddressStepHarness> {
  late Map<String, dynamic> _formData;
  late final Map<String, TextEditingController> _controllers;
  late final Map<String, FocusNode> _focusNodes;

  @override
  void initState() {
    super.initState();
    _formData = Map<String, dynamic>.from(widget.initialFormData);
    _controllers = _makeControllers();
    _focusNodes = _makeFocusNodes();
  }

  @override
  void dispose() {
    _disposeAll(_controllers, _focusNodes);
    super.dispose();
  }

  void replaceFormData(Map<String, dynamic> next) {
    setState(() {
      _formData = Map<String, dynamic>.from(next);
    });
  }

  @override
  Widget build(BuildContext context) {
    return RegistrationAddressStep(
      comp: widget.comp,
      formData: _formData,
      controllers: _controllers,
      focusNodes: _focusNodes,
      onFieldChanged: (e) {
        setState(() {
          _formData[e.key] = e.value;
        });
      },
      onFormPatch: (patch) {
        setState(() {
          _formData.addAll(patch);
        });
        widget.onFormPatch?.call(patch);
      },
      registrationApi: widget.api,
      errors: const {},
    );
  }
}

void main() {
  group('RegistrationAddressStep', () {
    testWidgets(
      'sans pays en session: bannière, pas de recherche ni champs adresse',
      (tester) async {
        final comp = _addressStepComponent();
        final controllers = _makeControllers();
        final focusNodes = _makeFocusNodes();

        await tester.pumpWidget(_wrap(
          RegistrationAddressStep(
            comp: comp,
            formData: const {},
            controllers: controllers,
            focusNodes: focusNodes,
            onFieldChanged: (_) {},
            onFormPatch: (_) {},
            registrationApi: _FakeAddressRegistrationApi(),
            errors: const {},
          ),
        ));
        await tester.pump();

        expect(find.byType(AppTextInput), findsNothing);
        expect(find.byType(TextField), findsNothing);
        expect(find.byType(AppCountryPicker), findsNothing);
        expect(
          find.textContaining('Country of residence should be set on the previous step'),
          findsOneWidget,
        );

        _disposeAll(controllers, focusNodes);
      },
    );

    testWidgets(
      'embedTitleAndSubtitle false : pas de titre / sous-titre dans le widget',
      (tester) async {
        final comp = RegistrationComponent.fromJson({
          'id': 'addr-embed',
          'component_type': 'address_step',
          'component_key': 'address',
          'position': 0,
          'props': <String, dynamic>{
            'title': 'Titre widget adresse',
            'subtitle': 'Sous-titre widget adresse',
            'search_enabled': true,
            'search_min_chars': 2,
            'address_line_2_optional': true,
          },
        });
        final c = _makeControllers();
        final f = _makeFocusNodes();

        await tester.pumpWidget(_wrap(
          RegistrationAddressStep(
            comp: comp,
            formData: const {'country_of_residence': 'BE'},
            controllers: c,
            focusNodes: f,
            onFieldChanged: (_) {},
            onFormPatch: (_) {},
            registrationApi: _FakeAddressRegistrationApi(),
            errors: const {},
            embedTitleAndSubtitle: false,
          ),
        ));
        await tester.pump();

        expect(find.text('Titre widget adresse'), findsNothing);
        expect(find.text('Sous-titre widget adresse'), findsNothing);
        expect(
          find.byKey(const ValueKey<String>('registration_address_search_trigger')),
          findsOneWidget,
        );

        _disposeAll(c, f);
      },
    );

    testWidgets(
      'pays BE + search: trigger visible, pas de pays à l’écran, pas de TextField principal',
      (tester) async {
        final comp = _addressStepComponent();
        final controllers = _makeControllers();
        final focusNodes = _makeFocusNodes();

        await tester.pumpWidget(_wrap(
          RegistrationAddressStep(
            comp: comp,
            formData: const {'country_of_residence': 'BE'},
            controllers: controllers,
            focusNodes: focusNodes,
            onFieldChanged: (_) {},
            onFormPatch: (_) {},
            registrationApi: _FakeAddressRegistrationApi(),
            errors: const {},
          ),
        ));
        await tester.pump();

        expect(
          find.byKey(const ValueKey<String>('registration_address_search_trigger')),
          findsOneWidget,
        );
        expect(find.byType(TextField), findsNothing);
        expect(find.byType(AppTextInput), findsNothing);
        expect(find.byType(AppCountryPicker), findsNothing);

        _disposeAll(controllers, focusNodes);
      },
    );

    testWidgets(
      'tap trigger ouvre la bottom sheet avec TextField',
      (tester) async {
        final comp = _addressStepComponent();
        final c = _makeControllers();
        final f = _makeFocusNodes();

        await tester.pumpWidget(_wrap(
          RegistrationAddressStep(
            comp: comp,
            formData: const {'country_of_residence': 'BE'},
            controllers: c,
            focusNodes: f,
            onFieldChanged: (_) {},
            onFormPatch: (_) {},
            registrationApi: _FakeAddressRegistrationApi(),
            errors: const {},
          ),
        ));
        await tester.pump();
        await _openAddressSearchModalSheet(tester);

        expect(
          find.byKey(
            const ValueKey<String>('registration_address_search_modal_field'),
          ),
          findsOneWidget,
        );

        await tester.tap(find.byKey(kAddressSearchModalCloseKey));
        await tester.pumpAndSettle();

        _disposeAll(c, f);
      },
    );

    testWidgets(
      'fermeture modale par barrière: pas de champs adresse, contrôleurs inchangés',
      (tester) async {
        final comp = _addressStepComponent();
        final c = _makeControllers();
        final f = _makeFocusNodes();

        await tester.pumpWidget(_wrap(
          RegistrationAddressStep(
            comp: comp,
            formData: const {'country_of_residence': 'BE'},
            controllers: c,
            focusNodes: f,
            onFieldChanged: (_) {},
            onFormPatch: (_) {},
            registrationApi: _FakeAddressRegistrationApi(),
            errors: const {},
          ),
        ));
        await tester.pump();
        await _openAddressSearchModalSheet(tester);

        expect(
          find.byKey(
            const ValueKey<String>('registration_address_search_modal_field'),
          ),
          findsOneWidget,
        );

        // Tap hors de la feuille (le centre du viewport peut être sur le sheet).
        await tester.tapAt(const Offset(20, 80));
        await tester.pumpAndSettle();

        expect(
          find.byKey(
            const ValueKey<String>('registration_address_search_modal_field'),
          ),
          findsNothing,
        );
        expect(find.byType(AppTextInput), findsNothing);
        expect(c['address_line_1']!.text, isEmpty);
        expect(c['postal_code']!.text, isEmpty);
        expect(c['city']!.text, isEmpty);

        _disposeAll(c, f);
      },
    );

    testWidgets(
      'ordre des champs: rue, ligne2, CP, ville (sans pays visible)',
      (tester) async {
        final comp = _addressStepComponent(searchEnabled: false);
        final controllers = _makeControllers();
        final focusNodes = _makeFocusNodes();

        await tester.pumpWidget(_wrap(
          RegistrationAddressStep(
            comp: comp,
            formData: const {'country_of_residence': 'BE'},
            controllers: controllers,
            focusNodes: focusNodes,
            onFieldChanged: (_) {},
            onFormPatch: (_) {},
            registrationApi: _FakeAddressRegistrationApi(),
            errors: const {},
          ),
        ));
        await tester.pump();

        final inputs = tester
            .widgetList<AppTextInput>(find.byType(AppTextInput))
            .toList();
        expect(inputs.length, 4);
        expect(inputs[0].label, contains('Rue'));
        expect(inputs[1].label, contains('Étage'));
        expect(inputs[2].label, contains('Code postal'));
        expect(inputs[3].label, contains('Ville'));
        expect(find.byType(AppCountryPicker), findsNothing);

        _disposeAll(controllers, focusNodes);
      },
    );

    testWidgets(
      'manuel: pas de lien sur l’écran principal; modale + saisie → lien puis 4 champs vides',
      (tester) async {
        final comp = _addressStepComponent();
        final controllers = _makeControllers();
        final focusNodes = _makeFocusNodes();

        await tester.pumpWidget(_wrap(
          RegistrationAddressStep(
            comp: comp,
            formData: const {'country_of_residence': 'BE'},
            controllers: controllers,
            focusNodes: focusNodes,
            onFieldChanged: (_) {},
            onFormPatch: (_) {},
            registrationApi: _FakeAddressRegistrationApi(),
            errors: const {},
          ),
        ));
        await tester.pump();

        expect(find.textContaining("Mon adresse n'est pas ici"), findsNothing);
        await _openModalAndChooseManualEntry(tester);

        expect(find.byType(AppTextInput), findsNWidgets(4));
        expect(controllers['address_line_1']!.text, isEmpty);
        expect(controllers['postal_code']!.text, isEmpty);
        expect(controllers['city']!.text, isEmpty);

        _disposeAll(controllers, focusNodes);
      },
    );

    testWidgets('bannière quand pays de session absent', (tester) async {
      final comp = _addressStepComponent();
      final controllers = _makeControllers();
      final focusNodes = _makeFocusNodes();

      await tester.pumpWidget(_wrap(
        RegistrationAddressStep(
          comp: comp,
          formData: const {},
          controllers: controllers,
          focusNodes: focusNodes,
          onFieldChanged: (_) {},
          onFormPatch: (_) {},
          registrationApi: _FakeAddressRegistrationApi(),
          errors: const {},
        ),
      ));
      await tester.pump();

      expect(
        find.textContaining('previous step'),
        findsOneWidget,
      );

      _disposeAll(controllers, focusNodes);
    });

    testWidgets(
      'autocomplete envoie le pays ISO2 après debounce',
      (tester) async {
        final comp = _addressStepComponent();
        final controllers = _makeControllers();
        final focusNodes = _makeFocusNodes();
        final api = _FakeAddressRegistrationApi();

        await tester.pumpWidget(_wrap(
          RegistrationAddressStep(
            comp: comp,
            formData: const {'country_of_residence': 'BE'},
            controllers: controllers,
            focusNodes: focusNodes,
            onFieldChanged: (_) {},
            onFormPatch: (_) {},
            registrationApi: api,
            errors: const {},
          ),
        ));
        await tester.pump();

        await _openAddressSearchModalSheet(tester);
        await tester.enterText(
          find.byKey(
            const ValueKey<String>('registration_address_search_modal_field'),
          ),
          'br',
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 350));
        await tester.pumpAndSettle();

        expect(api.lastAutocompleteCountryIso2, 'BE');

        _disposeAll(controllers, focusNodes);
      },
    );

    testWidgets(
      'sélection suggestion → champs visibles et préremplis, pays = session',
      (tester) async {
        final comp = _addressStepComponent();
        final controllers = _makeControllers();
        final focusNodes = _makeFocusNodes();
        final api = _FakeAddressRegistrationApi()..returnPredictions = true;
        final countryWrites = <String>[];

        await tester.pumpWidget(_wrap(
          RegistrationAddressStep(
            comp: comp,
            formData: const {'country_of_residence': 'BE'},
            controllers: controllers,
            focusNodes: focusNodes,
            onFieldChanged: (e) {
              if (e.key == 'country_of_residence' && e.value is String) {
                countryWrites.add(e.value as String);
              }
            },
            onFormPatch: (_) {},
            registrationApi: api,
            errors: const {},
          ),
        ));
        await tester.pump();

        await _openAddressSearchModalSheet(tester);
        await tester.enterText(
          find.byKey(
            const ValueKey<String>('registration_address_search_modal_field'),
          ),
          'ru',
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 350));
        await tester.pumpAndSettle();

        expect(find.textContaining('Rue du Test'), findsOneWidget);
        await tester.tap(find.textContaining('Rue du Test'));
        await tester.pumpAndSettle();

        expect(api.lastDetailsPlaceId, 'place_test_1');
        expect(find.byType(AppTextInput), findsNWidgets(4));
        expect(controllers['address_line_1']!.text, 'Rue du Test 1');
        expect(controllers['postal_code']!.text, '1000');
        expect(controllers['city']!.text, 'Bruxelles');
        expect(countryWrites, contains('BE'));

        _disposeAll(controllers, focusNodes);
      },
    );

    testWidgets(
      'pays session même si absent des allowed_countries du step: recherche + merge allowlist',
      (tester) async {
        final comp = _addressStepWithAllowedCountries([
          {'iso2': 'FR', 'label_en': 'France', 'label_fr': 'France'},
        ]);
        final controllers = _makeControllers();
        final focusNodes = _makeFocusNodes();
        final api = _FakeAddressRegistrationApi();

        await tester.pumpWidget(_wrap(
          RegistrationAddressStep(
            comp: comp,
            formData: const {'country_of_residence': 'BE'},
            controllers: controllers,
            focusNodes: focusNodes,
            onFieldChanged: (_) {},
            onFormPatch: (_) {},
            registrationApi: api,
            errors: const {},
          ),
        ));
        await tester.pump();

        expect(
          find.byKey(const ValueKey<String>('registration_address_search_trigger')),
          findsOneWidget,
        );
        expect(
          find.textContaining(
            'Address search is not available for this country',
          ),
          findsNothing,
        );

        await _openAddressSearchModalSheet(tester);
        await tester.enterText(
          find.byKey(
            const ValueKey<String>('registration_address_search_modal_field'),
          ),
          'br',
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 350));
        await tester.pumpAndSettle();

        expect(api.lastAutocompleteCountryIso2, 'BE');
        expect(api.lastAutocompleteAllowedCountries, ['BE', 'FR']);

        await tester.tap(find.byKey(kAddressSearchModalCloseKey));
        await tester.pumpAndSettle();

        _disposeAll(controllers, focusNodes);
      },
    );

    testWidgets(
      'section recherche: placeholder dans le trigger sans label dupliqué au-dessus',
      (tester) async {
        final comp = _addressStepComponent();
        final c = _makeControllers();
        final f = _makeFocusNodes();

        await tester.pumpWidget(_wrap(
          RegistrationAddressStep(
            comp: comp,
            formData: const {'country_of_residence': 'BE'},
            controllers: c,
            focusNodes: f,
            onFieldChanged: (_) {},
            onFormPatch: (_) {},
            registrationApi: _FakeAddressRegistrationApi(),
            errors: const {},
          ),
        ));
        await tester.pump();

        expect(find.text('Rechercher une adresse'), findsOneWidget);

        _disposeAll(c, f);
      },
    );

    testWidgets(
      'réponse API country_not_in_allowed_list: modale UX sans message backend',
      (tester) async {
        final comp = _addressStepComponent();
        final controllers = _makeControllers();
        final focusNodes = _makeFocusNodes();
        final api = _FakeAutocompleteNotInAllowed();

        await tester.pumpWidget(_wrap(
          RegistrationAddressStep(
            comp: comp,
            formData: const {'country_of_residence': 'BE'},
            controllers: controllers,
            focusNodes: focusNodes,
            onFieldChanged: (_) {},
            onFormPatch: (_) {},
            registrationApi: api,
            errors: const {},
          ),
        ));
        await tester.pump();

        await _openAddressSearchModalSheet(tester);
        await tester.enterText(
          find.byKey(
            const ValueKey<String>('registration_address_search_modal_field'),
          ),
          'br',
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 350));
        await tester.pumpAndSettle();

        expect(api.autocompleteCallCount, 1);
        expect(
          find.textContaining(
            'Address search is not available for this country',
          ),
          findsWidgets,
        );
        expect(find.textContaining('country is not included'), findsNothing);

        _disposeAll(controllers, focusNodes);
      },
    );

    testWidgets(
      'changement de pays en session (retour arrière): reset recherche et champs masqués',
      (tester) async {
        final comp = _addressStepComponent();
        final api = _FakeAddressRegistrationApi();

        await tester.pumpWidget(_wrap(
          _AddressStepHarness(
            initialFormData: {'country_of_residence': 'BE'},
            comp: comp,
            api: api,
          ),
        ));
        await tester.pump();

        expect(find.textContaining("Mon adresse n'est pas ici"), findsNothing);
        await _openModalAndChooseManualEntry(tester);
        expect(find.byType(AppTextInput), findsNWidgets(4));

        await tester.enterText(find.byType(AppTextInput).first, '10 rue X');
        await tester.pump();

        await _openAddressSearchModalSheet(tester);
        await tester.enterText(
          find.byKey(
            const ValueKey<String>('registration_address_search_modal_field'),
          ),
          'xyz',
        );
        await tester.pump();
        await tester.tap(find.byKey(kAddressSearchModalCloseKey));
        await tester.pumpAndSettle();

        final harnessState = tester.state<_AddressStepHarnessState>(
          find.byType(_AddressStepHarness),
        );
        harnessState.replaceFormData({'country_of_residence': 'FR'});
        await tester.pumpAndSettle();

        expect(find.byType(AppTextInput), findsNothing);
        final step = tester.widget<RegistrationAddressStep>(
          find.byType(RegistrationAddressStep),
        );
        expect(step.controllers['address_line_1']!.text, isEmpty);
        expect(find.byType(TextField), findsNothing);
      },
    );
  });
}
