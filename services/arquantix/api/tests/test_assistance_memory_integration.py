"""Tests d'intégration de `services.assistance.memory` (Palier 2 D.2).

Avec DB Postgres réelle (transaction rollback automatique via fixture `db`)
et mock de `httpx.post` pour simuler les réponses du LLM summarizer.

Couvre :
  - `load_memory_state` (lecture snapshot)
  - `_consolidate_sync` end-to-end (cas nominal, idempotence, no-op,
    fallback heuristique sur LLM down)
  - `consolidate_conversation` (orchestration async + lock par conv)

Stratégie d'isolation :
  - Le fixture `db` ouvre une transaction à savepoint qui est rollback
    en fin de test → pas de pollution DB.
  - Pour les tests qui appellent `_consolidate_sync` (lequel utilise
    `session_factory()` → ouvre **une nouvelle session** indépendante),
    on injecte une factory custom qui retourne la session fixture sans
    la fermer (`_NonClosingSession`). Comme ça les écritures faites
    dans `_consolidate_sync` participent à la même transaction et sont
    rollback en fin de test.
  - `consolidate_conversation` (full async, utilise `asyncio.to_thread`)
    est testée séparément avec mock complet pour ne pas franchir le
    boundary thread/transaction (problématique avec SQLAlchemy).
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID

import httpx
import pytest

from database import (
    AssistanceConversation,
    AssistanceMessage,
)
from services.assistance import memory
from services.portfolio_engine.clients.models import Client as PeClients

from tests.conftest import make_linked_client


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


def _make_conv_with_messages(
    db,
    *,
    n_user_turns: int = 5,
    msg_chars: int = 200,
    summary: str | None = None,
    facts: list | None = None,
    summarized_until_turn: int | None = None,
) -> tuple[PeClients, AssistanceConversation, list[AssistanceMessage]]:
    """Crée un client + conv + 2*N tours alternant user/assistant.

    `msg_chars` détermine la longueur approx. de chaque message (utile pour
    contrôler `should_consolidate`). À titre indicatif :
      - 200 chars/msg × 8 msgs ≈ 400 tokens (sous seuil floor 1000)
      - 2000 chars/msg × 8 msgs ≈ 4000 tokens (déclenche consolidation)
    """
    client = make_linked_client(db, email=f"mem-{uuid.uuid4().hex[:8]}@example.com")
    conv = AssistanceConversation(
        id=uuid.uuid4(),
        client_id=client.id,
        title="Test conv",
        status="active",
        conversation_summary=summary,
        conversation_facts=facts if facts is not None else [],
        summarized_until_turn=summarized_until_turn,
    )
    db.add(conv)
    db.flush()

    messages = []
    # Phrase de référence ≈ 50 chars : on répète pour atteindre msg_chars.
    base_phrase = "contenu détaillé pour atteindre le seuil token. "
    for i in range(n_user_turns * 2):
        role = "user" if i % 2 == 0 else "assistant"
        repeats = max(1, msg_chars // len(base_phrase))
        m = AssistanceMessage(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            turn_index=i,
            role=role,
            content=f"[{role} #{i}] " + base_phrase * repeats,
        )
        db.add(m)
        messages.append(m)
    db.flush()
    return client, conv, messages


class _NonClosingSession:
    """Wrapper proxy autour de la session fixture pour les tests d'intégration.

    Spécificités vs une vraie SQLAlchemy Session :
      - `close()` est no-op : le fixture `db` du conftest s'occupe du
        rollback global en fin de test, on ne doit pas fermer la session
        transactionnelle au milieu.
      - `commit()` est dégradé en `flush()` : la fixture utilise un
        savepoint nested rollbacké en fin de test ; un vrai `commit`
        consomme ce savepoint et casse l'isolation. Un `flush` suffit
        pour matérialiser les écritures dans la transaction (visibles via
        `db.refresh()` côté test) tout en restant rollback-safe.

    Garantit que les tests intégration restent **idempotents** et
    **isolés** sans toucher au code de production (lequel doit garder
    son `db.commit()` pour la prod, ce qui est testé indirectement par
    le fait que les écritures sont visibles end-of-flow).
    """

    def __init__(self, db):
        self._db = db

    def __getattr__(self, name):
        return getattr(self._db, name)

    def close(self):
        return None

    def commit(self):
        # Substitute commit→flush pour rester dans le savepoint du fixture.
        self._db.flush()


def _session_factory_using(db):
    """Retourne une factory qui yield la session fixture sans la fermer."""
    return lambda: _NonClosingSession(db)


def _llm_response_factory(
    *,
    summary: str = "Résumé de test.",
    facts: list | None = None,
    open_points: list | None = None,
    raise_error: bool = False,
    status_code: int = 200,
):
    """Construit une closure qui mock `httpx.post` pour retourner un payload OpenAI."""
    payload_facts = facts if facts is not None else []
    payload_open = open_points if open_points is not None else []
    body = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {"summary": summary, "facts": payload_facts, "open_points": payload_open}
                    )
                }
            }
        ]
    }

    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: A002
        if raise_error:
            raise httpx.ConnectError("simulated network error")
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = status_code
        resp.text = "fake error" if status_code >= 400 else ""
        resp.json = MagicMock(return_value=body)
        return resp

    return fake_post


# ─────────────────────────────────────────────────────────────────────────
# `load_memory_state`
# ─────────────────────────────────────────────────────────────────────────


class TestLoadMemoryState:
    def test_returns_none_for_unknown_conv(self, db):
        out = memory.load_memory_state(db, uuid.uuid4())
        assert out is None

    def test_returns_snapshot_with_empty_defaults(self, db):
        client, conv, _ = _make_conv_with_messages(db, n_user_turns=1)
        state = memory.load_memory_state(db, conv.id)
        assert state is not None
        assert state.conversation_summary is None
        assert state.conversation_facts == []
        assert state.summarized_until_turn is None
        assert state.summary_updated_at is None
        assert state.client_long_memory == {}

    def test_returns_snapshot_with_persisted_values(self, db):
        client, conv, _ = _make_conv_with_messages(
            db,
            n_user_turns=1,
            summary="déjà résumé",
            facts=[{"type": "goal", "value": "PEA", "confidence": 0.9}],
            summarized_until_turn=5,
        )
        # Patch directement la mémoire client
        client.assistance_long_memory = {
            "facts": [{"type": "goal", "value": "PEA", "confidence": 0.9}]
        }
        db.flush()

        state = memory.load_memory_state(db, conv.id)
        assert state.conversation_summary == "déjà résumé"
        assert state.summarized_until_turn == 5
        assert len(state.conversation_facts) == 1
        assert len(state.client_long_memory["facts"]) == 1


# ─────────────────────────────────────────────────────────────────────────
# `_consolidate_sync` — flux complet
# ─────────────────────────────────────────────────────────────────────────


class TestConsolidateSync:
    """Tests directs du synchrone (évite la complexité asyncio.to_thread)."""

    def test_no_op_when_conv_gone(self, db):
        """Une conv inexistante ne doit pas crash, juste return."""
        # Ne raise pas
        memory._consolidate_sync(_session_factory_using(db), uuid.uuid4())

    def test_no_op_when_too_few_messages(self, db, monkeypatch):
        """< 2 msgs → rien à compresser."""
        client, conv, _ = _make_conv_with_messages(db, n_user_turns=0)
        # 0 messages → no-op (pas de crash, pas d'écriture)
        # Ajout d'un seul message pour tester le seuil "< 2"
        db.add(AssistanceMessage(
            id=uuid.uuid4(), conversation_id=conv.id, turn_index=0,
            role="user", content="solo",
        ))
        db.flush()
        memory._consolidate_sync(_session_factory_using(db), conv.id)
        # Aucun summary ne doit être créé
        db.refresh(conv)
        assert conv.conversation_summary is None
        assert conv.summarized_until_turn is None

    def test_no_op_below_threshold(self, db, monkeypatch):
        """Si total tokens < threshold, on ne consolide PAS."""
        monkeypatch.setenv("ASSISTANCE_SUMMARY_THRESHOLD_TOKENS", "100000")
        client, conv, _ = _make_conv_with_messages(db, n_user_turns=3, msg_chars=50)

        memory._consolidate_sync(_session_factory_using(db), conv.id)

        db.refresh(conv)
        assert conv.conversation_summary is None
        assert conv.conversation_facts == []
        assert conv.summarized_until_turn is None

    def test_writes_summary_and_facts_when_threshold_exceeded(self, db, monkeypatch):
        """Cas nominal : threshold dépassé + LLM répond → écriture summary + facts + client memory."""
        monkeypatch.setenv("ASSISTANCE_SUMMARY_THRESHOLD_TOKENS", "100")
        monkeypatch.setattr(memory, "OPENAI_API_KEY", "test-key")

        # Mock LLM
        fake_post = _llm_response_factory(
            summary="Le client veut investir 50k€ sur 10 ans.",
            facts=[
                {
                    "type": "investment_target",
                    "value": 50000,
                    "confidence": 0.95,
                    "evidence": "investir 50k€",
                },
                {
                    "type": "investment_horizon",
                    "value": 120,
                    "confidence": 0.9,
                    "evidence": "10 ans",
                },
            ],
        )
        monkeypatch.setattr(httpx, "post", fake_post)

        client, conv, msgs = _make_conv_with_messages(db, n_user_turns=4, msg_chars=2000)

        memory._consolidate_sync(_session_factory_using(db), conv.id)

        db.refresh(conv)
        db.refresh(client)

        assert conv.conversation_summary == "Le client veut investir 50k€ sur 10 ans."
        assert len(conv.conversation_facts) == 2
        assert conv.summarized_until_turn == max(m.turn_index for m in msgs)
        assert conv.summary_updated_at is not None

        # Mémoire client agrégée
        assert "facts" in client.assistance_long_memory
        assert len(client.assistance_long_memory["facts"]) == 2
        # Traçabilité : source_conversation_id + timestamps
        f = client.assistance_long_memory["facts"][0]
        assert f["source_conversation_id"] == str(conv.id)
        assert "first_seen_at" in f
        assert "last_seen_at" in f

    def test_idempotent_second_run_below_threshold(self, db, monkeypatch):
        """Après une 1ère consolidation, un 2ème run sans nouveau message ne refait rien."""
        monkeypatch.setenv("ASSISTANCE_SUMMARY_THRESHOLD_TOKENS", "100")
        monkeypatch.setattr(memory, "OPENAI_API_KEY", "test-key")

        call_count = {"n": 0}

        def counting_fake_post(*args, **kwargs):
            call_count["n"] += 1
            return _llm_response_factory(summary="Round " + str(call_count["n"]))(*args, **kwargs)

        monkeypatch.setattr(httpx, "post", counting_fake_post)

        client, conv, msgs = _make_conv_with_messages(db, n_user_turns=4, msg_chars=2000)

        # Run 1
        memory._consolidate_sync(_session_factory_using(db), conv.id)
        assert call_count["n"] == 1

        # Run 2 sans nouveau message : on a déjà absorbé tous les tours,
        # donc new_turns = [] → pas de 2ème appel LLM.
        memory._consolidate_sync(_session_factory_using(db), conv.id)
        assert call_count["n"] == 1  # toujours 1, pas de re-call

    def test_uses_heuristic_fallback_when_llm_fails(self, db, monkeypatch):
        """Si httpx.post raise, on tombe sur le fallback heuristique (ne crash pas)."""
        monkeypatch.setenv("ASSISTANCE_SUMMARY_THRESHOLD_TOKENS", "100")
        monkeypatch.setattr(memory, "OPENAI_API_KEY", "test-key")

        fake_post_fail = _llm_response_factory(raise_error=True)
        monkeypatch.setattr(httpx, "post", fake_post_fail)

        client, conv, _ = _make_conv_with_messages(db, n_user_turns=3, msg_chars=2000)

        memory._consolidate_sync(_session_factory_using(db), conv.id)

        db.refresh(conv)
        # Summary contient le marqueur dégradé
        assert conv.conversation_summary is not None
        assert "[Mémoire dégradée]" in conv.conversation_summary
        # Pas de facts (heuristique conservateur)
        assert conv.conversation_facts == []
        # summarized_until_turn AVANCE quand même (sinon retry infini)
        assert conv.summarized_until_turn is not None

    def test_uses_heuristic_when_llm_returns_invalid_json(self, db, monkeypatch):
        """JSON parsing fail → fallback."""
        monkeypatch.setenv("ASSISTANCE_SUMMARY_THRESHOLD_TOKENS", "100")
        monkeypatch.setattr(memory, "OPENAI_API_KEY", "test-key")

        def bad_json_post(url, headers=None, json=None, timeout=None):
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.json = MagicMock(return_value={
                "choices": [{"message": {"content": "this is not json {{{ broken"}}]
            })
            return resp

        monkeypatch.setattr(httpx, "post", bad_json_post)

        client, conv, _ = _make_conv_with_messages(db, n_user_turns=3, msg_chars=2000)

        memory._consolidate_sync(_session_factory_using(db), conv.id)

        db.refresh(conv)
        assert "[Mémoire dégradée]" in (conv.conversation_summary or "")

    def test_uses_heuristic_when_llm_returns_http_error(self, db, monkeypatch):
        """HTTP 500 → fallback heuristique."""
        monkeypatch.setenv("ASSISTANCE_SUMMARY_THRESHOLD_TOKENS", "100")
        monkeypatch.setattr(memory, "OPENAI_API_KEY", "test-key")

        fake_post_500 = _llm_response_factory(status_code=500)
        monkeypatch.setattr(httpx, "post", fake_post_500)

        client, conv, _ = _make_conv_with_messages(db, n_user_turns=3, msg_chars=2000)

        memory._consolidate_sync(_session_factory_using(db), conv.id)

        db.refresh(conv)
        assert "[Mémoire dégradée]" in (conv.conversation_summary or "")

    def test_facts_dedupliques_through_runs_via_long_memory(self, db, monkeypatch):
        """Au 2ème tour de consolidation, un fact identique ne crée pas de doublon."""
        monkeypatch.setenv("ASSISTANCE_SUMMARY_THRESHOLD_TOKENS", "100")
        monkeypatch.setattr(memory, "OPENAI_API_KEY", "test-key")

        def post_with_same_fact(*args, **kwargs):
            return _llm_response_factory(
                summary="r",
                facts=[{"type": "goal", "value": "PEA", "confidence": 0.9, "evidence": "x"}],
            )(*args, **kwargs)

        monkeypatch.setattr(httpx, "post", post_with_same_fact)

        client, conv, msgs = _make_conv_with_messages(db, n_user_turns=3, msg_chars=2000)

        # Run 1
        memory._consolidate_sync(_session_factory_using(db), conv.id)
        db.refresh(client)
        assert len(client.assistance_long_memory["facts"]) == 1

        # Ajout 2 nouveaux messages → re-déclenche la consolidation
        db.add(AssistanceMessage(
            id=uuid.uuid4(), conversation_id=conv.id, turn_index=10,
            role="user", content="x" * 5000,
        ))
        db.add(AssistanceMessage(
            id=uuid.uuid4(), conversation_id=conv.id, turn_index=11,
            role="assistant", content="x" * 5000,
        ))
        db.flush()

        memory._consolidate_sync(_session_factory_using(db), conv.id)
        db.refresh(client)
        # Toujours 1 fact (dédup par (type, value normalisée)) — last_seen_at refresh
        assert len(client.assistance_long_memory["facts"]) == 1

    def test_horizon_evolution_creates_new_long_memory_entry(self, db, monkeypatch):
        """Append-mostly : si la valeur d'un fact change, le nouveau coexiste avec l'ancien."""
        monkeypatch.setenv("ASSISTANCE_SUMMARY_THRESHOLD_TOKENS", "100")
        monkeypatch.setattr(memory, "OPENAI_API_KEY", "test-key")

        runs = [
            [{"type": "investment_horizon", "value": 60, "confidence": 0.9, "evidence": "5 ans"}],
            [{"type": "investment_horizon", "value": 84, "confidence": 0.9, "evidence": "7 ans"}],
        ]

        def staged_post(*args, **kwargs):
            facts = runs.pop(0) if runs else []
            return _llm_response_factory(facts=facts)(*args, **kwargs)

        monkeypatch.setattr(httpx, "post", staged_post)

        client, conv, _ = _make_conv_with_messages(db, n_user_turns=3, msg_chars=2000)
        memory._consolidate_sync(_session_factory_using(db), conv.id)

        # Ajout messages → 2ème consolidation
        db.add(AssistanceMessage(
            id=uuid.uuid4(), conversation_id=conv.id, turn_index=10,
            role="user", content="x" * 5000,
        ))
        db.add(AssistanceMessage(
            id=uuid.uuid4(), conversation_id=conv.id, turn_index=11,
            role="assistant", content="x" * 5000,
        ))
        db.flush()

        memory._consolidate_sync(_session_factory_using(db), conv.id)
        db.refresh(client)

        # 2 entries : l'historique des horizons coexiste
        long_facts = client.assistance_long_memory["facts"]
        horizons = sorted(
            f["value"] for f in long_facts if f.get("type") == "investment_horizon"
        )
        assert horizons == [60, 84]


# ─────────────────────────────────────────────────────────────────────────
# `consolidate_conversation` — orchestration async + lock
# ─────────────────────────────────────────────────────────────────────────


class TestConsolidateConversationAsync:
    """L'orchestration async par-dessus _consolidate_sync."""

    @pytest.mark.asyncio
    async def test_swallows_exceptions(self, monkeypatch):
        """Toute exception du sync doit être catchée (best-effort, pas de propagation)."""
        # Mock _consolidate_sync pour raise
        def failing_sync(session_factory, conv_id):
            raise RuntimeError("simulated crash")

        monkeypatch.setattr(memory, "_consolidate_sync", failing_sync)

        # Si l'exception était propagée, le test échouerait avec le RuntimeError
        await memory.consolidate_conversation(
            session_factory=lambda: None,
            conversation_id=uuid.uuid4(),
        )
        # Si on arrive ici sans raise, c'est OK

    @pytest.mark.asyncio
    async def test_calls_consolidate_sync_with_correct_args(self, monkeypatch):
        captured = {}

        def spy_sync(session_factory, conv_id):
            captured["session_factory"] = session_factory
            captured["conv_id"] = conv_id

        monkeypatch.setattr(memory, "_consolidate_sync", spy_sync)

        my_factory = lambda: None
        my_id = uuid.uuid4()

        await memory.consolidate_conversation(
            session_factory=my_factory,
            conversation_id=my_id,
        )

        assert captured["session_factory"] is my_factory
        assert captured["conv_id"] == my_id

    @pytest.mark.asyncio
    async def test_lock_serializes_concurrent_consolidations(self, monkeypatch):
        """2 calls concurrents sur la même conv → sérialisés (pas en parallèle)."""
        execution_order = []

        async def slow_sync_simulation(session_factory, conv_id):
            execution_order.append(("start", conv_id))
            await asyncio.sleep(0.05)
            execution_order.append(("end", conv_id))

        # On ne peut pas remplacer _consolidate_sync directement (il est sync).
        # On remplace _lock_for + asyncio.to_thread pour simuler.
        # Plus simple : on remplace consolidate_conversation localement avec
        # un sleep dans le sync.
        def slow_sync(session_factory, conv_id):
            execution_order.append(("start", str(conv_id)))
            import time
            time.sleep(0.05)
            execution_order.append(("end", str(conv_id)))

        monkeypatch.setattr(memory, "_consolidate_sync", slow_sync)

        same_id = uuid.uuid4()
        # Lance 2 consolidations concurrentes sur la MÊME conv
        await asyncio.gather(
            memory.consolidate_conversation(session_factory=lambda: None, conversation_id=same_id),
            memory.consolidate_conversation(session_factory=lambda: None, conversation_id=same_id),
        )

        # Sérialisation : start_1, end_1, start_2, end_2 (jamais entrelacés)
        assert len(execution_order) == 4
        assert execution_order[0][0] == "start"
        assert execution_order[1][0] == "end"
        assert execution_order[2][0] == "start"
        assert execution_order[3][0] == "end"

    @pytest.mark.asyncio
    async def test_different_convs_run_in_parallel(self, monkeypatch):
        """2 calls sur des convs DIFFÉRENTES → s'exécutent en parallèle (locks distincts)."""
        in_progress = {"max": 0, "current": 0}

        def parallel_aware_sync(session_factory, conv_id):
            in_progress["current"] += 1
            in_progress["max"] = max(in_progress["max"], in_progress["current"])
            import time
            time.sleep(0.05)
            in_progress["current"] -= 1

        monkeypatch.setattr(memory, "_consolidate_sync", parallel_aware_sync)

        await asyncio.gather(
            memory.consolidate_conversation(session_factory=lambda: None, conversation_id=uuid.uuid4()),
            memory.consolidate_conversation(session_factory=lambda: None, conversation_id=uuid.uuid4()),
            memory.consolidate_conversation(session_factory=lambda: None, conversation_id=uuid.uuid4()),
        )

        # Au moins 2 ont tourné en parallèle (locks par conv_id distincts)
        assert in_progress["max"] >= 2
