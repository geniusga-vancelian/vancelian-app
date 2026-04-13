import 'package:flutter/cupertino.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

/// Route plein écran pour Login0 → téléphone (et flux auth similaires).
///
/// Sur **iOS**, [CupertinoPageRoute] aligne la transition sur le navigateur système
/// (slide + shader path souvent mieux amorti au premier push que [MaterialPageRoute]
/// + transitions Material 3).
///
/// Autres plateformes : [MaterialPageRoute] inchangé.
Route<T> authSlideRoute<T>(WidgetBuilder builder) {
  switch (defaultTargetPlatform) {
    case TargetPlatform.iOS:
      return CupertinoPageRoute<T>(builder: builder);
    default:
      return MaterialPageRoute<T>(builder: builder);
  }
}
