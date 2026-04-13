#!/usr/bin/env python3
"""
Script d'audit de complétude de la documentation canonique

Vérifie:
- Mots-clés incomplets: UNKNOWN, TODO, TBD, "needs confirmation"
- Titres vides (heading suivi de rien ou contenu minimal)
- Liens relatifs cassés vers docs canoniques

Génère: docs/canonical/AUDIT_DOC_COMPLETENESS_REPORT.md
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict
from datetime import datetime

# Configuration
BASE_DIR = Path(__file__).parent.parent
CANONICAL_DIR = BASE_DIR / "docs" / "canonical"
REPORT_FILE = CANONICAL_DIR / "AUDIT_DOC_COMPLETENESS_REPORT.md"

# Patterns à rechercher (insensible à la casse)
INCOMPLETE_PATTERNS = [
    r'\bUNKNOWN\b',
    r'\bTODO\b',
    r'\bTBD\b',
    r'needs confirmation',
    r'needs verification',
    r'non vérifié',
    r'non vérifiables',
]

# Extensions markdown
MD_EXTENSIONS = {'.md', '.markdown'}


class DocAuditor:
    def __init__(self, canonical_dir: Path):
        self.canonical_dir = canonical_dir
        self.issues: List[Dict] = []
        self.all_canonical_files: List[str] = []
        self.all_canonical_links: Dict[str, List[str]] = {}  # file -> list of referenced files
        
    def find_all_canonical_files(self) -> List[Path]:
        """Trouve tous les fichiers markdown dans docs/canonical"""
        files = []
        if not self.canonical_dir.exists():
            return files
        
        for file_path in self.canonical_dir.iterdir():
            if file_path.is_file() and file_path.suffix in MD_EXTENSIONS:
                if file_path.name != "AUDIT_DOC_COMPLETENESS_REPORT.md":  # Exclure le rapport lui-même
                    files.append(file_path)
                    self.all_canonical_files.append(file_path.name)
        
        return sorted(files)
    
    def extract_links_from_content(self, content: str) -> List[str]:
        """Extrait les liens relatifs markdown (format [text](file.md))"""
        link_pattern = r'\[([^\]]+)\]\(([^)]+\.md)\)'
        links = []
        for match in re.finditer(link_pattern, content):
            link_target = match.group(2)
            # Normaliser le chemin (enlever ./ ou ../)
            if link_target.startswith('./'):
                link_target = link_target[2:]
            elif link_target.startswith('../'):
                link_target = link_target[3:]
            links.append(link_target)
        return links
    
    def check_incomplete_keywords(self, file_path: Path, content: str):
        """Vérifie les mots-clés incomplets (UNKNOWN, TODO, etc.)"""
        lines = content.split('\n')
        for line_num, line in enumerate(lines, start=1):
            for pattern in INCOMPLETE_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    match = re.search(pattern, line, re.IGNORECASE)
                    keyword = match.group(0)
                    self.issues.append({
                        'type': 'incomplete_keyword',
                        'file': file_path.name,
                        'line': line_num,
                        'keyword': keyword,
                        'context': line.strip()[:100],  # Premiers 100 caractères
                    })
    
    def check_empty_headings(self, file_path: Path, content: str):
        """Vérifie les titres vides (heading suivi de rien ou contenu minimal)"""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            # Détecter un heading (## ou ###)
            heading_match = re.match(r'^(#{2,})\s+(.+)$', line)
            if heading_match:
                heading_level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()
                
                # Chercher le contenu suivant (jusqu'au prochain heading de même niveau ou supérieur)
                next_line_idx = i + 1
                content_found = False
                content_length = 0
                
                while next_line_idx < len(lines):
                    next_line = lines[next_line_idx].strip()
                    
                    # Si on trouve un heading de même niveau ou supérieur, on s'arrête
                    next_heading_match = re.match(r'^(#{2,})\s+', next_line)
                    if next_heading_match:
                        next_heading_level = len(next_heading_match.group(1))
                        if next_heading_level <= heading_level:
                            break
                    
                    # Ignorer les lignes vides et les séparateurs
                    if next_line and not next_line.startswith('---'):
                        content_found = True
                        content_length += len(next_line)
                        # Si on a trouvé du contenu significatif (plus de 50 caractères), c'est OK
                        if content_length > 50:
                            break
                    
                    next_line_idx += 1
                
                # Si pas de contenu ou contenu très court (< 50 caractères), c'est suspect
                if not content_found or content_length < 50:
                    self.issues.append({
                        'type': 'empty_heading',
                        'file': file_path.name,
                        'line': i + 1,
                        'heading': heading_text,
                        'level': heading_level,
                        'content_length': content_length,
                    })
    
    def check_broken_links(self, file_path: Path, content: str):
        """Vérifie les liens relatifs cassés vers docs canoniques"""
        links = self.extract_links_from_content(content)
        file_links = []
        lines = content.split('\n')
        
        for link in links:
            file_links.append(link)
            
            # Trouver la ligne du lien (approximatif)
            link_line = 0
            for line_num, line in enumerate(lines, start=1):
                if link in line:
                    link_line = line_num
                    break
            
            # Vérifier si le fichier cible existe
            if '/' in link:
                # Lien avec chemin relatif, vérifier depuis canonical_dir
                target_path = self.canonical_dir.parent / link
            else:
                # Lien simple (même répertoire)
                target_path = self.canonical_dir / link
            
            # Vérifier si le fichier existe
            if not target_path.exists():
                # Mais seulement si c'est un fichier canonique (dans notre liste)
                if link.endswith('.md') and any(cf.endswith(link) or link.endswith(cf) for cf in self.all_canonical_files):
                    self.issues.append({
                        'type': 'broken_link',
                        'file': file_path.name,
                        'line': link_line,
                        'link': link,
                        'target': str(target_path.relative_to(BASE_DIR)),
                    })
        
        self.all_canonical_links[file_path.name] = file_links
    
    def audit_file(self, file_path: Path):
        """Audite un fichier markdown"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.issues.append({
                'type': 'read_error',
                'file': file_path.name,
                'line': 0,
                'error': str(e),
            })
            return
        
        # Vérifier les mots-clés incomplets
        self.check_incomplete_keywords(file_path, content)
        
        # Vérifier les titres vides
        self.check_empty_headings(file_path, content)
        
        # Vérifier les liens cassés
        self.check_broken_links(file_path, content)
    
    def audit_all(self):
        """Audite tous les fichiers canoniques"""
        files = self.find_all_canonical_files()
        
        if not files:
            print(f"⚠️  Aucun fichier markdown trouvé dans {self.canonical_dir}")
            return
        
        print(f"📚 Audit de {len(files)} fichiers dans {self.canonical_dir}")
        
        for file_path in files:
            print(f"   ✓ {file_path.name}")
            self.audit_file(file_path)
    
    def generate_report(self) -> str:
        """Génère le rapport d'audit"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""# Audit de Complétude Documentation Canonique

**Date**: {now}  
**Répertoire**: `docs/canonical/`

---

## Résumé

- **Fichiers audités**: {len(self.all_canonical_files)}
- **Issues trouvées**: {len(self.issues)}
- **Mots-clés incomplets**: {len([i for i in self.issues if i['type'] == 'incomplete_keyword'])}
- **Titres vides**: {len([i for i in self.issues if i['type'] == 'empty_heading'])}
- **Liens cassés**: {len([i for i in self.issues if i['type'] == 'broken_link'])}

---

## Issues par Type

"""
        
        # Issues par type
        issues_by_type = {}
        for issue in self.issues:
            issue_type = issue['type']
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = []
            issues_by_type[issue_type].append(issue)
        
        # Détails par type
        for issue_type in ['incomplete_keyword', 'empty_heading', 'broken_link']:
            if issue_type not in issues_by_type:
                continue
            
            type_label = {
                'incomplete_keyword': 'Mots-clés Incomplets (UNKNOWN, TODO, TBD, etc.)',
                'empty_heading': 'Titres Vides',
                'broken_link': 'Liens Relatifs Cassés',
            }[issue_type]
            
            report += f"\n### {type_label}\n\n"
            
            if issue_type == 'incomplete_keyword':
                for issue in issues_by_type[issue_type]:
                    report += f"- **{issue['file']}:{issue['line']}** - Mot-clé: `{issue['keyword']}`\n"
                    report += f"  ```\n  {issue['context']}\n  ```\n\n"
            
            elif issue_type == 'empty_heading':
                for issue in issues_by_type[issue_type]:
                    heading_prefix = '#' * issue['level']
                    report += f"- **{issue['file']}:{issue['line']}** - {heading_prefix} {issue['heading']}\n"
                    report += f"  Contenu: {issue['content_length']} caractères\n\n"
            
            elif issue_type == 'broken_link':
                for issue in issues_by_type[issue_type]:
                    report += f"- **{issue['file']}** - Lien: `{issue['link']}`\n"
                    report += f"  Cible: `{issue['target']}` (n'existe pas)\n\n"
        
        # Checklist de remediation
        report += "\n---\n\n## Checklist de Remediation\n\n"
        
        for issue_type in ['incomplete_keyword', 'empty_heading', 'broken_link']:
            if issue_type not in issues_by_type:
                continue
            
            count = len(issues_by_type[issue_type])
            type_action = {
                'incomplete_keyword': 'Remplacer les mots-clés incomplets par du contenu réel',
                'empty_heading': 'Ajouter du contenu sous les titres vides',
                'broken_link': 'Corriger les liens relatifs cassés',
            }[issue_type]
            
            report += f"- [ ] **{count} issues** - {type_action}\n"
        
        report += "\n---\n\n"
        report += f"*Généré par: `tools/audit_doc_completeness.py`*\n"
        
        return report
    
    def write_report(self):
        """Écrit le rapport dans le fichier"""
        report = self.generate_report()
        
        try:
            with open(REPORT_FILE, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n✅ Rapport généré: {REPORT_FILE}")
            return True
        except Exception as e:
            print(f"\n❌ Erreur lors de l'écriture du rapport: {e}")
            return False
    
    def print_summary(self):
        """Affiche un résumé dans la console"""
        print(f"\n{'='*60}")
        print(f"RÉSUMÉ DE L'AUDIT")
        print(f"{'='*60}\n")
        
        print(f"Fichiers audités: {len(self.all_canonical_files)}")
        print(f"Total issues: {len(self.issues)}\n")
        
        if not self.issues:
            print("✅ Aucune issue trouvée! Documentation complète.")
            return
        
        issues_by_type = {}
        for issue in self.issues:
            issue_type = issue['type']
            issues_by_type[issue_type] = issues_by_type.get(issue_type, 0) + 1
        
        for issue_type, count in sorted(issues_by_type.items()):
            type_label = {
                'incomplete_keyword': 'Mots-clés incomplets',
                'empty_heading': 'Titres vides',
                'broken_link': 'Liens cassés',
            }.get(issue_type, issue_type)
            print(f"  - {type_label}: {count}")
        
        print(f"\n📄 Voir le rapport détaillé: {REPORT_FILE}")


def main():
    """Point d'entrée principal"""
    auditor = DocAuditor(CANONICAL_DIR)
    
    # Auditer tous les fichiers
    auditor.audit_all()
    
    # Générer et écrire le rapport
    success = auditor.write_report()
    
    # Afficher le résumé
    auditor.print_summary()
    
    # Exit code: 0 si pas d'issues, 1 sinon
    if auditor.issues:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

