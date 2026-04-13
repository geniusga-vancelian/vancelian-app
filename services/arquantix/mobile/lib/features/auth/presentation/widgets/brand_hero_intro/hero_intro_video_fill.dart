import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

/// Vidéo plein écran type « cover » (même intention que [Image] `BoxFit.cover`).
class HeroIntroVideoFill extends StatelessWidget {
  const HeroIntroVideoFill({
    super.key,
    required this.controller,
  });

  final VideoPlayerController controller;

  @override
  Widget build(BuildContext context) {
    if (!controller.value.isInitialized) {
      return const SizedBox.expand();
    }
    final size = controller.value.size;
    if (size.width <= 0 || size.height <= 0) {
      return const SizedBox.expand();
    }
    return SizedBox.expand(
      child: FittedBox(
        fit: BoxFit.cover,
        child: SizedBox(
          width: size.width,
          height: size.height,
          child: VideoPlayer(controller),
        ),
      ),
    );
  }
}
