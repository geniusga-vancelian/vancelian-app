import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    let ok = super.application(application, didFinishLaunchingWithOptions: launchOptions)
    // iOS n’affiche la ligne « Notifications » sous Réglages > [nom de l’app] qu’après
    // enregistrement auprès du centre de notifications / APNs. Le plugin permission_handler
    // n’appelle registerForRemoteNotifications() qu’en cas d’acceptation du dialogue —
    // pas si l’utilisateur refuse, ce qui peut laisser la section absente.
    // Appeler à chaque lancement est le pattern recommandé par Apple (TN2265).
    DispatchQueue.main.async {
      application.registerForRemoteNotifications()
    }
    return ok
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
  }
}
