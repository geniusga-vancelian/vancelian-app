#!/usr/bin/env python3
"""
Passe 1 — Audit structurel automatique du Wiki Vancelian.
Détecte : frontmatter invalide, questions: insuffisantes, orphelins, liens
cassés, sources raw inexistantes, pages stale.
"""
import os, re, yaml, json, unicodedata
from pathlib import Path
from datetime import date, datetime

def nfc(s): return unicodedata.normalize("NFC", str(s))

ROOT = Path("/sessions/trusting-festive-ride/mnt/Vancelian Support (Chat WIKI LLM)")
WIKI = ROOT / "wiki"
RAW  = ROOT / "raw"
TODAY = date(2026, 4, 18)
STALE_DAYS = 180

REQUIRED_FAQ_FIELDS = [
    "title","slug","category","audience","status",
    "last_reviewed","sources","questions"
]
VALID_CATEGORIES = {
    "savings","exclusive-offers","crypto","aktio","memberships","account",
    "transfers-cards","legal-compliance","company","business",
    "affiliate-partner","b2b-agent","other"
}
VALID_STATUS = {"draft","verified","stale"}

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

def parse_fm(text):
    m = FM_RE.match(text)
    if not m:
        return None, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        return {"__yaml_error__": str(e)}, m.group(2)
    return fm, m.group(2)

def list_pages(root):
    out = []
    for p in root.rglob("*.md"):
        rel = p.relative_to(WIKI)
        if rel.name in {"index.md","log.md"}: continue
        out.append(p)
    return sorted(out)

def load_pages():
    pages = {}
    for p in list_pages(WIKI):
        txt = p.read_text(encoding="utf-8", errors="replace")
        fm, body = parse_fm(txt)
        pages[str(p.relative_to(WIKI))] = {"fm": fm, "body": body, "path": p}
    return pages

def load_raw_files():
    return {nfc(str(p.relative_to(ROOT))) for p in RAW.rglob("*") if p.is_file()}

def load_index_entries():
    idx = (WIKI / "index.md").read_text(encoding="utf-8", errors="replace")
    # Find all links to wiki/ pages
    links = re.findall(r"\]\(([^)]+\.md)\)", idx)
    # Normalize
    norm = set()
    for l in links:
        l = l.strip()
        if l.startswith("wiki/"):
            l = l[len("wiki/"):]
        if l.startswith("./"):
            l = l[2:]
        norm.add(l)
    # Also plain "category/slug.md" mentions
    plain = re.findall(r"(?<![\w\-/])(faq/[a-z0-9\-]+/[a-z0-9\-]+\.md)", idx)
    for l in plain: norm.add(l)
    return norm, idx

