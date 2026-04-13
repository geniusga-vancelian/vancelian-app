import 'package:flutter/foundation.dart';

import 'session_lifecycle_state.dart';

/// Machine d’état centralisée du cycle de vie session (Flutter).
///
/// - Ne remplace pas [SessionService] (I/O) ni [SessionIdentityContext] (claims).
/// - Rend les transitions **explicites** et loggables pour éviter les bugs de timing.
class SessionStateMachine extends ChangeNotifier {
  SessionStateMachine._();
  static final SessionStateMachine instance = SessionStateMachine._();

  SessionLifecycleState _state = SessionLifecycleState.anonymous;
  SessionLifecycleState get state => _state;

  /// État juste avant [SessionLifecycleState.refreshingToken] (succès / abandon y reviennent).
  SessionLifecycleState? _stateBeforeRefresh;

  /// Dernière transition refusée (debug).
  String? lastBlockedReason;

  /// Réinitialise l’état (tests uniquement).
  @visibleForTesting
  void resetForTest(SessionLifecycleState s) {
    _state = s;
    _stateBeforeRefresh = null;
    lastBlockedReason = null;
    notifyListeners();
  }

  /// Applique un événement ; retourne `true` si la transition a été acceptée.
  bool apply(SessionLifecycleEvent event, {String? detail}) {
    final from = _state;
    if (event == SessionLifecycleEvent.tokensCleared &&
        from == SessionLifecycleState.anonymous) {
      _log(
        'session_state_tokensCleared_noop_already_anonymous'
        '${detail != null ? ' ($detail)' : ''}',
      );
      return true;
    }
    final to = _nextState(from, event);
    if (to == null) {
      lastBlockedReason =
          'guard_blocked: $from + $event${detail != null ? ' ($detail)' : ''}';
      _log('session_state_guard_blocked: $lastBlockedReason');
      return false;
    }
    if (to != from) {
      _log(
        'session_state_transition: ${_name(from)} -> ${_name(to)} '
        '[$event]${detail != null ? ' $detail' : ''}',
      );
      _state = to;
      notifyListeners();
    } else {
      _log(
        'session_state_noop: ${_name(from)} [$event]${detail != null ? ' $detail' : ''}',
      );
    }
    return true;
  }

  /// Remplace l’état sans événement (ex. réconciliation cold start) — à utiliser avec parcimonie.
  void replaceState(SessionLifecycleState next, {String? reason}) {
    if (_state == next) return;
    _log(
      'session_state_replace: ${_name(_state)} -> ${_name(next)} ${reason ?? ''}',
    );
    _state = next;
    notifyListeners();
  }

  /// Bootstrap Home authentifié (jeton + état prêt).
  bool get canBootstrapHomeAuthenticated =>
      _state == SessionLifecycleState.authenticatedReady;

  /// Alias historique v1.
  bool get canStartAuthenticatedHomeBootstrap => canBootstrapHomeAuthenticated;

  /// Utilisateur peut utiliser le contenu principal (après PIN / skip unlock).
  bool get canEnterApp =>
      _state == SessionLifecycleState.authenticatedReady ||
      _state == SessionLifecycleState.bootstrappingHome;

  bool get isAnonymous => _state == SessionLifecycleState.anonymous;

  bool get isLocked => _state == SessionLifecycleState.authenticatedLocked;

  bool get isReady => _state == SessionLifecycleState.authenticatedReady;

  bool get isBootstrappingHome =>
      _state == SessionLifecycleState.bootstrappingHome;

  bool get isRefreshingToken =>
      _state == SessionLifecycleState.refreshingToken;

  /// Tenter un refresh JWT (présence RT + état compatible hors flux anonyme / expiration).
  bool get shouldAttemptRefresh =>
      _state == SessionLifecycleState.authenticatedReady ||
      _state == SessionLifecycleState.authenticatedLocked ||
      _state == SessionLifecycleState.bootstrappingHome;

  /// Bloquer chargements dashboard tant que le contrôle local (PIN) n’est pas passé.
  bool get shouldBlockAuthenticatedHomeUntilUnlock =>
      _state == SessionLifecycleState.authenticatedLocked;

  /// Session serveur considérée « présente » pour la navigation (UI).
  bool get isAuthenticatedPhase {
    switch (_state) {
      case SessionLifecycleState.authenticatedLocked:
      case SessionLifecycleState.authenticatedReady:
      case SessionLifecycleState.bootstrappingHome:
      case SessionLifecycleState.refreshingToken:
        return true;
      default:
        return false;
    }
  }

