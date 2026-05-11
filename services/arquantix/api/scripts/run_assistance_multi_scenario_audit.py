#!/usr/bin/env python3
"""
Audit multi-scénarios — conversations E2E + deux analyses :

1. **Dialogue** : lisibilité en ne regardant que user + assistant (longueurs, mots-clés,
   cohérence minimale avec l’intent du tour).
2. **Conformité code** : relit les lignes golden (tables ``AssistanceMessage`` +
   ``Assistance_agent_decisions`` via :mod:`services.assistance.golden_trace_export`) —
   pour un ``data_need`` ``transaction_data`` / ``account_data`` / ``kyc_data``, vérifie
   qu’au moins un outil de lecture attendu **a été appelé** **ou** qu’une ligne
   ``policy_data_need_reads`` existe (audit soft comme dans
   ``data_need_read_policy``).

Usage (répertoire conseillé ``services/arquantix/api``) :

    API_BASE_URL=http://127.0.0.1:8000 \\
    ASSISTANCE_E2E_SKIP_ORDER_CHECK=1 \\
    python3 scripts/run_assistance_multi_scenario_audit.py

  # Sous-ensemble :

    python3 scripts/run_assistance_multi_scenario_audit.py \\
      --scenarios s01_deposit,s02_moves_verify_laconic_stress

  # Scénario « widget Bitcoin implicite » (utilisateur ne nomme jamais BTC/Bitcoin).
  # Après les 4 tours implicites, si aucune ``instrument_detail_card`` n’est reçue,
  # le script enchaîne jusqu’à 2 tours avec ``agent_hint=product``
  # (équivalent Flutter après QCM). Désactiver ce chaînage :

    ASSISTANCE_S06_SKIP_ADAPTIVE_CHAIN=1 python3 scripts/run_assistance_multi_scenario_audit.py \\
      --scenarios s06_implicit_btc_widget

  # Rapport JSON (en plus du texte) :

    python3 scripts/run_assistance_multi_scenario_audit.py --json-out /tmp/audit.json

Même identité / prérequis que ``run_assistance_e2e_turns.py``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from uuid import UUID

api_dir = Path(__file__).resolve().parent.parent
os.chdir(api_dir)
sys.path.insert(0, str(api_dir))

try:
    from dotenv import load_dotenv

    load_dotenv(api_dir / ".env.local")
    load_dotenv(api_dir / ".env")
except ImportError:
    pass

from sqlalchemy import func

from auth import create_access_token
from database import AdminUser, Person, SessionLocal
from services.auth.jwt_user_claims import build_user_jwt_access_base_claims
from services.assistance.data_need_read_policy import (
    DATA_NEEDS_REQUIRING_READ,
    data_need_reads_satisfied,
)
from services.assistance.golden_trace_export import (
    export_conversation_turns_jsonl_strings,
)
from services.portfolio_engine.clients.models import Client as PeClient
from services.portfolio_engine.orders.models import Order
from services.portfolio_engine.trades.models import Trade


# ---------------------------------------------------------------------------
# Scénarios (messages utilisateur)
# ---------------------------------------------------------------------------


@dataclass
class Scenario:
    id: str
    title: str
    messages: list[str]
    dialogue_checks: list[Callable[[list[dict[str, Any]]], list[str]]] = field(
        default_factory=list
    )


def _check_no_empty_assistant(transcript: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for i, t in enumerate(transcript, start=1):
        c = (t.get("assistant") or "").strip()
        mt = (t.get("message_type") or "text").lower()
        if not c and mt == "text":
            out.append(f"Tour {i} : assistant texte vide.")
    return out


def _warn_service_unavailable(transcript: list[dict[str, Any]]) -> list[str]:
    """Pas un échec bloquant — utile pour cold start."""
    out: list[str] = []
    for i, t in enumerate(transcript, start=1):
        low = (t.get("assistant") or "").lower()
        if "temporairement indisponible" in low:
            out.append(f"Tour {i} : message « service indisponible » (fallback).")
    return out


def _s02_turn3_offers_followup(transcript: list[dict[str, Any]]) -> list[str]:
    """Après « Les offres », on attend encore du sens produit / offres / contexte."""
    if len(transcript) < 3:
        return []
    assistant = transcript[2].get("assistant") or ""
    low = assistant.lower()
    hints = (
        "offre",
        "épargne",
        "placement",
        "produit",
        "pack",
        "portefeuille",
        "risque",
    )
    if not any(h in low for h in hints):
        return [
            "Tour 3 : après « Les offres », la réponse assistant ne réactive pas "
            "clairement le thème offres/produits — possible rupture de continuité."
        ]
    return []


def _s02_turn2_amount_grounded(transcript: list[dict[str, Any]]) -> list[str]:
    """Tour 2 : question ~500 € — réponse soit ancrée (€, montant, date…) soit prudente."""
    if len(transcript) < 2:
        return []
    assistant = transcript[1].get("assistant") or ""
    low = assistant.lower()
    has_number = bool(
        re.search(
            r"500\s*€|[\d]+[.,]\d{2}\s*€|environ\s*500|five hundred",
            low,
            re.I,
        )
    )
    prudence = any(
        w in low for w in ("ne vois pas", "ne trouve pas", "pas retrouvé", "confirmer", "vérifi")
    )
    if has_number or prudence or len(assistant) > 220:
        return []
    return [
        "Tour 2 : réponse très courte sans € ni marqueurs de prudence — risque peu "
        "informatif sur la question ~500 €."
    ]


def _extract_embed_snapshot(reply: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Types d'embed HTTP + symbols des cartes ``instrument_detail_card``."""
    embeds = reply.get("embeds") or []
    if not isinstance(embeds, list):
        return [], []

    embed_types: list[str] = []
    instrument_syms: list[str] = []
    for e in embeds:
        if not isinstance(e, dict):
            continue
        t = str(e.get("type") or "").strip()
        if t:
            embed_types.append(t)
        if t == "instrument_detail_card":
            sym = e.get("symbol")
            if sym:
                instrument_syms.append(str(sym).strip().upper())

    return embed_types, instrument_syms


