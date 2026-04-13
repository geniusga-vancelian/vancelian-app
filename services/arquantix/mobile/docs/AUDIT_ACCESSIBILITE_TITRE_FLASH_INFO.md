# Audit : accessibilité du titre « Flash info » (module sous My account)

## Contexte

Le titre du module « Flash info », affiché juste sous le module « Mes comptes » (My account), n’est pas facilement accessible. Cet audit analyse la chaîne de layout, le hit-test et l’accessibilité pour identifier les causes et les corrections.

---

## 1. Structure des couches (Home)

- **Stack** (body du Scaffold) :
  1. **Header** (Positioned) : hauteur ≈ 60 % écran, fond hero.
  2. **Scroll** (CustomScrollView) : spacer header + sheet (WalletsModule) + content (Padding > Column > BlogNews).
  3. **headerInteractionOverlay** (Positioned) : même taille que le header, pour avatar / période / boutons.

- **Overlay** : base en `IgnorePointer(child: SizedBox.expand())`, donc les taps en dehors des zones cliquables (avatar, période, boutons) **passent au scroll**. L’overlay ne bloque pas le titre Flash info.

---

## 2. Ordre des slivers (scroll)

1. `SliverToBoxAdapter(SizedBox(headerHeight))` — réserve la place du header.
2. `SliverToBoxAdapter(sheet)` — carte My account, sous le header (sans chevauchement).
3. `SliverToBoxAdapter(content)` — contenu (padding + Column avec BlogNews), avec `Transform.translate(0, -overlap)`.
4. `SliverToBoxAdapter(SizedBox(reserved))` — marge bas.

- **Hit-test** : les enfants du scroll sont testés dans l’ordre inverse (du bas vers le haut). Le **content** est donc testé avant le **sheet** pour un point dans la zone du content. Le titre Flash info, qui est dans le content, peut recevoir le tap dès que le doigt est dans les bounds du content.

---

## 3. Problèmes identifiés

### 3.1 Zone de tap trop faible (cause principale)

- Le titre « Flash info » est dans un `InkWell` avec `Padding(vertical: 8)` et un `Row(mainAxisSize: MainAxisSize.min)`.
- La hauteur réelle de la ligne ≈ hauteur du texte (~20–22 px) + 16 px de padding ≈ **36–38 px**.
- Les recommandations d’accessibilité (Apple HIG, Material) demandent une **zone de touch d’au moins 44 pt**.
- Conséquence : la cible est petite, surtout en bord de zone ou après un scroll, ce qui donne l’impression que le titre n’est « pas facilement accessible ».

### 3.2 Sémantique accessibilité

- Pas de `Semantics(button: true, hint: …)` sur la ligne titre.
- Les lecteurs d’écran n’ont pas d’indication claire de « bouton » ni de hint du type « ouvrir la section blog ».

### 3.3 Largeur de la zone de tap

- `SizedBox(width: double.infinity)` est bien présent : la ligne occupe toute la largeur disponible (moins les marges horizontales du module). Pas de problème de largeur identifié.

---

## 4. Corrections appliquées

1. **Hauteur minimale de la ligne titre**  
   Contrainte **minHeight: 44** sur la zone cliquable du titre (Material/InkWell) pour respecter la cible de touch minimale.

2. **Sémantique**  
   - `Semantics(button: true, label: titre, hint: 'Ouvrir la section Flash info')` sur la zone titre pour que les technologies d’assistance annoncent un bouton et son action.

3. **Comportement de hit-test**  
   - Conservation de `Material` + `InkWell` sur toute la largeur avec `SizedBox(width: double.infinity)` pour que toute la ligne reste cliquable et que le ripple couvre bien la zone.

---

## 5. Fichiers modifiés

- `lib/design_system/components/blog_news.dart` : zone titre avec `ConstraintBox(minHeight: 44)`, `Semantics`, et structure inchangée pour le reste du module.

---

## 6. Vérifications recommandées

- Sur device/simulateur : taper sur le titre « Flash info » (centre, bords, après un peu de scroll) et vérifier que la navigation vers le blog se fait à chaque fois.
- Avec VoiceOver / TalkBack : vérifier que le titre est annoncé comme bouton avec un hint du type « Ouvrir la section Flash info ».
