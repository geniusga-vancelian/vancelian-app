# Launch Screen Assets

- **LaunchLogo.pdf** : export vectoriel depuis `mobile/assets/logo.svg` (même viewBox 658×78 que Flutter `SplashBrandLogo`).  
  Préserve le ratio exact sous `scaleAspectFit`, contrairement aux PNG rasterisés (hauteur arrondie → letterboxing).

Régénérer si le logo change :

```bash
cd "$(git rev-parse --show-toplevel)/services/arquantix/mobile"
rsvg-convert -f pdf assets/logo.svg -o ios/Runner/Assets.xcassets/LaunchImage.imageset/LaunchLogo.pdf
```

**Storyboard** (`LaunchScreen.storyboard`) : contraintes inchangées — largeur **50 %** de l’écran, hauteur = largeur × (78/658), centré (équivalent `HeroIntroMotion` + `SplashBrandLogo`).
