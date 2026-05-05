// Cognitive Bot v4 — Lot 7 V1.1 (2026-05-05). Tests unitaires Flutter
// pour la chaîne auto-QCM côté client :
//
//   * Parsing JSON de [AssistanceAutoQcmPayload] (cap 7, source par
//     défaut, robustesse aux clés manquantes).
//   * Parsing [AssistanceHistoryMessage] avec `message_payload.auto_qcm`
//     (compat ancienne réponse SANS la clé : pas de footer).
//   * Parsing SSE [AssistanceTurnEvent.doneAutoQcm].
//   * Widget [AutoQcmFooter] : rendu des options, tap → callback,
//     mode consommé après [selectedOptionId].
//
// Aucun appel réseau, pas de DB. Tests purement unitaires + widget.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:arquantix_news/features/search/data/chat_api.dart';
import 'package:arquantix_news/features/search/presentation/widgets/auto_qcm_footer.dart';

void main() {
  group('AssistanceAutoQcmPayload.fromJson', () {
    test('parses minimal payload', () {
      final p = AssistanceAutoQcmPayload.fromJson({
        'prompt': 'Lequel ?',
        'options': [
          {'id': 'opt_1', 'label': 'A', 'agent_hint': 'product'},
          {'id': 'opt_2', 'label': 'B'},
        ],
        'source': 'auto_promoted',
      });
      expect(p.prompt, 'Lequel ?');
      expect(p.options.length, 2);
      expect(p.options[0].label, 'A');
      expect(p.options[0].agentHint, 'product');
      expect(p.options[1].label, 'B');
      expect(p.options[1].agentHint, isNull);
      expect(p.source, 'auto_promoted');
      expect(p.truncated, false);
    });

    test('caps options to kMaxOptions=7', () {
      final p = AssistanceAutoQcmPayload.fromJson({
        'prompt': '?',
        'options': [
          for (var i = 0; i < 10; i++)
            {'id': 'opt_$i', 'label': 'Option $i'},
        ],
      });
      expect(p.options.length, AssistanceAutoQcmPayload.kMaxOptions);
      expect(p.options.length, 7);
      expect(p.options.last.label, 'Option 6');
    });

    test('default source is auto_promoted when missing', () {
      final p = AssistanceAutoQcmPayload.fromJson({
        'prompt': '?',
        'options': [
          {'id': 'a', 'label': 'A'},
        ],
      });
      expect(p.source, 'auto_promoted');
    });

    test('truncated flag is parsed', () {
      final p = AssistanceAutoQcmPayload.fromJson({
        'prompt': '?',
        'options': [
          {'id': 'a', 'label': 'A'},
        ],
        'truncated': true,
      });
      expect(p.truncated, true);
    });

    test('isEmpty when no options', () {
      final p = AssistanceAutoQcmPayload.fromJson({
        'prompt': '?',
        'options': const [],
      });
      expect(p.isEmpty, true);
    });
  });

  group('AssistanceHistoryMessage with auto_qcm', () {
    test('parses auto_qcm from message_payload', () {
      final msg = AssistanceHistoryMessage.fromJson({
        'id': 'm1',
        'turn_index': 4,
        'role': 'assistant',
        'content': 'Voici les options ...\n1. A\n2. B\n3. C\nLequel ?',
        'created_at': '2026-05-05T08:00:00Z',
        'agent_used': 'product',
        'message_type': 'text',
        'message_payload': {
          'auto_qcm': {
            'prompt': 'Lequel t\'intéresse ?',
            'options': [
              {'id': 'auto_qcm_1', 'label': 'A', 'agent_hint': 'product'},
              {'id': 'auto_qcm_2', 'label': 'B', 'agent_hint': 'product'},
              {'id': 'auto_qcm_3', 'label': 'C', 'agent_hint': 'product'},
            ],
            'source': 'auto_promoted',
          },
        },
      });
      expect(msg.hasAutoQcm, true);
      expect(msg.autoQcmPayload!.options.length, 3);
      expect(msg.autoQcmPayload!.options.first.label, 'A');
      expect(msg.messageType, 'text');
      // pas de choicesPayload : auto_qcm n'est PAS un message de type
      // choices, juste un footer annexé.
      expect(msg.choicesPayload, isNull);
      expect(msg.isChoicesMessage, false);
    });

    test('legacy message without auto_qcm key has no footer', () {
      final msg = AssistanceHistoryMessage.fromJson({
        'id': 'm1',
        'turn_index': 0,
        'role': 'assistant',
        'content': 'Hello',
        'created_at': '2026-05-05T08:00:00Z',
        'message_type': 'text',
        'message_payload': null,
      });
      expect(msg.hasAutoQcm, false);
      expect(msg.autoQcmPayload, isNull);
    });

    test('auto_qcm with empty options is dropped (defensive)', () {
      final msg = AssistanceHistoryMessage.fromJson({
        'id': 'm1',
        'turn_index': 0,
        'role': 'assistant',
        'content': 'Hello',
        'created_at': '2026-05-05T08:00:00Z',
        'message_type': 'text',
        'message_payload': {
          'auto_qcm': {'prompt': '?', 'options': []},
        },
      });
      expect(msg.hasAutoQcm, false);
    });
  });

  group('AssistanceTurnEvent.doneAutoQcm (SSE)', () {
    test('returns payload when present in done', () {
      final ev = AssistanceTurnEvent('done', {
        'message_id': 'mid',
        'completed': true,
        'message_type': 'text',
        'auto_qcm': {
          'prompt': '?',
          'options': [
            {'id': 'opt', 'label': 'A'},
            {'id': 'opt2', 'label': 'B'},
            {'id': 'opt3', 'label': 'C'},
          ],
        },
      });
      expect(ev.doneAutoQcm, isNotNull);
      expect(ev.doneAutoQcm!.options.length, 3);
    });

    test('returns null when key absent', () {
      final ev = AssistanceTurnEvent('done', {
        'message_id': 'mid',
        'completed': true,
        'message_type': 'text',
      });
      expect(ev.doneAutoQcm, isNull);
    });

    test('returns null when options empty', () {
      final ev = AssistanceTurnEvent('done', {
        'auto_qcm': {'prompt': '?', 'options': []},
      });
      expect(ev.doneAutoQcm, isNull);
    });
  });

  group('AutoQcmFooter widget', () {
    AssistanceAutoQcmPayload _payload({int n = 3}) => AssistanceAutoQcmPayload(
          prompt: 'Lequel ?',
          options: [
            for (var i = 0; i < n; i++)
              AssistanceChoiceOption(
                id: 'opt_$i',
                label: 'Option $i',
                agentHint: 'product',
              ),
          ],
          source: 'auto_promoted',
        );

    Widget _wrap(Widget w) => MaterialApp(
          home: Scaffold(body: SingleChildScrollView(child: w)),
        );

    testWidgets('renders all options as tappable buttons', (tester) async {
      final tapped = <String>[];
      await tester.pumpWidget(
        _wrap(
          AutoQcmFooter(
            payload: _payload(n: 3),
            onOptionTapped: (opt) => tapped.add(opt.id),
          ),
        ),
      );
      expect(find.text('Option 0'), findsOneWidget);
      expect(find.text('Option 1'), findsOneWidget);
      expect(find.text('Option 2'), findsOneWidget);

      await tester.tap(find.text('Option 1'));
      await tester.pump();
      expect(tapped, ['opt_1']);
    });

    testWidgets('shows prompt as italic header', (tester) async {
      await tester.pumpWidget(
        _wrap(
          AutoQcmFooter(
            payload: _payload(n: 2),
            onOptionTapped: (_) {},
          ),
        ),
      );
      expect(find.text('Lequel ?'), findsOneWidget);
    });

    testWidgets('consumed mode disables further taps', (tester) async {
      final tapped = <String>[];
      await tester.pumpWidget(
        _wrap(
          AutoQcmFooter(
            payload: _payload(n: 3),
            selectedOptionId: 'opt_0',
            onOptionTapped: (opt) => tapped.add(opt.id),
          ),
        ),
      );
      // Le tap sur une autre option ne doit RIEN déclencher (onTap=null
      // sur les boutons consommés).
      await tester.tap(find.text('Option 1'), warnIfMissed: false);
      await tester.pump();
      expect(tapped, isEmpty);
    });

    testWidgets('empty payload renders nothing', (tester) async {
      await tester.pumpWidget(
        _wrap(
          AutoQcmFooter(
            payload: AssistanceAutoQcmPayload(
              prompt: '?',
              options: const [],
              source: 'auto_promoted',
            ),
            onOptionTapped: (_) {},
          ),
        ),
      );
      expect(find.text('?'), findsNothing);
      expect(find.byType(InkWell), findsNothing);
    });
  });
}
