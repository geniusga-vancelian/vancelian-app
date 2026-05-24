import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/design_system/components/localisation_card.dart';

void main() {
  const kSampleIframe =
      '<iframe src="https://www.google.com/maps/embed?pb=!1m17!1m12!1m3!'
      '1d2724.472426735881!2d55.3053681642601!3d25.101453835896287!2m3!'
      '1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m2!1m1!'
      '2zMjXCsDA2JzA3LjgiTiA1NcKwMTgnMjMuNCJF!5e1!3m2!1sfr!2sae!'
      '4v1778728026269!5m2!1sfr!2sae" width="600" height="450"></iframe>';

  group('normalizeLocalisationEmbedInput', () {
    test('extracts src from iframe Google Maps embed', () {
      final url = normalizeLocalisationEmbedInput(kSampleIframe);
      expect(url.startsWith('https://www.google.com/maps/embed'), isTrue);
      expect(url.contains('!2d55.3053681642601!3d25.101453835896287'), isTrue);
    });
  });

  group('extractCoords', () {
    test('parses pb !2d{lng}!3d{lat} from raw iframe html', () {
      final c = LocalisationCard.extractCoords(kSampleIframe);
      expect(c, isNotNull);
      expect(c!.lat, closeTo(25.101453835896287, 1e-6));
      expect(c.lng, closeTo(55.3053681642601, 1e-6));
    });

    test('parses normalized embed URL without iframe wrapper', () {
      final raw = normalizeLocalisationEmbedInput(kSampleIframe);
      final c = LocalisationCard.extractCoords(raw);
      expect(c, isNotNull);
      expect(c!.lng, closeTo(55.3053681642601, 1e-6));
    });

    test('parses !3d!4d variant', () {
      const u =
          'https://www.google.com/maps/embed?pb=foo!3d48.8566!4d2.3522bar';
      final c = LocalisationCard.extractCoords(u);
      expect(c, isNotNull);
      expect(c!.lat, closeTo(48.8566, 1e-6));
      expect(c.lng, closeTo(2.3522, 1e-6));
    });

    test('@lat,lng in link', () {
      final c =
          LocalisationCard.extractCoords('https://www.google.com/maps/@25.1,55.3,17z');
      expect(c, isNotNull);
      expect(c!.lat, closeTo(25.1, 1e-6));
      expect(c.lng, closeTo(55.3, 1e-6));
    });
  });
}