def _s06_user_avoids_explicit_bitcoin_label(
    transcript: list[dict[str, Any]],
) -> list[str]:
    """Contrôle métier du scénario : l'utilisateur ne doit pas nommer BTC/Bitcoin."""
    pat = re.compile(r"\bbitcoin\b|\bbtc\b", re.I)
    for i, t in enumerate(transcript, start=1):
        user_text = str(t.get("user") or "")
        if pat.search(user_text):
            return [
                f"Tour {i} : le message utilisateur nomme encore Bitcoin/BTC — "
                "le scénario implicite est invalide pour ce tour."
            ]
    return []


def _s06_report_instrument_card_outcome(transcript: list[dict[str, Any]]) -> list[str]:
    """Constat lisible pour savoir si le widget ``instrument_detail_card`` est arrivé."""

    used_adaptive = any(bool(t.get("adaptive_chain")) for t in transcript)
    prelude: list[str] = []
    if used_adaptive:
        prelude.append(
            "S06 — tours adaptatifs avec ``agent_hint=product`` (équivalent du clic "
            "branche crypto / product côté app après un QCM)."
        )

    observations: list[str] = []
    for i, t in enumerate(transcript, start=1):
        et = t.get("embed_types") or []
        syms = t.get("instrument_card_symbols") or []
        if "instrument_detail_card" in et:
            observations.append(
                f"Tour {i} assistant : embed instrument_detail_card "
                f"(symboles={syms if syms else '?'})."
            )

    if observations:
        has_btc = any(
            "BTC" in (t.get("instrument_card_symbols") or [])
            for t in transcript
        )
        observations.append(
            "Synthèse S06 — au moins une carte instrument vue en HTTP "
            "(objectif « type Bitcoin » implicite : "
            f"{'symbole BTC présent dans le payload' if has_btc else 'BTC absent dans les symbols embarqués — autre actif ou symbole manquant'})."
        )
        return prelude + observations

    return prelude + [
        "Synthèse S06 — aucun embed instrument_detail_card dans les réponses HTTP "
        "(pas de widget carte côté client pour ce run, ou embed_gate / refus LLM)."
    ]


