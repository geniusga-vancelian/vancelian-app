/// MVP D.1.4.8 — Voice input pour le chat Assistance sur mesure.
///
/// Abstraction unique pour les 2 moteurs de transcription audio :
///
/// 1. **Native** ([NativeVoiceTranscriber], défaut) : utilise le moteur
///    de reconnaissance vocale natif iOS/Android via le package
///    `speech_to_text`. Gratuit, fonctionne offline pour FR/EN sur la
///    plupart des appareils récents, latence < 200 ms. Audio jamais
///    transmis hors de l'appareil.
///
/// 2. **Whisper** ([WhisperVoiceTranscriber]) : enregistre l'audio en
///    .m4a localement via `record`, puis l'upload vers le backend
///    Python qui appelle l'API OpenAI Whisper. Meilleure qualité,
///    mais latence réseau (~1-3 s) et coût par minute. Audio
///    transmis vers Vancelian puis OpenAI.
///
/// Le moteur est sélectionné au lancement via la variable Dart
/// `ASSISTANCE_VOICE_ENGINE` (`native` par défaut). Cf.
/// [VoiceTranscriberFactory].
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart' show kDebugMode, debugPrint;
import 'package:http/http.dart' as http;
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';

/// Code d'erreur retourné par [VoiceTranscriber.startListening] et
/// [VoiceTranscriber.stopAndTranscribe] pour communiquer un échec
/// catégorisé à l'UI sans dépendre de strings.
enum VoiceTranscriberError {
  /// L'utilisateur a refusé la permission micro (et speech sur iOS).
  permissionDenied,

  /// Le moteur natif n'est pas dispo sur cet appareil (ex. Android sans
  /// Google Services, ou simulateur trop ancien). L'UI peut proposer
  /// de basculer vers Whisper.
  engineUnavailable,

  /// Échec réseau lors de l'appel au backend (uniquement Whisper).
  networkFailure,

  /// L'audio a été capturé mais aucune phrase n'a pu être extraite
  /// (silence, bruit ambiant uniquement, etc.).
  emptyTranscript,

  /// Erreur inattendue côté plugin natif.
  internal,
}

/// Exception levée par les méthodes de [VoiceTranscriber] quand une
/// étape échoue. Le code [error] permet à l'UI d'afficher un message
/// utilisateur adapté ; [message] est utile pour les logs.
class VoiceTranscriberException implements Exception {
  const VoiceTranscriberException(this.error, [this.message]);

  final VoiceTranscriberError error;
  final String? message;

  @override
  String toString() => 'VoiceTranscriberException($error, $message)';
}

/// Interface commune aux 2 moteurs. Le cycle de vie attendu est :
///
/// 1. [initialize] (idempotent) — vérifie que le moteur est dispo.
/// 2. [startListening] — démarre la capture audio.
/// 3. Pendant la capture : l'UI peut consommer [soundLevelStream] pour
///    animer une waveform.
/// 4. Soit [stopAndTranscribe] (succès / valide), soit [cancel]
///    (abandon, audio jeté).
/// 5. Quand l'écran est démonté : [dispose].
///
/// Toutes les méthodes sont sûres à appeler dans n'importe quel ordre :
/// elles no-op si l'état courant ne le permet pas, sauf
/// [startListening] qui throw si pas initialisé.
abstract class VoiceTranscriber {
  /// Initialise le moteur sous-jacent. Doit être appelé une seule fois
  /// avant [startListening]. Idempotent (les appels suivants sont
  /// no-op). Throw [VoiceTranscriberException] si le moteur est
  /// indisponible (cf. [VoiceTranscriberError.engineUnavailable]).
  Future<void> initialize();

  /// Vérifie / demande la permission micro (et speech recognition sur
  /// iOS pour le moteur natif). Retourne `true` si la permission est
  /// accordée, `false` sinon.
  ///
  /// Doit être appelé **avant** [startListening] pour ouvrir la modale
  /// système au bon moment dans le flow utilisateur (sinon le moteur
  /// ouvrira ses propres modales pas toujours cohérentes).
  Future<bool> requestPermissions();

