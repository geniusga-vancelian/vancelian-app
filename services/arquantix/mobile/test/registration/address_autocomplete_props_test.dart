import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/features/registration/widgets/address_autocomplete_field.dart';

void main() {
  test('allowedIso2CodesFromProps parses iso2 map list', () {
    final codes = allowedIso2CodesFromProps({
      'allowed_countries': [
        {'iso2': 'SG', 'label_en': 'Singapore'},
        {'iso2': 'fr', 'label_en': 'France'},
      ],
    });
    expect(codes, ['FR', 'SG']);
  });

  test('allowedIso2CodesFromProps empty when missing', () {
    expect(allowedIso2CodesFromProps({}), isEmpty);
  });

  test('parseIso2CountryCode accepts BE and be', () {
    expect(parseIso2CountryCode('BE'), 'BE');
    expect(parseIso2CountryCode(' be '), 'BE');
  });

  test('parseIso2CountryCode rejects invalid', () {
    expect(parseIso2CountryCode(null), isNull);
    expect(parseIso2CountryCode(''), isNull);
    expect(parseIso2CountryCode('BEL'), isNull);
    expect(parseIso2CountryCode('12'), isNull);
    expect(parseIso2CountryCode('B2'), isNull);
  });

  test('allowedCountriesForPlacesQuery merges residence into step list', () {
    expect(
      allowedCountriesForPlacesQuery(
        allowedFromStep: ['FR', 'DE'],
        residenceIso2: 'BE',
      ),
      ['BE', 'DE', 'FR'],
    );
    expect(
      allowedCountriesForPlacesQuery(allowedFromStep: [], residenceIso2: 'FR'),
      isNull,
    );
    expect(
      allowedCountriesForPlacesQuery(
        allowedFromStep: ['fr'],
        residenceIso2: 'FR',
      ),
      ['FR'],
    );
  });

  test('detailsCountryMatchesExpectedResidence', () {
    expect(
      detailsCountryMatchesExpectedResidence('BE', {'country': 'BE'}),
      isTrue,
    );
    expect(
      detailsCountryMatchesExpectedResidence('BE', {'country': 'FR'}),
      isFalse,
    );
    expect(
      detailsCountryMatchesExpectedResidence('BE', {'country': ''}),
      isFalse,
    );
    expect(
      detailsCountryMatchesExpectedResidence('BE', <String, dynamic>{}),
      isFalse,
    );
  });
}