# Après les 4 messages « implicites » s06 : si le router reste en QCM ou sans carte,
# on simule le « clic » mobile (``agent_hint``) — aligné sur le client Flutter.
_S06_ADAPTIVE_STEPS: list[tuple[str, str]] = [
    (
        "Je reprends : ma question porte sur les **marchés crypto**, pas l’immobilier. "
        "Si un menu vient d’être proposé, je choisis la voie **suivi des tendances / "
        "crypto** ; réponds en **texte continu** (évite un nouveau QCM) et explique "
        "pourquoi un actif sert souvent de **repère commun**.",
        "product",
    ),
    (
        "Merci. Sans conseil d’achat décisionnel, affiche dans le chat la **fiche live** "
        "(prix instantané + courbe 24h) pour **cet actif-repère**, comme la carte market "
        "de l’application.",
        "product",
    ),
]


def _transcript_has_instrument_card(transcript: list[dict[str, Any]]) -> bool:
    for t in transcript:
        et = t.get("embed_types") or []
        if "instrument_detail_card" in et:
            return True
    return False


SCENARIOS: list[Scenario] = [
    Scenario(
        id="s01_deposit",
        title="Dépôt délais → pas dans l'historique → insistance données",
        messages=[
            (
                "Bonjour. J’aimerais bien comprendre comment ça marche pour un dépôt : "
                "en général ça prend combien de temps avant que ça apparaisse sur mon "
                "compte, et qu’est-ce qui se passe étape par étape côté appli ou côté "
                "traitement ?"
            ),
            (
                "Merci pour les explications. En fait j’ai fait un dépôt récemment et "
                "pour l’instant je ne vois pas le mouvement dans mes transactions — "
                "est-ce que ça peut mettre encore un peu de temps, ou j’ai peut-être "
                "raté quelque chose du côté de l’app ?"
            ),
            (
                "Je vois. Tu peux me donner une vision plus concrète de mes **dernières "
                "transactions** ou du statut du dépôt dans vos systèmes ?"
            ),
            (
                "Le virement est bien parti de ma banque. Peux-tu m’indiquer ce que je "
                "peux encore vérifier côté appli pendant que ça arrive, sans alarmer "
                "inutilement ?"
            ),
        ],
        dialogue_checks=[
            _check_no_empty_assistant,
            _warn_service_unavailable,
        ],
    ),
    Scenario(
        id="s02_moves_verify_laconic_stress",
        title="Parcours doc ASSISTANCE_E2E_SCENARIO_01 — mouvements, 500 €, lacune, marchés",
        messages=[
            (
                "Bonjour, je cherche où voir mes derniers mouvements et paiements dans "
                "l’app. Tu peux m’indiquer le chemin, et me dire si je peux filtrer par mois ?"
            ),
            (
                "Merci. La semaine dernière j’ai fait un paiement ou un débit "
                "d’environ 500 € — tu peux me confirmer si tu le vois sur mon compte ?"
            ),
            "Les offres",
            (
                "Honnêtement je suis un peu inquiète avec tout ce qu’on entend sur les "
                "marchés. Tu peux m’expliquer calmement ce que ça change pour mon épargne "
                "sur 5–10 ans, sans me pousser à acheter un truc ?"
            ),
        ],
        dialogue_checks=[
            _check_no_empty_assistant,
            _warn_service_unavailable,
            _s02_turn2_amount_grounded,
            _s02_turn3_offers_followup,
        ],
    ),
    Scenario(
        id="s03_market_crypto_pulse",
        title="Ouverture thématique marchés / actifs",
        messages=[
            (
                "Salut — je suivrais bien l’actualité BTC / ETH sans tout surveiller "
                "H24 : tu conseilles quoi comme réflexes dans l’app Vancelian / quoi éviter "
                "comme comportement compulsif ?"
            ),
            "Et niveau épargne long terme, tu peux me rappeler en une phrase votre philosophie générale ?",
        ],
        dialogue_checks=[
            _check_no_empty_assistant,
            _warn_service_unavailable,
        ],
    ),
    Scenario(
        id="s04_trust_registration_edge",
        title="Inscription / données perso — ton prudent",
        messages=[
            (
                "Je veux faire avancer mon inscription mais je ne suis pas à l’aise pour "
                "envoyer encore des documents tant que ce n’est pas clair où ça partie. "
                "Tu peux m’expliquer simplement qui traite ces données chez vous ?"
            ),
            "Ok. Et où je vois où j'en suis exactement dans le parcours d'inscription ?",
        ],
        dialogue_checks=[
            _check_no_empty_assistant,
            _warn_service_unavailable,
        ],
    ),
    Scenario(
        id="s05_contradiction_correction",
        title="Corriger une affirmation mal comprise (cohérence sur 2 tours)",
        messages=[
            "Tu m’as dit tout à l’heure que les dépôts étaient instantanés — c’est toujours vrai pour un virement SEPA ?",
            (
                "Pardon, je me suis mal exprimé : je parlais d’un **virement** vers mon "
                "compte titre, pas d’une carte. Tu peux reformuler ce qui est réaliste en délai ?"
            ),
        ],
        dialogue_checks=[
            _check_no_empty_assistant,
            _warn_service_unavailable,
        ],
    ),
    Scenario(
        id="s06_implicit_btc_widget",
        title=(
            "Conseils progressifs → repère crypto implicite → fiche live ; "
            "chaînage auto product si pas de widget (QCM)"
        ),
        messages=[
            (
                "Bonjour. Je prépare mon orientation long terme et j’aimerais des "
                "conseils concrets sans jargon : comment **suivre les marchés crypto** "
                "sans passer ma vie sur les graphes, tout en gardant les pieds sur terre "
                "côté risque ?"
            ),
            (
                "Merci, ça aide. Si je voulais une **boussole minimale** — une seule "
                "chose à regarder quand tout le monde parle euphorie ou panique côté "
                "actifs digitaux — quel angle tu recommandes pour quelqu’un qui utilise "
                "surtout l’appli Vancelian sans être trader ? Sans me pousser à acheter "
                "tout de suite."
            ),
            (
                "D’accord. Parmi ce qui est **visible et coté** dans l’appli pour les "
                "cryptos, il y a presque toujours **un actif** que les gens citent "
                "avant les autres comme **repère généraliste** — même quand ils "
                "ensuite parlent d’autre chose. Tu peux m’expliquer **pourquoi** on "
                "s’en sert comme point de comparaison commun, sans me sortir tout le "
                "tableau des symboles ?"
            ),
            (
                "Ça fait sens. Dans un cadre **très neutre** (ni achat ni vente "
                "décisionnel), j’aimerais **voir la fiche live** comme dans la partie "
                "recherche/market : **prix instantané + petite courbe 24h** pour **cet "
                "actif de référence** dont tu disais qu’on s’en sert comme repère — "
                "histoire d’avoir une visualisation calme depuis le chat."
            ),
        ],
        dialogue_checks=[
            _check_no_empty_assistant,
            _warn_service_unavailable,
            _s06_user_avoids_explicit_bitcoin_label,
            _s06_report_instrument_card_outcome,
        ],
    ),
]


