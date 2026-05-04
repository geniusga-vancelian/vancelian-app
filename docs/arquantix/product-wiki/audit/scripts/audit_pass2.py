#!/usr/bin/env python3
"""
Passe 2 — Audit factuel des zones à risque.
Zones couvertes :
  Z1. Marques obsolètes (Automata, Akt.io, RAYN, Automata Pay)
  Z2. Attribution d'entité (Vancelian LTD vs Automata Group UK vs ADGM)
  Z3. AKTIO transférabilité (EEA vs non-EEA)
  Z4. Cloud Mining JV structure + art. 4.3 CGUPM
  Z5. Distinction type d'offre (mining vs lending vs refinancement BTC)
  Z6. Mécanique BTC lending "générique" (ne doit pas être dupliquée par offre)
  Z7. Dubai Villa Al Barari (quartier) vs Solaria (emprunteur)
"""
import os, re, yaml, json, unicodedata
from pathlib import Path
from collections import defaultdict

def nfc(s): return unicodedata.normalize("NFC", str(s))

ROOT = Path("/sessions/trusting-festive-ride/mnt/Vancelian Support (Chat WIKI LLM)")
WIKI = ROOT / "wiki"

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

def parse(p):
    txt = p.read_text(encoding="utf-8", errors="replace")
    m = FM_RE.match(txt)
    if m:
        try: fm = yaml.safe_load(m.group(1)) or {}
        except: fm = {}
        return fm, m.group(2)
    return {}, txt

def pages():
    for p in WIKI.rglob("*.md"):
        if p.name in {"index.md","log.md"}: continue
        fm, body = parse(p)
        yield str(p.relative_to(WIKI)), fm, body

findings = []
def flag(zone, page, sev, kind, detail, excerpt=""):
    findings.append({
        "zone": zone, "page": page, "severity": sev,
        "kind": kind, "detail": detail, "excerpt": excerpt[:300]
    })

# Collect all pages once
all_pages = list(pages())

# ───────────────────────────────────────────────────────────
# Z1. Marques obsolètes
# ───────────────────────────────────────────────────────────
# Mentions OK dans contexte historique, entities/, ICO legacy.
# PROBLEMATIC: brand "Akt.io" or "RAYN" as current company name
# in client-facing FAQ content body.
HIST_OK_PAGES = {
    "entities/automata-group.md",
    "entities/automata-ico-ltd.md",
    "faq/aktio/aktio-issuer-automata-ico.md",
    "faq/aktio/aktio-ico-sale-rounds.md",
    "faq/company/vancelian-brand-history.md",  # if exists
    "concepts/regulatory-roadmap.md",
    "concepts/vancelian-glossary.md",
    "faq/aktio/what-is-aktio.md",  # may reference historic ICO
}
old_brands = [
    ("Akt.io", "Akt\\.io"),
    ("RAYN", r"\bRAYN\b"),
    ("Automata Pay", r"\bAutomata Pay\b"),
]
# Automata is only OK when referring to "Automata Group" (UK holding) or
# "Automata ICO Ltd" as historical entities
for rel, fm, body in all_pages:
    if rel in HIST_OK_PAGES: continue
    if not rel.startswith("faq/"): continue
    for label, pat in old_brands:
        if re.search(pat, body):
            # Extract excerpt
            m = re.search(r".{0,80}" + pat + r".{0,80}", body)
            ex = m.group(0) if m else ""
            flag("Z1_brand", rel, "MEDIUM", "obsolete_brand",
                 f"Mention de '{label}' hors contexte historique", ex)
    # Automata standalone (not Automata Group, Automata ICO, Automata France)
    for m in re.finditer(r"\bAutomata\b(?! Group| ICO| Pay| France)", body):
        # Look at surrounding context
        start = max(0, m.start()-60)
        end = min(len(body), m.end()+60)
        ex = body[start:end]
        flag("Z1_brand", rel, "LOW", "automata_standalone",
             "Mention 'Automata' sans qualificatif (Group/ICO/France)", ex)

# ───────────────────────────────────────────────────────────
# Z2. Attribution d'entité — pour Cloud Mining en particulier
# ───────────────────────────────────────────────────────────
# Cloud Mining = Vancelian LTD (JV: Automata Group UK + Hearst Solution FZCO)
CM_ENTITY_TERMS = ["Vancelian LTD","Automata Group","Hearst Solution FZCO",
                   "JV","joint venture","Joint Venture","co-entreprise"]