  /// Démarre la capture audio. Pour le moteur natif, déclenche aussi
  /// la transcription en streaming en arrière-plan (résultat final
  /// dispo via [stopAndTranscribe]). Pour Whisper, juste l'enreg.
  ///
  /// [localeId] : identifiant BCP-47 (ex. `fr_FR`, `en_US`). Le moteur
  /// natif utilise cette langue pour la transcription. Whisper l'ignore
  /// (auto-détecté côté serveur).
  Future<void> startListening({String localeId = 'fr_FR'});

  /// Stream émis pendant la capture, à fréquence ~10 Hz. Valeur entre
  /// `0.0` (silence) et `1.0` (saturation). Utilisé par l'UI pour
  /// animer la waveform.
  Stream<double> get soundLevelStream;

  /// Stoppe la capture et retourne le texte transcrit. Pour le moteur
  /// natif, c'est instantané (la transcription a déjà eu lieu en
  /// streaming). Pour Whisper, déclenche l'upload + appel API
  /// (latence ~1-3 s, peut être annulé via [cancel]).
  ///
  /// Throw [VoiceTranscriberException] avec [VoiceTranscriberError.emptyTranscript]
  /// si le résultat est vide. Throw avec [VoiceTranscriberError.networkFailure]
  /// pour Whisper en cas d'erreur réseau.
  Future<String> stopAndTranscribe();

  /// Annule la capture en cours et l'éventuelle transcription Whisper
  /// pending. Idempotent. Aucune exception levée — c'est l'utilisateur
  /// qui annule volontairement, on ne veut surtout pas le bloquer.
  Future<void> cancel();

  /// Libère les ressources natives. Doit être appelé au dispose de
  /// l'écran qui possède le transcriber. Après dispose, l'instance
  /// n'est plus utilisable.
  Future<void> dispose();
}

/// Choix du moteur de transcription, lu au lancement depuis la
/// variable Dart `ASSISTANCE_VOICE_ENGINE` :
/// - `native` (défaut, ou valeur invalide) → [NativeVoiceTranscriber]
/// - `whisper` → [WhisperVoiceTranscriber]
enum VoiceEngine {
  native,
  whisper;

  static VoiceEngine fromString(String? raw) {
    switch (raw?.toLowerCase()) {
      case 'whisper':
        return VoiceEngine.whisper;
      case 'native':
      case '':
      case null:
        return VoiceEngine.native;
      default:
        // Valeur inconnue → on retombe sur native silencieusement.
        // L'UI peut afficher un warning si elle veut.
        return VoiceEngine.native;
    }
  }
}

/// Factory qui produit le bon [VoiceTranscriber] selon la
/// configuration. Centralise la lecture de la variable d'env pour
/// éviter de dupliquer le `String.fromEnvironment` partout.
class VoiceTranscriberFactory {
  /// Variable Dart compile-time qui choisit le moteur.
  /// Valeurs : `native` (défaut) | `whisper`. Cf. [VoiceEngine].
  ///
  /// Exemple : `flutter run --dart-define=ASSISTANCE_VOICE_ENGINE=whisper`
  static const String _engineEnv = String.fromEnvironment(
    'ASSISTANCE_VOICE_ENGINE',
    defaultValue: 'native',
  );

  /// Moteur sélectionné au lancement. Constant pour toute la durée de
  /// vie de l'app — pas de switch à chaud (un restart est requis).
  static final VoiceEngine engine = VoiceEngine.fromString(_engineEnv);

  /// Construit une nouvelle instance du moteur sélectionné. Le caller
  /// est responsable du cycle de vie (init / dispose).
  static VoiceTranscriber create() {
    switch (engine) {
      case VoiceEngine.native:
        return NativeVoiceTranscriber();
      case VoiceEngine.whisper:
        return WhisperVoiceTranscriber();
    }
  }
}

