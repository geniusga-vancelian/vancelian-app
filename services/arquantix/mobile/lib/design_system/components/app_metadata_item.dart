import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../atoms/app_colors.dart';

/// Petit élément de métadonnée avec icône et texte.
///
/// Figma spec:
/// - Icon size: 12px, couleur accent (#6155F5)
/// - Text: Inter Regular 13px, line-height 18, tracking -0.08, couleur #8E8E93
/// - Gap: 4px entre icône et texte
///
/// Utilisé pour afficher date, heure, catégorie, etc. dans les articles.
class AppMetadataItem extends StatelessWidget {
  const AppMetadataItem({
    super.key,
    required this.icon,
    required this.text,
    this.iconColor = const Color(0xFF6155F5),
  });

  final IconData icon;
  final String text;
  final Color iconColor;

  static const _textStyle = TextStyle(
    fontSize: 13,
    fontWeight: FontWeight.w400,
    height: 18 / 13,
    letterSpacing: -0.08,
  );

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 12, color: iconColor),
        const SizedBox(width: 4),
        Flexible(
          child: Text(
            text,
            style: GoogleFonts.inter(textStyle: _textStyle)
                .copyWith(color: AppColors.textMuted),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}
