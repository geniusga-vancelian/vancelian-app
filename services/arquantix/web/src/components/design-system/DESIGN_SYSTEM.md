# Design System - Composants Extraits

## 🎨 Palette de Couleurs

```css
--primary: #6155F5
--on-primary: #FFFFFF
--surface: #FFFFFF
--on-surface: #000000
```

## 📦 Composants

### 1. Button (Bouton)

**Variantes:**
- `primary`: Fond violet (#6155F5), texte blanc
- `secondary`: Fond blanc, texte noir

**Spécifications:**
- Height: 48px
- Border Radius: 9999px (fully rounded)
- Padding horizontal: 40px
- Font: Inter Semi Bold
- Font Size: 16px
- Letter Spacing: -0.31px
- Line Height: 21px

**Props Flutter suggérées:**
```dart
enum ButtonVariant { primary, secondary }

class AppButton extends StatelessWidget {
  final ButtonVariant variant;
  final String text;
  final VoidCallback? onPressed;
  final bool fullWidth;

  // Styling constants
  static const double height = 48.0;
  static const double borderRadius = 9999.0;
  static const EdgeInsets padding = EdgeInsets.symmetric(horizontal: 40.0);
  static const double fontSize = 16.0;
  static const double letterSpacing = -0.31;
}
```

---

### 2. StatusBar (Barre de Statut iOS)

**Spécifications:**
- Height: 54px
- Couleur du texte: Blanc
- Font (Time): SF Pro Semibold, 17px
- Icônes: Batterie, WiFi, Signal cellulaire

**Composants:**
- Time (à gauche): "9:41"
- Levels (à droite): Batterie + WiFi + Signal

---

### 3. HomeIndicator (Indicateur Home iOS)

**Spécifications:**
- Container Height: 21px
- Indicator Width: 139px
- Indicator Height: 5px
- Border Radius: 100px
- Couleur: Blanc
- Position: Centré horizontalement, 8px du bas

---

### 4. Logo

**Spécifications:**
- Width: 251px
- Height: 29.61px
- Format: SVG
- Couleur: Blanc (fill)
- ViewBox: "0 0 250.999 29.6147"

---

### 5. VideoBackground (Fond Vidéo)

**Spécifications:**
- Object-fit: cover
- Autoplay: true
- Loop: true
- PlayInline: true
- Controls: hidden (nodownload)

---

## 📐 Layout

### Écran Login (375x812px - iPhone dimensions)

**Structure:**
1. **StatusBar** - Top (0px)
2. **Logo** - Position: left: 62px, top: 129px
3. **Buttons Container** - Position: left: 16px, top: 645px, width: 343px
   - Gap entre boutons: 8px
4. **HomeIndicator** - Bottom (0px)

**Spacing System:**
- Petit: 4px
- Moyen: 8px
- Large: 16px, 21px
- Extra Large: 40px

---

## 🎯 Tokens pour Flutter

```dart
class AppSpacing {
  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 16.0;
  static const double lg = 21.0;
  static const double xl = 40.0;
}

class AppColors {
  static const Color primary = Color(0xFF6155F5);
  static const Color onPrimary = Color(0xFFFFFFFF);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color onSurface = Color(0xFF000000);
}

class AppTypography {
  static const TextStyle buttonText = TextStyle(
    fontFamily: 'Inter',
    fontWeight: FontWeight.w600, // Semi Bold
    fontSize: 16.0,
    letterSpacing: -0.31,
    height: 21 / 16, // lineHeight / fontSize
  );

  static const TextStyle statusBarTime = TextStyle(
    fontFamily: 'SF Pro',
    fontWeight: FontWeight.w600,
    fontSize: 17.0,
    height: 22 / 17,
  );
}

class AppBorderRadius {
  static const double button = 9999.0; // Fully rounded
  static const double homeIndicator = 100.0;
}
```

---

## 📱 Usage Examples (React)

```tsx
import { Button } from './components/Button';
import { StatusBar } from './components/StatusBar';
import { HomeIndicator } from './components/HomeIndicator';
import { Logo } from './components/Logo';

// Bouton primaire
<Button variant="primary" fullWidth>
  Login
</Button>

// Bouton secondaire
<Button variant="secondary" fullWidth>
  S'inscrire
</Button>

// Barre de statut
<StatusBar />

// Indicateur home
<HomeIndicator />

// Logo
<Logo />
```