/// Implémentation native via `speech_to_text` (iOS Speech Framework /
/// Android SpeechRecognizer). Audio jamais transmis hors de l'appareil.
class NativeVoiceTranscriber implements VoiceTranscriber {
  NativeVoiceTranscriber();

  final stt.SpeechToText _speech = stt.SpeechToText();
  final StreamController<double> _soundLevelCtrl =
      StreamController<double>.broadcast();

  bool _initialized = false;
  String _lastTranscript = '';
  Completer<String>? _stopCompleter;

  @override
  Stream<double> get soundLevelStream => _soundLevelCtrl.stream;

  @override
  Future<void> initialize() async {
    if (_initialized) return;
    final ok = await _speech.initialize(
      onError: (err) {
        // Fail-safe : si on attend un résultat et qu'une erreur
        // arrive, on complète avec une exception au lieu de bloquer.
        final completer = _stopCompleter;
        if (completer != null && !completer.isCompleted) {
          completer.completeError(
            VoiceTranscriberException(
              VoiceTranscriberError.internal,
              'speech_to_text error: ${err.errorMsg}',
            ),
          );
          _stopCompleter = null;
        }
      },
      onStatus: (_) {
        // Pas d'usage métier pour l'instant. On pourrait logger.
      },
    );
    if (!ok) {
      throw const VoiceTranscriberException(
        VoiceTranscriberError.engineUnavailable,
        'speech_to_text initialize() returned false',
      );
    }
    _initialized = true;
  }

  @override
  Future<bool> requestPermissions() async {
    // Fix D.1.4.8 — sur iOS 18+, `permission_handler` peut retourner
    // `denied` alors que la permission est vraiment accordée
    // (incohérence entre AVAudioSession.recordPermission et le cache
    // du plugin). On interroge donc EN PRIORITÉ
    // `SpeechToText.hasPermission` qui appelle directement
    // `SFSpeechRecognizer.authorizationStatus` + `AVAudioSession.
    // recordPermission` côté natif. Si elle dit `true`, on fait
    // confiance et on continue, même si permission_handler dirait
    // `denied` ailleurs.
    if (kDebugMode) {
      debugPrint('[voice/native] checking _speech.hasPermission ...');
    }
    final hasNative = await _speech.hasPermission;
    if (kDebugMode) {
      debugPrint('[voice/native] _speech.hasPermission = $hasNative');
    }
    if (hasNative) return true;
    // Fallback : permission_handler peut éventuellement déclencher la
    // modale système si pas encore demandée.
    return _checkOrRequestMicrophonePermission(label: 'native');
  }

  @override
  Future<void> startListening({String localeId = 'fr_FR'}) async {
    if (!_initialized) {
      throw const VoiceTranscriberException(
        VoiceTranscriberError.internal,
        'startListening called before initialize',
      );
    }
    _lastTranscript = '';
    await _speech.listen(
      localeId: localeId,
      onResult: (result) {
        // On accumule au fur et à mesure : `recognizedWords` contient
        // toujours le texte courant complet (partial → final).
        _lastTranscript = result.recognizedWords;
        // Si un stop est en attente et que c'est le résultat final,
        // on complète le Future.
        final completer = _stopCompleter;
        if (result.finalResult && completer != null && !completer.isCompleted) {
          completer.complete(_lastTranscript);
          _stopCompleter = null;
        }
      },
      onSoundLevelChange: (level) {
        // `level` est en dB (typiquement entre -2 et 10 sur device).
        // On normalise grossièrement vers [0, 1] pour la waveform.
        // Plage observée : ~ -2 (silence) à ~ 10 (parole forte).
        final normalized = ((level + 2.0) / 12.0).clamp(0.0, 1.0);
        if (!_soundLevelCtrl.isClosed) {
          _soundLevelCtrl.add(normalized);
        }
      },
      listenOptions: stt.SpeechListenOptions(
        partialResults: true,
        cancelOnError: false,
        listenMode: stt.ListenMode.dictation,
      ),
    );
  }

