#!/usr/bin/env python3
"""
Passe 3 — Audit éditorial.
Règles (mémoire Jean) :
  R1. Short answer doit être AUTONOME (pas de "see above/below/details/list")
  R2. Fiches produit/risque doivent privilégier la NARRATION (pas listes à puces)
  R3. Méthode éducative 6 étapes pour les pages à forte valeur explicative
"""
import re, yaml, json
from pathlib import Path
from collections import defaultdict

ROOT = Path("/sessions/trusting-festive-ride/mnt/Vancelian Support (Chat WIKI LLM)/wiki")

findings = []
def flag(page, sev, kind, detail, excerpt=""):
    findings.append({
        "page": page, "severity": sev, "kind": kind,
        "detail": detail, "excerpt": excerpt[:300]
    })

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

# Categories with product/risk character (need narrative, not bullets)
PRODUCT_RISK_CATEGORIES = {"exclusive-offers","savings","aktio","crypto"}

for p in ROOT.rglob("*.md"):
    if p.name in {"index.md","log.md"}: continue
    txt = p.read_text(encoding="utf-8", errors="replace")
    m = FM_RE.match(txt)
    if not m: continue
    try: fm = yaml.safe_load(m.group(1)) or {}
    except: continue
    body = m.group(2)
    rel = str(p.relative_to(ROOT))
    if not rel.startswith("faq/"): continue

    cat = fm.get("category")

    # Extract short answer section
    sa_match = re.search(r"## Short answer\s*\n(.+?)(?=\n##|\Z)", body, re.DOTALL)
    short_ans = sa_match.group(1).strip() if sa_match else ""

    # R1. Short answer autonomy checks
    if short_ans:
        # Check for external references
        bad_phrases = [
            (r"\bsee (above|below|details|the details|the list|the table)", "ref_to_external"),
            (r"\bas (mentioned|shown|explained) (above|below)", "ref_to_external"),
            (r"\b(refer|see) to (the|this) (section|page|list|table)", "ref_to_external"),
            (r"voir ci-(dessus|dessous)|voir le tableau|voir la liste", "ref_to_external"),
        ]
        for pat, k in bad_phrases:
            if re.search(pat, short_ans, re.I):
                m2 = re.search(r".{0,50}" + pat + r".{0,50}", short_ans, re.I)
                ex = m2.group(0) if m2 else ""
                flag(rel, "HIGH", "short_answer_not_autonomous",
                     f"Short answer référence du contenu externe à la section",
                     ex)

        # Short answer too short / too long
        words = len(short_ans.split())
        if words < 20:
            flag(rel, "LOW","short_answer_too_short",
                 f"{words} mots (cible 25-90, 2-4 phrases)")
        if words > 120:
            flag(rel, "LOW","short_answer_too_long",
                 f"{words} mots (cible 25-90, 2-4 phrases)")

    # R2. Product/risk pages — bullet dominance
    if cat in PRODUCT_RISK_CATEGORIES:
        lines = body.split("\n")
        bullet_lines = sum(1 for L in lines if re.match(r"^\s*[\-\*]\s", L))
        prose_lines = sum(1 for L in lines if L.strip() and not re.match(r"^#|^\s*[\-\*]\s|^\s*\||^>", L))
        total_content = bullet_lines + prose_lines
        if total_content > 20 and bullet_lines > 0:
            bullet_ratio = bullet_lines / total_content
            if bullet_ratio > 0.6:
                flag(rel, "MEDIUM", "bullet_heavy",
                     f"Ratio bullet {bullet_ratio:.0%} ({bullet_lines}/{total_content}) — fiche produit/risque devrait privilégier la narration")

    # Count H2/H3 sections to gauge structure
    h2_count = len(re.findall(r"^## ", body, re.M))

    # R3. Check section schema (CLAUDE.md expected: Short answer, Details, [Req], [Process], [Costs], [Caveats], Sources)
    expected = ["## Short answer","## Details","## Sources"]
    missing = [s for s in expected if s not in body]
    if missing:
        flag(rel, "MEDIUM", "missing_sections",
             f"Sections manquantes: {', '.join(missing)}")

# ───────── Summary ─────────
by_sev = defaultdict(int); by_kind = defaultdict(int)
for f in findings:
    by_sev[f["severity"]]+=1; by_kind[f["kind"]]+=1

print(f"Total findings Passe 3: {len(findings)}")
print("\n-- Sévérité --")
for k,v in sorted(by_sev.items()): print(f"  {k}: {v}")
print("\n-- Type --")
for k,v in sorted(by_kind.items(), key=lambda x:-x[1]): print(f"  {k}: {v}")

json.dump(findings, open('/sessions/trusting-festive-ride/audit_pass3_findings.json','w'),
          ensure_ascii=False, indent=2)