cm_pages = [(rel,fm,body) for rel,fm,body in all_pages
            if "cloud-mining" in rel or "cloud_mining" in rel
            or re.search(r"Cloud Mining", body) and rel.startswith("faq/exclusive-offers")]

for rel, fm, body in cm_pages:
    has_vancelian_ltd = bool(re.search(r"Vancelian\s*LTD", body, re.I))
    has_hearst = bool(re.search(r"Hearst", body, re.I))
    has_automata_group = bool(re.search(r"Automata\s+Group", body))
    mentions_cm = bool(re.search(r"Cloud\s+Mining", body, re.I))

    if mentions_cm and not has_hearst:
        # Cloud mining page that doesn't mention Hearst = suspicious
        if "cloud-mining" in rel or "mining" in rel:
            flag("Z2_entity", rel, "MEDIUM", "cm_no_hearst",
                 "Page Cloud Mining sans mention de Hearst Solution (partenaire JV)")

# ───────────────────────────────────────────────────────────
# Z3. AKTIO transférabilité (EEA vs non-EEA)
# ───────────────────────────────────────────────────────────
aktio_transfer_pages = []
for rel, fm, body in all_pages:
    if not re.search(r"AKTIO", body): continue
    if re.search(r"transfer|withdraw|retrait|BitMart|bit ?mart", body, re.I):
        aktio_transfer_pages.append((rel, fm, body))

for rel, fm, body in aktio_transfer_pages:
    mentions_eea = bool(re.search(r"\bEEA\b|European Economic Area|Espace \u00e9conomique", body))
    mentions_ico_investor = bool(re.search(r"ICO (investor|buyer|participant)|ICO participant", body, re.I))
    mentions_not_transfer = bool(re.search(r"not (transferable|transferrable)|non[- ]?transferable|cannot (be )?transferred|impossible (de )?transf\u00e9rer", body, re.I))
    mentions_transfer_ok = bool(re.search(r"(you )?can (transfer|withdraw) AKTIO|transfer AKTIO to BitMart", body, re.I))

    if mentions_transfer_ok and not mentions_eea and not mentions_ico_investor:
        flag("Z3_aktio", rel, "HIGH", "aktio_transfer_no_restriction",
             "Page évoquant transfert AKTIO sans mentionner restriction EEA ou condition ICO investor",
             "")
    if mentions_not_transfer and mentions_transfer_ok:
        # Both statements in same page — check if disambiguation is clear
        flag("Z3_aktio", rel, "MEDIUM", "aktio_transfer_mixed",
             "Page mentionne à la fois 'transférable' et 'non transférable' — vérifier disambiguation EEA/non-EEA")

# ───────────────────────────────────────────────────────────
# Z4. Cloud Mining + art. 4.3 CGUPM
# ───────────────────────────────────────────────────────────
art43_pages = []
for rel, fm, body in all_pages:
    if re.search(r"4\.3|Art(icle)? 4", body) and re.search(r"CGUPM|Conditions g\u00e9n\u00e9rales|General (Conditions|Terms)", body, re.I):
        art43_pages.append((rel, fm, body))
    if re.search(r"mining", body, re.I) and re.search(r"capital|reimburs|remboursement", body, re.I) and "exclusive-offers" in rel:
        art43_pages.append((rel, fm, body))

# Deduplicate
seen = set()
dedup = []
for rel, fm, body in art43_pages:
    if rel in seen: continue
    seen.add(rel); dedup.append((rel, fm, body))
art43_pages = dedup

for rel, fm, body in art43_pages:
    # Look for phrases that contradict JV solvency bound
    if re.search(r"guaranteed capital|capital garanti|fully reimbursed|100% reimburs", body, re.I):
        # Cloud Mining capital is NOT guaranteed — it's contractually committed but bounded by solvency
        flag("Z4_art43", rel, "HIGH", "capital_guarantee_overclaim",
             "Page Cloud Mining affirme un 'guaranteed capital' ou équivalent — contradit la mémoire (bounded by JV solvency)")

# ───────────────────────────────────────────────────────────
# Z5. Distinction type d'offre (mining vs lending vs refinancing)
# ───────────────────────────────────────────────────────────
# Real estate = lending/refinancing (BTC loan refinanced via rental yield)
# Cloud Mining = computing mining (hashrate leasing)
# Watch for pages that confuse the two mechanics
real_estate_pages = [(rel,fm,body) for rel,fm,body in all_pages
                     if any(k in rel for k in ["bali","dubai","niseko","villa","chalet"])]

