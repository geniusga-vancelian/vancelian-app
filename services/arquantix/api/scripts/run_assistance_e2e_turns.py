#!/usr/bin/env python3
"""
E2E minimal — joue le scénario S01 contre l’API locale comme **client métier**.

Usage (depuis ``services/arquantix/api`` avec DB + API up) :

    API_BASE_URL=http://127.0.0.1:8000 python3 scripts/run_assistance_e2e_turns.py

Identité :

  - En prod/app, le JWT utilise toujours ``sub`` = ``au:<admin_users.id>``
    (:mod:`services.auth.jwt_user_claims`) ;
  - Un **client** est une ligne ``admin_users`` avec ``person_id`` +
    ``pe_clients`` ; ce n’est pas une table séparée « Customer ».

Sélection par défaut : email ``gaelitier@gmail.com`` (override :
``ASSISTANCE_E2E_EMAIL``). Sinon : ``PERSON_ID=<uuid>``.

Vérification optionnelle : au moins un ``pe_orders`` ou ``pe_trades``
(rattaché à ce ``client_id`` via les commandes). Sinon refus, sauf si
``ASSISTANCE_E2E_SKIP_ORDER_CHECK=1``.

Enchaînement : chaque ``POST .../chat/turn`` est **bloquant** jusqu'à la
réponse HTTP complète du bot : aucun message utilisateur suivant n'est
envoyé tant que la réponse n'est pas arrivée.

Optionnel : ``ASSISTANCE_E2E_PAUSE_AFTER_ASSISTANT_SEC`` (nombre de
secondes de pause après chaque réponse, pour cadence « humaine »).

Après le tour 2, si la réponse ne semble pas lister des mouvements
concrets (heuristique sur le texte), le tour 3 (insistance) est joué ;
sinon il est sauté. ``ASSISTANCE_E2E_FORCE_INSIST=1`` envoie toujours le
tour 3.

Le script émet un JWT puis enchaîne ``POST /api/app/assistance/chat/turn``.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
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
from services.portfolio_engine.clients.models import Client as PeClient
from services.portfolio_engine.orders.models import Order
from services.portfolio_engine.trades.models import Trade

# Scénario E2E « dépôt / visibilité transactions » : délais puis absence
# visuelle dans l'historique, insistance données concrètes, tension sobre.
SCENARIO_MESSAGES = [
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
        "Je vois. Là tout de suite, ça reste un peu abstrait pour moi : tu ne "
        "peux pas me donner d’infos plus concrètes sur mes **dernières "
        "transactions**, ou au moins vérifier si mon dernier dépôt apparaît "
        "quelque part de votre côté ? Ce serait vraiment rassurant."
    ),
    (
        "Je te demande ça avec la tête froide mais je dois être honnête : le "
        "virement est bien parti de mon compte en banque. Je n’aimerais pas "
        "dramatiser, mais ça fait quand même un peu flipper qu’ici je ne voie "
        "rien d’écrit encore. Tu peux m’aider à comprendre ce qui est encore "
        "possible (délai, statut à vérifier, où regarder pour être tranquille) "
        "sans être dans l’alarme gratuite — juste avoir une ligne claire ?"
    ),
]


def _assistant_provides_transaction_visibility(body: str) -> bool:
    """Heuristique : la réponse semble-t-elle donner des mouvements chiffrés ?

    Conçu pour être **conservateur** : en cas de doute, on considère qu'il
    n'y a pas assez de visibilité et le tour d'insistance est joué.
    """
    if not body or len(body) < 120:
        return False
    low = body.lower()
    amounts = re.findall(
        r"\d{1,3}(?:[ \u00a0]\d{3})*(?:[.,]\d{2})\s*€|\d+[.,]\d{2}\s*€",
        body,
    )
    euroish = len(amounts) >= 2
    tabular = body.count("|") >= 6
    dated = bool(
        re.search(
            r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b|\b20\d{2}-\d{2}-\d{2}\b",
            body,
        )
    )
    lex = any(
        w in low
        for w in (
            "transaction",
            "mouvement",
            "opération",
            "virement",
            "crédit",
            "débit",
        )
    )
    if tabular and amounts:
        return True
    if euroish and lex:
        return True
    if dated and len(amounts) >= 1 and lex:
        return True
    return False


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
        _assert_client_has_portfolio_activity(db, pc, label=f"PERSON_ID={forced}")
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
            f"L’utilisateur email={email!r} (id={u.id}) n’a pas de person_id "
            "(compte back-office pur, pas client app)."
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
) -> dict[str, Any]:
    body: dict[str, Any] = {"content": content}
    if conversation_id:
        body["conversation_id"] = conversation_id
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


def main() -> int:
    base = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000").strip()
    pause_sec = float(
        os.environ.get("ASSISTANCE_E2E_PAUSE_AFTER_ASSISTANT_SEC", "0") or "0"
    )
    force_insist = (
        os.environ.get("ASSISTANCE_E2E_FORCE_INSIST", "").strip() == "1"
    )

    with SessionLocal() as db:
        user, client = _pick_user_and_client(db)
        token = create_access_token(build_user_jwt_access_base_claims(user))
        print(
            f"Client app (admin_users) id={user.id} email={user.email!r} "
            f"person_id={user.person_id} client_id={client.id}"
        )
        print(f"API_BASE_URL={base}\n")

    m1, m2, m3, m4 = SCENARIO_MESSAGES
    conv: str | None = None

    def run_turn(step_label: str, msg: str) -> dict[str, Any]:
        nonlocal conv
        print(f"--- {step_label} (user) ---\n{msg}\n")
        print("(Envoi POST — attente bloquante de la réponse complète du serveur.)")
        reply = _post_turn(base, token, msg, conv)
        conv = str(reply["conversation_id"])
        content = reply.get("content") or ""
        print(
            f"--- {step_label} (assistant) agent={reply.get('agent_used')} "
            f"message_id={reply.get('message_id')} ---"
        )
        print(content[:6000] + ("…" if len(content) > 6000 else ""))
        print()
        print(
            "--- Réponse terminée ; le corps HTTP est lu en entier. "
            "Prochain message utilisateur uniquement après ce point."
        )
        if pause_sec > 0:
            print(f"(Pause ASSISTANCE_E2E_PAUSE_AFTER_ASSISTANT_SEC={pause_sec}s)\n")
            time.sleep(pause_sec)
        else:
            print()
        return reply

    _ = run_turn("1 — infos dépôt", m1)
    r2 = run_turn("2 — dépôt invisible dans l'historique", m2)

    c2 = (r2.get("content") or "")
    show_insist = force_insist or not _assistant_provides_transaction_visibility(
        c2
    )
    if show_insist:
        r3 = run_turn("3 — insistance données / dernières transactions", m3)
    else:
        print(
            "--- Tour 3 (insistance) non envoyé : heuristique = visibilité "
            "mouvements plausible dans la réponse du tour 2. "
            "Forcer avec ASSISTANCE_E2E_FORCE_INSIST=1 pour envoyer quand même. ---\n"
        )

    _ = run_turn("4 — inquiétude mesurée (virement parti, rien vu côté app)", m4)

    print(f"Conversation finale : {conv}")
    print(
        "Audit admin : Clients → person_id ci-dessus → conversations assistance →"
        f" ouvrir {conv}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
