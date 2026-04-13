import 'package:arquantix_news/core/session/session_lifecycle_state.dart';
import 'package:arquantix_news/core/session/session_state_machine.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  late SessionStateMachine m;

  setUp(() {
    m = SessionStateMachine.instance;
    m.resetForTest(SessionLifecycleState.anonymous);
  });

  group('login success', () {
    test('anonymous -> authenticating -> authenticatedLocked on tokens', () {
      expect(m.apply(SessionLifecycleEvent.loginFlowStarted), isTrue);
      expect(m.state, SessionLifecycleState.authenticating);
      expect(m.apply(SessionLifecycleEvent.accessTokenPersisted), isTrue);
      expect(m.state, SessionLifecycleState.authenticatedLocked);
    });
  });

  group('passcode unlock success', () {
    test('authenticatedLocked -> authenticatedReady', () {
      m.resetForTest(SessionLifecycleState.authenticatedLocked);
      expect(m.apply(SessionLifecycleEvent.passcodeUnlocked), isTrue);
      expect(m.state, SessionLifecycleState.authenticatedReady);
    });
  });

  group('Home bootstrap', () {
    test('authenticatedReady -> bootstrappingHome -> authenticatedReady', () {
      m.resetForTest(SessionLifecycleState.authenticatedReady);
      expect(m.apply(SessionLifecycleEvent.homeBootstrapStarted), isTrue);
      expect(m.state, SessionLifecycleState.bootstrappingHome);
      expect(m.apply(SessionLifecycleEvent.homeBootstrapCompleted), isTrue);
      expect(m.state, SessionLifecycleState.authenticatedReady);
    });

    test('bootstrap sans état ready: transition refusée', () {
      m.resetForTest(SessionLifecycleState.authenticatedLocked);
      expect(m.apply(SessionLifecycleEvent.homeBootstrapStarted), isFalse);
      expect(m.lastBlockedReason, isNotNull);
    });
  });

  group('refresh', () {
    test('success path (ready)', () {
      m.resetForTest(SessionLifecycleState.authenticatedReady);
      expect(m.apply(SessionLifecycleEvent.refreshStarted), isTrue);
      expect(m.state, SessionLifecycleState.refreshingToken);
      expect(m.apply(SessionLifecycleEvent.refreshSucceeded), isTrue);
      expect(m.state, SessionLifecycleState.authenticatedReady);
    });

    test('success path (locked) — revient locked sans déverrouiller', () {
      m.resetForTest(SessionLifecycleState.authenticatedLocked);
      expect(m.apply(SessionLifecycleEvent.refreshStarted), isTrue);
      expect(m.state, SessionLifecycleState.refreshingToken);
      expect(m.apply(SessionLifecycleEvent.refreshSucceeded), isTrue);
      expect(m.state, SessionLifecycleState.authenticatedLocked);
    });

    test('aborted (locked) — session conservée, état locked', () {
      m.resetForTest(SessionLifecycleState.authenticatedLocked);
      expect(m.apply(SessionLifecycleEvent.refreshStarted), isTrue);
      expect(m.apply(SessionLifecycleEvent.refreshAborted), isTrue);
      expect(m.state, SessionLifecycleState.authenticatedLocked);
    });

    test('failure -> expired puis clear', () {
      m.resetForTest(SessionLifecycleState.refreshingToken);
      expect(m.apply(SessionLifecycleEvent.refreshFailed), isTrue);
      expect(m.state, SessionLifecycleState.expired);
      expect(m.apply(SessionLifecycleEvent.tokensCleared), isTrue);
      expect(m.state, SessionLifecycleState.anonymous);
    });
  });

  group('logout', () {
    test('loggingOut -> tokensCleared -> anonymous', () {
      m.resetForTest(SessionLifecycleState.authenticatedReady);
      expect(m.apply(SessionLifecycleEvent.logoutStarted), isTrue);
      expect(m.state, SessionLifecycleState.loggingOut);
      expect(m.apply(SessionLifecycleEvent.tokensCleared), isTrue);
      expect(m.state, SessionLifecycleState.anonymous);
    });
  });

  group('hard reset', () {
    test('hardResetSecurity -> hardResetRequired -> tokensCleared -> anonymous', () {
      m.resetForTest(SessionLifecycleState.authenticatedLocked);
      expect(m.apply(SessionLifecycleEvent.hardResetSecurity), isTrue);
      expect(m.state, SessionLifecycleState.hardResetRequired);
      expect(m.apply(SessionLifecycleEvent.tokensCleared), isTrue);
      expect(m.state, SessionLifecycleState.anonymous);
    });
  });

  group('cold start', () {
    test('coldStartTokensPresent: anonymous -> authenticatedLocked', () {
      m.resetForTest(SessionLifecycleState.anonymous);
      expect(m.apply(SessionLifecycleEvent.coldStartTokensPresent), isTrue);
      expect(m.state, SessionLifecycleState.authenticatedLocked);
    });
  });

  group('guard: clearSession pas sur succès passcode', () {
    test('passcodeUnlocked ne déclenche pas tokensCleared', () {
      m.resetForTest(SessionLifecycleState.authenticatedLocked);
      m.apply(SessionLifecycleEvent.passcodeUnlocked);
      expect(m.state, SessionLifecycleState.authenticatedReady);
      expect(m.apply(SessionLifecycleEvent.tokensCleared), isTrue);
      expect(m.state, SessionLifecycleState.anonymous);
    });
  });

  group('noop tokensCleared déjà anonymous', () {
    test('apply retourne true, état inchangé', () {
      m.resetForTest(SessionLifecycleState.anonymous);
      expect(m.apply(SessionLifecycleEvent.tokensCleared, detail: 'test_noop'), isTrue);
      expect(m.state, SessionLifecycleState.anonymous);
    });
  });

  group('helpers métier', () {
    test('isAnonymous / shouldAttemptRefresh / canEnterApp', () {
      m.resetForTest(SessionLifecycleState.anonymous);
      expect(m.isAnonymous, isTrue);
      expect(m.shouldAttemptRefresh, isFalse);
      expect(m.canEnterApp, isFalse);

      m.resetForTest(SessionLifecycleState.authenticatedLocked);
      expect(m.isLocked, isTrue);
      expect(m.shouldAttemptRefresh, isTrue);
      expect(m.canEnterApp, isFalse);

      m.resetForTest(SessionLifecycleState.authenticatedReady);
      expect(m.isReady, isTrue);
      expect(m.shouldAttemptRefresh, isTrue);
      expect(m.canEnterApp, isTrue);

      m.resetForTest(SessionLifecycleState.bootstrappingHome);
      expect(m.isBootstrappingHome, isTrue);
      expect(m.canEnterApp, isTrue);
    });
  });
}