# ---------------------------------------------------------------------------
# Auth + HTTP (aligné sur run_assistance_e2e_turns)
# ---------------------------------------------------------------------------


def _pick_user_and_client(db) -> tuple[AdminUser, PeClient]:
    forced = os.environ.get("PERSON_ID", "").strip()
    if forced:
        pid = UUID(forced)
        u = db.query(AdminUser).filter(AdminUser.person_id == pid).first()
        if u is None:
            raise SystemExit(f"No AdminUser for PERSON_ID={forced}")
        pc = db.query(PeClient).filter(PeClient.person_id == pid).first()
        if pc is None:
            raise SystemExit(f"No pe_clients row for PERSON_ID={forced}")
        _assert_person_active(db, pid)
        _assert_client_has_portfolio_activity(
            db, pc, label=f"PERSON_ID={forced}"
        )
        return u, pc

    email_default = "gaelitier@gmail.com"
    email = (
        os.environ.get("ASSISTANCE_E2E_EMAIL", email_default).strip()
        or email_default
    )
    u = (
        db.query(AdminUser)
        .filter(func.lower(AdminUser.email) == email.lower())
        .first()
    )
    if u is None:
        raise SystemExit(
            f"Aucun admin_users pour l’email {email!r}. "
            "Vérifie la base ou passe PERSON_ID=<uuid>."
        )
    if u.person_id is None:
        raise SystemExit(
            f"L’utilisateur email={email!r} (id={u.id}) n’a pas de person_id."
        )
    _assert_person_active(db, u.person_id)
    pc = (
        db.query(PeClient).filter(PeClient.person_id == u.person_id).first()
    )
    if pc is None:
        raise SystemExit(
            f"Pas de pe_clients pour person_id={u.person_id} (email={email!r})."
        )
    _assert_client_has_portfolio_activity(db, pc, label=f"email={email!r}")
    return u, pc