  @override
  Future<String> stopAndTranscribe() async {
    if (!_speech.isListening) {
      // Stop appelé alors que le moteur n'écoute plus (timeout, ou
      // double-stop). On retourne ce qu'on a, ou on throw si vide.
      if (_lastTranscript.trim().isEmpty) {
        throw const VoiceTranscriberException(
          VoiceTranscriberError.emptyTranscript,
          'no audio captured',
        );
      }
      return _lastTranscript;
    }
    // On arme un completer puis on stoppe : `onResult(finalResult=true)`
    // viendra le compléter (ou onError fera completeError).
    final completer = Completer<String>();
    _stopCompleter = completer;
    await _speech.stop();
    final transcript = await completer.future;
    if (transcript.trim().isEmpty) {
      throw const VoiceTranscriberException(
        VoiceTranscriberError.emptyTranscript,
        'transcription returned empty string',
      );
    }
    return transcript;
  }

  @override
  Future<void> cancel() async {
    final completer = _stopCompleter;
    _stopCompleter = null;
    if (_speech.isListening) {
      await _speech.cancel();
    }
    _lastTranscript = '';
    if (completer != null && !completer.isCompleted) {
      // Si quelqu'un attendait stopAndTranscribe au moment du cancel,
      // on le débloque proprement plutôt que de le laisser pendre.
      completer.completeError(
        const VoiceTranscriberException(
          VoiceTranscriberError.emptyTranscript,
          'cancelled by user',
        ),
      );
    }
  }

  @override
  Future<void> dispose() async {
    await cancel();
    await _soundLevelCtrl.close();
    _initialized = false;
  }
}

/// Implémentation Whisper : enregistre l'audio en .m4a localement via
/// `record`, puis upload vers `POST /api/mobile/flutter/assistance/voice/transcribe`
/// qui forward vers le backend Python qui appelle l'API OpenAI Whisper.
class WhisperVoiceTranscriber implements VoiceTranscriber {
  WhisperVoiceTranscriber();

  final AudioRecorder _recorder = AudioRecorder();
  final StreamController<double> _soundLevelCtrl =
      StreamController<double>.broadcast();

  bool _initialized = false;
  String? _currentRecordingPath;
  Timer? _amplitudeTimer;
  http.Client? _activeUploadClient;

  @override
  Stream<double> get soundLevelStream => _soundLevelCtrl.stream;

  @override
  Future<void> initialize() async {
    // AudioRecorder n'a pas d'init explicite, juste hasPermission et
    // start. On marque initialized pour cohérence avec l'interface.
    _initialized = true;
  }

  @override
  Future<bool> requestPermissions() async {
    // Fix D.1.4.8 — sur iOS 18+, `permission_handler` peut retourner
    // `denied` alors que `AVAudioSession.recordPermission` dit
    // `granted`. Le package `record` interroge directement
    // AVAudioSession via son code natif Swift, donc plus fiable.
    if (kDebugMode) {
      debugPrint('[voice/whisper] checking _recorder.hasPermission(request:false) ...');
    }
    // `request: false` = on ne déclenche PAS la modale système si pas
    // encore répondue. Permet de distinguer "vraiment denied" de
    // "jamais demandé".
    final hasNativeWithoutRequest =
        await _recorder.hasPermission(request: false);
    if (kDebugMode) {
      debugPrint('[voice/whisper] _recorder.hasPermission(request:false) = $hasNativeWithoutRequest');
    }
    if (hasNativeWithoutRequest) return true;

    // Pas accordée d'après record → on demande explicitement (modale
    // système si pas encore répondue, sinon no-op et même retour).
    if (kDebugMode) {
      debugPrint('[voice/whisper] requesting via _recorder.hasPermission(request:true) ...');
    }
    final hasNativeAfterRequest = await _recorder.hasPermission();
    if (kDebugMode) {
      debugPrint('[voice/whisper] _recorder.hasPermission(request:true) = $hasNativeAfterRequest');
    }
    if (hasNativeAfterRequest) return true;

    // Dernier recours : permission_handler (utile si record est buggé
    // sur une version d'iOS particulière).
    return _checkOrRequestMicrophonePermission(label: 'whisper-fallback');
  }