  SessionLifecycleState? _nextState(
    SessionLifecycleState from,
    SessionLifecycleEvent event,
  ) {
    switch (event) {
      case SessionLifecycleEvent.loginFlowStarted:
        if (from == SessionLifecycleState.anonymous) {
          return SessionLifecycleState.authenticating;
        }
        if (from == SessionLifecycleState.authenticating) return from;
        return null;

      case SessionLifecycleEvent.accessTokenPersisted:
        return _onAccessTokenPersisted(from);

      case SessionLifecycleEvent.passcodeUnlocked:
        if (from == SessionLifecycleState.authenticatedLocked ||
            from == SessionLifecycleState.authenticating) {
          return SessionLifecycleState.authenticatedReady;
        }
        if (from == SessionLifecycleState.authenticatedReady) return from;
        return null;

      case SessionLifecycleEvent.homeBootstrapStarted:
        if (from == SessionLifecycleState.authenticatedReady) {
          return SessionLifecycleState.bootstrappingHome;
        }
        if (from == SessionLifecycleState.bootstrappingHome) return from;
        if (from == SessionLifecycleState.anonymous) return from;
        return null;

      case SessionLifecycleEvent.homeBootstrapCompleted:
        if (from == SessionLifecycleState.bootstrappingHome) {
          return SessionLifecycleState.authenticatedReady;
        }
        return null;

      case SessionLifecycleEvent.refreshStarted:
        if (from == SessionLifecycleState.authenticatedReady ||
            from == SessionLifecycleState.bootstrappingHome ||
            from == SessionLifecycleState.authenticatedLocked) {
          _stateBeforeRefresh = from;
          return SessionLifecycleState.refreshingToken;
        }
        return null;

      case SessionLifecycleEvent.refreshSucceeded:
        if (from == SessionLifecycleState.refreshingToken) {
          final back =
              _stateBeforeRefresh ?? SessionLifecycleState.authenticatedReady;
          _stateBeforeRefresh = null;
          return back;
        }
        return null;

      case SessionLifecycleEvent.refreshFailed:
        if (from == SessionLifecycleState.refreshingToken) {
          _stateBeforeRefresh = null;
          return SessionLifecycleState.expired;
        }
        return null;

      case SessionLifecycleEvent.refreshAborted:
        if (from == SessionLifecycleState.refreshingToken) {
          final back =
              _stateBeforeRefresh ?? SessionLifecycleState.authenticatedReady;
          _stateBeforeRefresh = null;
          return back;
        }
        return null;

      case SessionLifecycleEvent.logoutStarted:
        if (from == SessionLifecycleState.anonymous) return null;
        return SessionLifecycleState.loggingOut;

      case SessionLifecycleEvent.tokensCleared:
        return _onTokensCleared(from);

      case SessionLifecycleEvent.hardResetSecurity:
        if (from == SessionLifecycleState.authenticatedLocked ||
            from == SessionLifecycleState.authenticating) {
          return SessionLifecycleState.hardResetRequired;
        }
        return null;

      case SessionLifecycleEvent.coldStartTokensPresent:
        if (from == SessionLifecycleState.anonymous) {
          return SessionLifecycleState.authenticatedLocked;
        }
        return null;
    }
  }

  SessionLifecycleState _onAccessTokenPersisted(SessionLifecycleState from) {
    switch (from) {
      case SessionLifecycleState.anonymous:
      case SessionLifecycleState.authenticating:
      case SessionLifecycleState.expired:
      case SessionLifecycleState.authError:
        return SessionLifecycleState.authenticatedLocked;
      case SessionLifecycleState.authenticatedLocked:
      case SessionLifecycleState.bootstrappingHome:
        return from;
      case SessionLifecycleState.authenticatedReady:
      case SessionLifecycleState.refreshingToken:
        return SessionLifecycleState.authenticatedReady;
      case SessionLifecycleState.loggingOut:
        return SessionLifecycleState.authenticatedLocked;
      default:
        return from;
    }
  }

  SessionLifecycleState _onTokensCleared(SessionLifecycleState from) {
    switch (from) {
      case SessionLifecycleState.refreshingToken:
        _stateBeforeRefresh = null;
        return SessionLifecycleState.anonymous;
      case SessionLifecycleState.hardResetRequired:
      case SessionLifecycleState.loggingOut:
      case SessionLifecycleState.authenticatedLocked:
      case SessionLifecycleState.authenticatedReady:
      case SessionLifecycleState.bootstrappingHome:
      case SessionLifecycleState.expired:
      case SessionLifecycleState.authError:
      case SessionLifecycleState.authenticating:
        return SessionLifecycleState.anonymous;
      case SessionLifecycleState.anonymous:
        return from;
    }
  }

  void _log(String message) {
    if (kDebugMode) {
      debugPrint('[SessionStateMachine] $message');
    }
  }

  String _name(SessionLifecycleState s) => s.name;
}