def _assert_client_has_portfolio_activity(
    db, pc: PeClient, *, label: str
) -> None:
    if os.environ.get("ASSISTANCE_E2E_SKIP_ORDER_CHECK", "").strip() == "1":
        return
    has_order = (
        db.query(Order.id).filter(Order.client_id == pc.id).limit(1).first()
    )
    has_trade = (
        db.query(Trade.id)
        .join(Order, Trade.order_id == Order.id)
        .filter(Order.client_id == pc.id)
        .limit(1)
        .first()
    )
    if has_order is None and has_trade is None:
        raise SystemExit(
            f"Aucune activité pe_orders / pe_trades pour client_id={pc.id} "
            f"({label}). Pour ignorer : ASSISTANCE_E2E_SKIP_ORDER_CHECK=1"
        )


def _assert_person_active(db, person_id: UUID) -> None:
    p = db.query(Person).filter(Person.id == person_id).one_or_none()
    if p is None:
        raise SystemExit(f"Person {person_id} introuvable.")
    if p.account_state in ("PARTIAL", "BLOCKED") or p.login_frozen:
        raise SystemExit(
            f"Person {person_id} non utilisable (account_state="
            f"{p.account_state!r}, login_frozen={p.login_frozen})."
        )


def _post_turn(
    base_url: str,
    token: str,
    content: str,
    conversation_id: str | None,
    *,
    agent_hint: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"content": content}
    if conversation_id:
        body["conversation_id"] = conversation_id
    if agent_hint:
        body["agent_hint"] = agent_hint
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/app/assistance/chat/turn",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise SystemExit(f"HTTP {e.code}: {detail}") from e


# ---------------------------------------------------------------------------
# Audits
# ---------------------------------------------------------------------------


def _trace_data_need(trace: dict[str, Any]) -> str | None:
    orch = trace.get("router_decision") or {}
    if isinstance(orch, dict):
        sub = orch.get("orchestration")
        if isinstance(sub, dict):
            raw = str(sub.get("data_need") or "").strip().lower()
            return raw or None
    return None


def analyze_traces_vs_policy(traces: list[dict[str, Any]]) -> list[str]:
    """Politique locale alignée sur ``data_need_read_policy`` (+ trace policy_gaps)."""
    issues: list[str] = []
    for trace in traces:
        turn_ix = trace.get("turn_index")
        need = _trace_data_need(trace)
        if not need or need not in DATA_NEEDS_REQUIRING_READ:
            continue
        tools_called = trace.get("tools_called") or []
        if not isinstance(tools_called, list):
            tools_called = []
        gaps = trace.get("policy_gaps") or []
        has_gap_audit = isinstance(gaps, list) and len(gaps) > 0

        satisfied = data_need_reads_satisfied(need, tuple(tools_called))

        # Conformité « comme le code prévoit » : lecture OU audit soft persisté (gap).
        if satisfied or has_gap_audit:
            continue

        issues.append(
            f"Tour user turn_index={turn_ix}: data_need={need!r} sans lecture "
            f"métier reconnue (tools_called={tools_called!r}) et sans entrée "
            f"policy_data_need_reads dans la trace — divergence avec la policy "
            f"audit soft attendue."
        )
    return issues


def summarize_traces_instrument_widgets(traces: list[dict[str, Any]]) -> list[str]:
    """Synthèse outil ``show_instrument_card`` + payloads embed persistés."""

    findings: list[str] = []
    for tr in traces:
        ix = tr.get("turn_index")
        tools = tr.get("tools_called") or []
        embeds = tr.get("embeds") or []
        if not isinstance(tools, list):
            tools = []
        if not isinstance(embeds, list):
            embeds = []

        if "show_instrument_card" in tools:
            syms = [
                str(e.get("symbol") or "")
                for e in embeds
                if isinstance(e, dict)
                and e.get("type") == "instrument_detail_card"
                and e.get("symbol")
            ]
            findings.append(
                f"Trace user turn_index={ix} : outil ``show_instrument_card`` avec "
                f"carte(s) symboles={syms if syms else 'voir embed JSON'}."
            )
    return findings


def analyze_transcript_dialogue(scenario: Scenario, transcript: list[dict[str, Any]]) -> list[str]:
    """Retourne des messages « problème » (liste vide si rien à signaler)."""
    flagged: list[str] = []
    for fn in scenario.dialogue_checks:
        flagged.extend(fn(transcript))

    return flagged