for rel, fm, body in real_estate_pages:
    if re.search(r"\bmining\b|\bhashrate\b|\bhash rate\b", body, re.I):
        # Real estate page mentioning "mining" — suspicious
        m = re.search(r".{0,100}mining.{0,100}", body, re.I)
        ex = m.group(0) if m else ""
        flag("Z5_offer_type", rel, "HIGH", "realestate_mentions_mining",
             "Page immobilière qui mentionne 'mining' ou 'hashrate' — confusion de type d'offre ?", ex)

# Reverse: Cloud Mining pages that claim "real estate" or "rental yield"
for rel, fm, body in cm_pages:
    if re.search(r"rental (yield|income)|loyer|real estate|immobilier", body, re.I):
        m = re.search(r".{0,100}(rental|loyer|real estate|immobilier).{0,100}", body, re.I)
        ex = m.group(0) if m else ""
        flag("Z5_offer_type", rel, "HIGH", "cm_mentions_realestate",
             "Page Cloud Mining évoque 'rental yield' ou 'immobilier' — confusion", ex)

# ───────────────────────────────────────────────────────────
# Z6. Mécanique BTC lending/refinancement — générique ou dupliquée ?
# ───────────────────────────────────────────────────────────
# Chercher les pages immobilières qui décrivent EN DÉTAIL la mécanique BTC
# loan, alors que ça devrait être factorisé dans une page générique.
generic_page_candidates = [rel for rel,_,_ in all_pages
                           if "btc-lending" in rel or "exclusive-offer-mechanic" in rel
                           or "how-exclusive-offer" in rel]

BTC_MECHANICS_SIGNATURE = [
    r"BTC.*(collateral|garantie|g\u00e9l\u00e9)",
    r"(refinanc|collateralized|prêt (adoss|adossé))",
    r"rental (yield|income).*(refinance|rembours|BTC)",
]

for rel, fm, body in real_estate_pages:
    if rel in generic_page_candidates: continue
    matches = sum(bool(re.search(p, body, re.I)) for p in BTC_MECHANICS_SIGNATURE)
    # Count length of BTC mechanics explanation
    btc_desc_len = 0
    for m in re.finditer(r"(BTC|bitcoin) (collateral|loan|refinanc|pr\u00eat)", body, re.I):
        btc_desc_len += 1
    if matches >= 2 or btc_desc_len >= 3:
        flag("Z6_generic", rel, "MEDIUM", "btc_mechanics_duplicated",
             f"Page projet immobilier qui duplique la mécanique BTC lending ({matches} signatures, {btc_desc_len} mentions) — devrait référencer la page générique")

# ───────────────────────────────────────────────────────────
# Z7. Dubai Villa — Al Barari (quartier) vs Solaria (emprunteur)
# ───────────────────────────────────────────────────────────
dubai_pages = [(rel,fm,body) for rel,fm,body in all_pages
               if "dubai" in rel.lower() or re.search(r"Dubai Villa|Al Barari|Solaria", body)]

for rel, fm, body in dubai_pages:
    mentions_al_barari = bool(re.search(r"Al[- ]Barari", body, re.I))
    mentions_solaria = bool(re.search(r"Solaria", body))
    if mentions_al_barari and not mentions_solaria and ("dubai" in rel.lower()):
        flag("Z7_dubai", rel, "HIGH", "dubai_missing_solaria",
             "Page Dubai Villa Al Barari sans mention de Solaria (l'emprunteur du prêt BTC)")
    if mentions_solaria and not mentions_al_barari and ("dubai" in rel.lower()):
        flag("Z7_dubai", rel, "MEDIUM", "dubai_missing_al_barari",
             "Page Dubai sans mention d'Al Barari (la localisation)")

# ───────────────────────────────────────────────────────────
# Export
# ───────────────────────────────────────────────────────────
print(f"\nTotal findings Passe 2 : {len(findings)}")
by_zone = defaultdict(int)
by_sev  = defaultdict(int)
by_kind = defaultdict(int)
for f in findings:
    by_zone[f["zone"]] += 1
    by_sev[f["severity"]] += 1
    by_kind[f["kind"]] += 1

print("\n-- Par zone --")
for k,v in sorted(by_zone.items(), key=lambda x:-x[1]):
    print(f"  {k}: {v}")
print("\n-- Par sévérité --")
for k,v in sorted(by_sev.items()): print(f"  {k}: {v}")
print("\n-- Par type --")
for k,v in sorted(by_kind.items(), key=lambda x:-x[1]): print(f"  {k}: {v}")

out = Path("/sessions/trusting-festive-ride/audit_pass2_findings.json")
out.write_text(json.dumps(findings, ensure_ascii=False, indent=2))
print(f"\nDump: {out}")