  @override
  Future<void> startListening({String localeId = 'fr_FR'}) async {
    if (!_initialized) {
      throw const VoiceTranscriberException(
        VoiceTranscriberError.internal,
        'startListening called before initialize',
      );
    }
    // m4a (aacLc) : compact, supporté nativement iOS+Android,
    // accepté par l'API OpenAI Whisper.
    final tempDir = Directory.systemTemp.path;
    final filename = 'vancelian_voice_${DateTime.now().millisecondsSinceEpoch}.m4a';
    final path = '$tempDir/$filename';
    _currentRecordingPath = path;

    await _recorder.start(
      const RecordConfig(
        encoder: AudioEncoder.aacLc,
        sampleRate: 16000, // Whisper attend 16 kHz idéalement.
        numChannels: 1,
      ),
      path: path,
    );

    // Polling de l'amplitude pour la waveform — `record` n'expose pas
    // de stream natif, on poll à 10 Hz comme fait l'UI ChatGPT.
    _amplitudeTimer?.cancel();
    _amplitudeTimer = Timer.periodic(
      const Duration(milliseconds: 100),
      (_) async {
        try {
          final amp = await _recorder.getAmplitude();
          // amp.current est en dBFS (négatif, 0 = max). Plage
          // typique : -50 (silence) à -2 (parole forte).
          final normalized = ((amp.current + 50.0) / 48.0).clamp(0.0, 1.0);
          if (!_soundLevelCtrl.isClosed) {
            _soundLevelCtrl.add(normalized);
          }
        } catch (_) {
          // Silencieux : si le recorder est arrêté entre 2 ticks.
        }
      },
    );
  }

  @override
  Future<String> stopAndTranscribe() async {
    _amplitudeTimer?.cancel();
    _amplitudeTimer = null;

    final path = await _recorder.stop();
    if (path == null || path.isEmpty) {
      throw const VoiceTranscriberException(
        VoiceTranscriberError.emptyTranscript,
        'no audio file produced',
      );
    }

    // Upload du fichier vers le backend.
    final uri = Uri.parse(Config.mobileAssistanceVoiceTranscribeUrl);
    final headers = await SessionBearerHttp.jsonHeadersAppScoped(
      uri: uri,
      debugTag: 'assistance_voice_transcribe',
      // Pas de Content-Type forcé : MultipartRequest le set lui-même.
      withJsonContentType: false,
    );

    final request = http.MultipartRequest('POST', uri)
      ..headers.addAll(headers)
      ..files.add(await http.MultipartFile.fromPath(
        'audio',
        path,
        filename: 'voice.m4a',
      ));

    final client = http.Client();
    _activeUploadClient = client;
    try {
      final streamedResponse = await client.send(request);
      final body = await streamedResponse.stream.bytesToString();
      if (streamedResponse.statusCode != 200) {
        throw VoiceTranscriberException(
          VoiceTranscriberError.networkFailure,
          'whisper backend status=${streamedResponse.statusCode} body=$body',
        );
      }
      final transcript = _extractTranscriptFromJson(body);
      if (transcript == null || transcript.trim().isEmpty) {
        throw const VoiceTranscriberException(
          VoiceTranscriberError.emptyTranscript,
          'whisper returned empty string',
        );
      }
      return transcript;
    } catch (e) {
      if (e is VoiceTranscriberException) rethrow;
      throw VoiceTranscriberException(
        VoiceTranscriberError.networkFailure,
        e.toString(),
      );
    } finally {
      client.close();
      _activeUploadClient = null;
      // Cleanup du fichier temporaire pour ne pas remplir le storage.
      _safeDeleteFile(path);
    }
  }