def analyze():
    pages = load_pages()
    raw_files = load_raw_files()
    idx_entries, idx_text = load_index_entries()

    issues = []

    page_rels = set(pages.keys())

    # Build slug index & related check
    slug_map = {}
    for rel, info in pages.items():
        fm = info["fm"] or {}
        if isinstance(fm, dict) and fm.get("slug"):
            slug_map.setdefault(fm["slug"], []).append(rel)

    def add(rel, severity, kind, detail):
        issues.append({"page": rel, "severity": severity, "kind": kind, "detail": detail})

    for rel, info in pages.items():
        fm = info["fm"]
        body = info["body"] or ""

        # 1. Frontmatter present & valid
        if fm is None:
            add(rel, "HIGH", "no_frontmatter", "Pas de bloc YAML frontmatter")
            continue
        if "__yaml_error__" in fm:
            add(rel, "HIGH", "frontmatter_yaml_error", fm["__yaml_error__"])
            continue

        is_faq = rel.startswith("faq/")

        # 2. Required fields (FAQ only strict)
        if is_faq:
            for field in REQUIRED_FAQ_FIELDS:
                if field not in fm or fm.get(field) in (None,"",[]):
                    add(rel, "HIGH", "missing_field", f"Champ manquant: {field}")

            # category valid
            cat = fm.get("category")
            if cat and cat not in VALID_CATEGORIES:
                add(rel, "MEDIUM", "invalid_category", f"Catégorie inconnue: {cat}")

            # category matches folder
            if cat:
                folder_cat = rel.split("/")[1] if rel.startswith("faq/") and "/" in rel[4:] else None
                if folder_cat and cat != folder_cat:
                    add(rel, "HIGH", "category_mismatch",
                        f"Fiche dans faq/{folder_cat}/ mais category={cat}")

            # status valid
            st = fm.get("status")
            if st and st not in VALID_STATUS:
                add(rel, "LOW", "invalid_status", f"status inconnu: {st}")

            # questions: coverage
            q = fm.get("questions") or []
            if not isinstance(q, list):
                add(rel, "HIGH", "questions_not_list", type(q).__name__)
            else:
                if len(q) < 5:
                    add(rel, "HIGH", "questions_too_few",
                        f"{len(q)} variantes (minimum 5, cible 5-8)")
                if len(q) > 10:
                    add(rel, "LOW", "questions_too_many",
                        f"{len(q)} variantes (cible 5-8)")
                # deduplicate / spot French leak
                lower = [str(x).lower() for x in q]
                if len(set(lower)) != len(lower):
                    add(rel, "MEDIUM","questions_duplicates",
                        "Variantes dupliquées dans questions:")

        # 3. last_reviewed staleness
        lr = fm.get("last_reviewed")
        if lr:
            try:
                if isinstance(lr, str):
                    lr_d = datetime.strptime(lr, "%Y-%m-%d").date()
                elif isinstance(lr, date):
                    lr_d = lr
                else:
                    lr_d = None
                if lr_d:
                    age = (TODAY - lr_d).days
                    if age > STALE_DAYS:
                        add(rel, "MEDIUM", "stale",
                            f"last_reviewed={lr_d}, {age} jours")
            except Exception as e:
                add(rel, "LOW","last_reviewed_format", str(e))

        # 4. sources field — check raw/ references exist
        srcs = fm.get("sources") or []
        if isinstance(srcs, list):
            for s in srcs:
                s_raw = str(s).strip()
                s = nfc(s_raw)
                # Acceptable: "raw/..." path
                if s.startswith("raw/"):
                    if s not in raw_files:
                        # Try matching basename
                        base = os.path.basename(s)
                        candidates = [r for r in raw_files if r.endswith("/"+base) or r.endswith(base)]
                        if not candidates:
                            add(rel, "HIGH","broken_source",
                                f"raw introuvable: {s_raw}")

        # 5. related: links — resolve relative to current page's folder
        rels = fm.get("related") or []
        if isinstance(rels, list):
            from pathlib import PurePosixPath
            cur_dir = PurePosixPath(rel).parent
            for r in rels:
                r_raw = str(r).strip()
                rr = r_raw
                if rr.startswith("wiki/"):
                    rr = rr[len("wiki/"):]
                if not rr.endswith(".md"):
                    add(rel, "LOW","related_not_md", f"related non-.md: {r_raw}")
                    continue
                # Resolve: if starts with './' or '../', resolve relative to cur_dir
                if rr.startswith("./") or rr.startswith("../"):
                    resolved = str((cur_dir / rr).as_posix())
                    # Normalize (remove ../)
                    parts = []
                    for seg in resolved.split("/"):
                        if seg == "..":
                            if parts: parts.pop()
                        elif seg not in (".",""):
                            parts.append(seg)
                    resolved = "/".join(parts)
                elif "/" not in rr:
                    # Bare filename → same folder
                    resolved = str((cur_dir / rr).as_posix())
                else:
                    resolved = rr
                if resolved not in page_rels:
                    add(rel, "MEDIUM","broken_related",
                        f"related introuvable: {r_raw} (résolu: {resolved})")

        # 6. short answer presence (FAQ)
        if is_faq:
            if "## Short answer" not in body and "## Short answer" not in body.replace("##  ","## "):
                add(rel, "MEDIUM","no_short_answer",
                    "Section '## Short answer' manquante")

    # 7. Orphans: pages not in index.md
    for rel in page_rels:
        if rel not in idx_entries and not any(rel in l for l in idx_entries):
            # Look for plain occurrence of the filename in index text
            if rel not in idx_text:
                add(rel, "MEDIUM","orphan_index",
                    "Page non référencée dans index.md")

    # 8. Duplicate slugs
    for slug, rels in slug_map.items():
        if len(rels) > 1:
            for r in rels:
                add(r, "HIGH","duplicate_slug",
                    f"slug={slug} partagé avec: {', '.join(x for x in rels if x!=r)}")

    return issues, pages, raw_files

if __name__ == "__main__":
    issues, pages, raw_files = analyze()
    print(f"Total pages analysées : {len(pages)}")
    print(f"Total fichiers raw/ dispo : {len(raw_files)}")
    print(f"Total anomalies trouvées : {len(issues)}")
    # Breakdown
    by_sev = {}
    by_kind = {}
    for i in issues:
        by_sev[i["severity"]] = by_sev.get(i["severity"],0)+1
        by_kind[i["kind"]] = by_kind.get(i["kind"],0)+1
    print("\n-- Par sévérité --")
    for k,v in sorted(by_sev.items()): print(f"  {k}: {v}")
    print("\n-- Par type --")
    for k,v in sorted(by_kind.items(), key=lambda x:-x[1]):
        print(f"  {k}: {v}")

    # Save json
    out = Path("/sessions/trusting-festive-ride/audit_pass1_issues.json")
    out.write_text(json.dumps(issues, ensure_ascii=False, indent=2, default=str))
    print(f"\nDump: {out}")