def run_scenario_http(
    base: str,
    token: str,
    scenario: Scenario,
    *,
    quiet: bool,
    pause_after: float,
) -> tuple[UUID, list[dict[str, Any]]]:
    conv: str | None = None
    transcript: list[dict[str, Any]] = []
    if not quiet:
        print("\n" + "═" * 70)
        print(f"▶ Scénario {scenario.id} — {scenario.title}")
        print("═" * 70)

    for step, msg in enumerate(scenario.messages, start=1):
        if not quiet:
            print(f"\n--- [{scenario.id}] tour {step}/{len(scenario.messages)} (user) ---\n")
            preview = msg if len(msg) < 560 else msg[:560] + "…"
            print(preview)

        reply = _post_turn(base, token, msg, conv)
        conv = str(reply["conversation_id"])
        embed_types, instrument_syms = _extract_embed_snapshot(reply)
        transcript.append(
            {
                "user": msg,
                "assistant": reply.get("content") or "",
                "agent_used": reply.get("agent_used"),
                "message_type": reply.get("message_type") or "text",
                "embed_types": embed_types,
                "instrument_card_symbols": instrument_syms,
            }
        )
        if not quiet:
            print(
                f"\n--- assistant agent={reply.get('agent_used')} "
                f"type={reply.get('message_type')} embeds="
                f"{embed_types if embed_types else '—'} ---\n"
            )
            ac = transcript[-1]["assistant"]
            print(ac[:4000] + ("…" if len(ac) > 4000 else ""))
        if pause_after > 0:
            time.sleep(pause_after)

    assert conv is not None

    if scenario.id == "s06_implicit_btc_widget":
        skip = (
            os.environ.get("ASSISTANCE_S06_SKIP_ADAPTIVE_CHAIN", "").strip() == "1"
        )
        if skip and not quiet:
            print(
                "\n[s06] ASSISTANCE_S06_SKIP_ADAPTIVE_CHAIN=1 — pas de chaînage "
                "``agent_hint=product``.\n"
            )
        elif not skip and not _transcript_has_instrument_card(transcript):
            if not quiet:
                print(
                    "\n[s06] Aucune carte instrument après les tours implicites — "
                    "chaînage **agent_hint=product** (équivalent choix après QCM)…\n"
                )
            for step_ai, (amsg, ahint) in enumerate(_S06_ADAPTIVE_STEPS, start=1):
                if _transcript_has_instrument_card(transcript):
                    if not quiet:
                        print(
                            f"[s06] carte reçue avant la fin du chaînage — "
                            f"arrêt avant l’étape {step_ai}/{len(_S06_ADAPTIVE_STEPS)}."
                        )
                    break
                if not quiet:
                    print(
                        f"\n--- [s06] chaînage adaptatif {step_ai}/"
                        f"{len(_S06_ADAPTIVE_STEPS)} (agent_hint={ahint}) (user) ---\n"
                    )
                    prv = amsg if len(amsg) < 560 else amsg[:560] + "…"
                    print(prv)

                reply = _post_turn(
                    base,
                    token,
                    amsg,
                    conv,
                    agent_hint=ahint,
                )
                embed_types, instrument_syms = _extract_embed_snapshot(reply)
                transcript.append(
                    {
                        "user": amsg,
                        "assistant": reply.get("content") or "",
                        "agent_used": reply.get("agent_used"),
                        "message_type": reply.get("message_type") or "text",
                        "embed_types": embed_types,
                        "instrument_card_symbols": instrument_syms,
                        "adaptive_chain": True,
                        "agent_hint": ahint,
                    }
                )
                if not quiet:
                    print(
                        f"\n--- assistant agent={reply.get('agent_used')} "
                        f"type={reply.get('message_type')} embeds="
                        f"{embed_types if embed_types else '—'} ---\n"
                    )
                    print(
                        (transcript[-1]["assistant"] or "")[:4000]
                        + (
                            "…"
                            if len(transcript[-1]["assistant"] or "") > 4000
                            else ""
                        )
                    )
                if pause_after > 0:
                    time.sleep(pause_after)

    return UUID(conv), transcript


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Multi-scénarios assistance + audit dialogue / conformité traces."
    )
    parser.add_argument(
        "--scenarios",
        default=os.environ.get("ASSISTANCE_AUDIT_SCENARIOS", "all"),
        help="Liste id séparée par virgule, ou « all » (défaut).",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Écrit le rapport structuré en JSON.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Moins de bruit (garde le résumé par scénario).",
    )
    args = parser.parse_args()

    base = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000").strip()
    pause_after = float(
        os.environ.get("ASSISTANCE_E2E_PAUSE_AFTER_ASSISTANT_SEC", "0") or "0"
    )

    want = args.scenarios.strip().lower()
    if want == "all":
        chosen = list(SCENARIOS)
    else:
        ids = {x.strip() for x in want.split(",") if x.strip()}
        id_by = {s.id: s for s in SCENARIOS}
        missing = ids - set(id_by)
        if missing:
            raise SystemExit(f"Scénarios inconnus : {sorted(missing)}")
        chosen = [id_by[i] for i in ids]

    report: dict[str, Any] = {
        "api_base_url": base,
        "scenarios": [],
        "summary": {
            "dialogue_flags": 0,
            "code_issues": 0,
        },
    }

    with SessionLocal() as db:
        user, _client = _pick_user_and_client(db)
        token = create_access_token(build_user_jwt_access_base_claims(user))
        if not args.quiet:
            print(
                f"Client id={user.id} email={user.email!r} person_id={user.person_id}"
            )
            print(f"API_BASE_URL={base}\n")

    for scenario in chosen:
        conv_id, transcript = run_scenario_http(
            base,
            token,
            scenario,
            quiet=args.quiet,
            pause_after=pause_after,
        )

        dialogue_flags = analyze_transcript_dialogue(scenario, transcript)

        with SessionLocal() as db2:
            jsonl = export_conversation_turns_jsonl_strings(
                db2, conversation_id=conv_id, recent_turn_cap=32
            )
        traces = [json.loads(line) for line in jsonl]
        code_issues = analyze_traces_vs_policy(traces)
        widget_lines = summarize_traces_instrument_widgets(traces)

        report["summary"]["dialogue_flags"] += len(dialogue_flags)
        report["summary"]["code_issues"] += len(code_issues)
        report["scenarios"].append(
            {
                "id": scenario.id,
                "title": scenario.title,
                "conversation_id": str(conv_id),
                "transcript": transcript,
                "dialogue_flags": dialogue_flags,
                "code_issues": code_issues,
                "widget_trace_notes": widget_lines,
                "trace_turns": len(traces),
                "s06_adaptive_turns": sum(
                    1 for t in transcript if t.get("adaptive_chain")
                ),
            }
        )

        print("\n" + "─" * 70)
        print(f"Rapport · {scenario.id}")
        print(f"conversation_id={conv_id}")
        ada = sum(1 for t in transcript if t.get("adaptive_chain"))
        if scenario.id == "s06_implicit_btc_widget":
            print(f"s06_tours_adaptatifs_agent_hint={ada}")
        print("\n(1) Analyse dialogue (user + bot seulement)")
        if dialogue_flags:
            for line in dialogue_flags:
                print(f"  • {line}")
        else:
            print("  OK — aucun drapeau heuristique.")

        print("\n(2) Analyse conformité code (traces DB / policy data_need)")
        if code_issues:
            for line in code_issues:
                print(f"  • {line}")
        else:
            print(
                "  OK — pour chaque tour avec data_need transaction/account/kyc, "
                "lecture métier ou audit policy_data_need_reads présent dans la trace."
            )

        if scenario.id == "s06_implicit_btc_widget" or widget_lines:
            print("\n(3) Widget carte instrument (HTTP + trace DB)")
            if widget_lines:
                for line in widget_lines:
                    print(f"  • {line}")
            else:
                print(
                    "  — Aucun ``show_instrument_card`` enregistré dans les traces "
                    "decisions pour cette conversation."
                )

    print("\n" + "═" * 70)
    print("Synthèse globale")
    print(
        f"  scénarios : {len(chosen)} · drapeaux dialogue : "
        f"{report['summary']['dialogue_flags']} · "
        f"écarts policy/code : {report['summary']['code_issues']}"
    )
    print("═" * 70)

    if args.json_out:
        # Retirer transcriptions trop lourdes si besoin — on garde tout pour audit.
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"\nJSON écrit : {args.json_out}")

    return 1 if (report["summary"]["code_issues"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