  @override
  Future<void> cancel() async {
    _amplitudeTimer?.cancel();
    _amplitudeTimer = null;

    // 1) Couper l'upload réseau s'il est en cours (cas où l'utilisateur
    //    annule pendant la transcription).
    final client = _activeUploadClient;
    if (client != null) {
      try {
        client.close();
      } catch (_) {}
      _activeUploadClient = null;
    }

    // 2) Stopper le recorder s'il est encore actif.
    if (await _recorder.isRecording()) {
      try {
        await _recorder.cancel();
      } catch (_) {}
    }

    // 3) Cleanup du fichier temp.
    final path = _currentRecordingPath;
    if (path != null) {
      _safeDeleteFile(path);
      _currentRecordingPath = null;
    }
  }

  @override
  Future<void> dispose() async {
    await cancel();
    await _recorder.dispose();
    await _soundLevelCtrl.close();
    _initialized = false;
  }

  /// Parse le body JSON `{"transcript": "..."}` retourné par le
  /// backend. Retourne null si le format est inattendu (sera converti
  /// en `emptyTranscript` côté caller).
  String? _extractTranscriptFromJson(String body) {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map<String, dynamic>) {
        final t = decoded['transcript'];
        if (t is String) return t;
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  void _safeDeleteFile(String path) {
    try {
      final f = File(path);
      if (f.existsSync()) f.deleteSync();
    } catch (_) {
      // Best-effort, le fichier sera nettoyé au prochain reboot
      // par l'OS dans /tmp.
    }
  }
}

/// Utilitaire partagé : vérifie/demande la permission micro de manière
/// **status-first**, ce qui évite un faux négatif sur iOS.
///
/// **Pourquoi `status` avant `request()` ?**
///
/// Sur iOS avec `permission_handler 11.x`, appeler directement
/// `Permission.microphone.request()` quand la permission est déjà
/// accordée (par ex. activée manuellement dans Réglages → Vancelian
/// → Micro) peut retourner un `PermissionStatus.denied` parasite parce
/// que `request()` ne déclenche pas la modale système (pas nécessaire,
/// déjà répondue) et ne va pas relire l'état système non plus dans
/// certains cas. C'est `status` qui reflète l'état courant
/// fiable.
///
/// **Logique :**
///   1. `status` dit `granted` / `limited` → on retourne `true` direct,
///      sans déclencher de modale.
///   2. `status` dit `permanentlyDenied` → on retourne `false` sans
///      `request()` (ce dernier serait no-op de toute façon).
///   3. Sinon (`denied` initial / `restricted` / non déterminé) →
///      on `request()` (modale système iOS si pas encore répondue)
///      et on évalue le retour.
///
/// `label` : juste pour le log debug (`native` vs `whisper`),
/// permet de pister quel moteur fait la demande.
Future<bool> _checkOrRequestMicrophonePermission({required String label}) async {
  var status = await Permission.microphone.status;
  if (kDebugMode) {
    debugPrint('[voice/$label] Permission.microphone initial status = $status');
  }
  if (status.isGranted || status.isLimited) {
    return true;
  }
  if (status.isPermanentlyDenied) {
    if (kDebugMode) {
      debugPrint(
        '[voice/$label] permission permanentlyDenied — UI doit guider vers Réglages',
      );
    }
    return false;
  }
  status = await Permission.microphone.request();
  if (kDebugMode) {
    debugPrint('[voice/$label] Permission.microphone after request() = $status');
  }
  return status.isGranted || status.isLimited;
}
