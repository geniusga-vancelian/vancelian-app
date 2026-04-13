"""
Orchestrator for POST /conversation/turn: load → Extractor → Compliance → decide → Coach or Copywriter+Portfolio → RiskGuardian → persist.
Event sourcing: ProfileUpdated, DisclaimerShown, etc. asked_questions in profile payload.
"""
from __future__ import annotations

import copy
import hashlib
import uuid
from typing import Any
import math
import re

from sqlalchemy.orm import Session

from database import (
    ChatbotSession,
    ChatbotProfile,
    ChatbotConversationTurn,
    ChatbotAuditEvent,
    ChatbotPortfolioProposal,
)
from services.chatbot_epargne.ai.agents import coach, decide, extractor, compliance, risk_guardian, copywriter, portfolio, summarizer
from services.chatbot_epargne.questions.library import Q_GOAL_FREE, Q_GOAL_CLARIFY, Q_GOAL_FORCE_PICK
from services.chatbot_epargne.ai.agents._llm import load_prompt, hash_prompt


def _apply_extracted(profile: dict, extracted: list[dict]) -> tuple[dict, dict]:
    diff: dict[str, Any] = {}
    p = copy.deepcopy(profile)
    budget_fields = {"initial_amount", "monthly_contribution", "contribution_frequency"}
    for e in extracted:
        field = (e.get("field") or "").strip()
        val = e.get("value")
        if not field:
            continue
        conf_raw = e.get("confidence")
        try:
            conf = float(conf_raw) if conf_raw is not None else None
        except (TypeError, ValueError):
            conf = None
        if field not in budget_fields and (conf is None or conf < 0.5):
            continue
        if field in budget_fields:
            conf_key = f"{field}_confidence"
            existing_conf_raw = p.get(conf_key)
            try:
                existing_conf = float(existing_conf_raw) if existing_conf_raw is not None else None
            except (TypeError, ValueError):
                existing_conf = None
            if existing_conf is not None and existing_conf >= 0.7 and (conf is None or conf < 0.7):
                continue
            if conf is not None:
                p[conf_key] = conf
        if "." in field:
            pre, suf = field.split(".", 1)
            if pre not in p:
                p[pre] = {}
            if not isinstance(p[pre], dict):
                continue
            old = p[pre].get(suf)
            p[pre][suf] = val
            diff[field] = {"old": old, "new": val}
        else:
            old = p.get(field)
            if val is not None or field not in budget_fields:
                p[field] = val
                diff[field] = {"old": old, "new": val}
    return p, diff


def _completeness_60s(profile: dict) -> float:
    goal = profile.get("goal") or {}
    goal_ok = bool(goal.get("type") or goal.get("narrative"))
    horizon_ok = bool(profile.get("horizon_bucket") is not None or profile.get("horizon_months") is not None)
    risk_ok = profile.get("risk_tolerance_score") is not None
    return ((1.0 if goal_ok else 0.0) + (1.0 if horizon_ok else 0.0) + (1.0 if risk_ok else 0.0)) / 3.0


def _prompt_hash(parts: list[str]) -> str:
    return hashlib.sha256(("\n").join(parts).encode("utf-8")).hexdigest()

def _normalize_str_list(values: list[Any] | None) -> list[str]:
    out: list[str] = []
    for v in values or []:
        if v is None:
            continue
        if isinstance(v, str):
            s = v.strip()
            if s:
                out.append(s)
            continue
        out.append(str(v))
    return out

def _dedupe_preserve(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))

def _dedupe_facts_preserve(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if not s:
            continue
        norm = " ".join(s.lower().split())
        if norm in seen:
            continue
        seen.add(norm)
        out.append(s)
    return out

def _has(value: Any) -> bool:
    return value is not None and value != ""

def _confidence_ok(value: Any, confidence: Any) -> bool:
    if value is None:
        return False
    if confidence is None:
        return True
    try:
        return float(confidence) >= 0.7
    except (TypeError, ValueError):
        return False

def _goal_confidence(profile: dict) -> float | None:
    conf = profile.get("goal_confidence")
    if conf is None:
        conf = profile.get("project_type_confidence")
    try:
        return float(conf) if conf is not None else None
    except (TypeError, ValueError):
        return None


def _goal_locked(profile: dict) -> bool:
    if profile.get("goal_locked") is True:
        return True
    conf = _goal_confidence(profile)
    if conf is None:
        return False
    return conf >= 0.7


def _sync_project_type_from_goal(profile: dict) -> None:
    if profile.get("project_type"):
        return
    goal = profile.get("goal") or {}
    goal_type = goal.get("type")
    if not goal_type:
        return
    goal_type_str = str(goal_type)
    if goal_type_str in ("buy_something", "live_better", "prepare_future", "protect_family", "experiences", "grow_money", "other"):
        profile["project_type"] = goal_type_str
        profile["project_type_confidence"] = 0.8
        profile["project_type_source"] = "goal_type"


def _sync_goal_from_project_type(profile: dict) -> None:
    _sync_project_type_from_goal(profile)
    if not profile.get("project_type"):
        return
    goal_conf = _goal_confidence(profile)
    pt_conf = profile.get("project_type_confidence")
    try:
        pt_conf_val = float(pt_conf) if pt_conf is not None else None
    except (TypeError, ValueError):
        pt_conf_val = None
    if goal_conf is None:
        profile["goal_confidence"] = pt_conf_val if pt_conf_val is not None else 0.7
    elif pt_conf_val is not None and pt_conf_val > goal_conf:
        profile["goal_confidence"] = pt_conf_val
    if _goal_confidence(profile) is not None and _goal_confidence(profile) >= 0.7:
        profile["goal_locked"] = True


def _update_goal_attempts(profile: dict, turn_index: int) -> None:
    if turn_index < 1:
        return
    _sync_goal_from_project_type(profile)
    if _goal_locked(profile):
        return
    conf = _goal_confidence(profile)
    if conf is None or conf < 0.7:
        attempts = int(profile.get("goal_attempts") or 0)
        profile["goal_attempts"] = min(attempts + 1, 2)

def _liquidity_conf_ok(profile: dict) -> bool:
    raw = profile.get("liquidity_needs")
    if isinstance(raw, dict):
        value = raw.get("value")
        conf = raw.get("confidence")
    else:
        value = raw
        conf = None
    if value in (None, ""):
        return False
    if conf is None:
        return True
    try:
        return float(conf) >= 0.7
    except (TypeError, ValueError):
        return False

def build_steps(profile: dict, state: str, turn_index: int) -> list[dict[str, Any]]:
    goal = profile.get("goal") or {}
    goal_locked = profile.get("goal_locked")
    if goal_locked is None or goal_locked is False:
        goal_locked = _goal_locked(profile)

    project_type = profile.get("project_type")
    project_type_conf = profile.get("project_type_confidence")
    goal_conf = profile.get("goal_confidence")
    goal_category_success = (
        goal_locked
        or (project_type is not None and _confidence_ok(project_type, project_type_conf))
        or (goal_conf is not None and _confidence_ok("goal_confidence", goal_conf))
    )

    opening_status = "in_progress" if turn_index == 0 else "success"
    if turn_index == 0:
        goal_category_status = None
    elif goal_category_success:
        goal_category_status = "success"
    else:
        goal_category_status = "in_progress"

    project_details_success = _has(goal.get("target_amount")) or _has(goal.get("description")) or _has(goal.get("narrative"))
    if project_details_success:
        project_details_status = "success"
    elif goal_category_status == "success":
        project_details_status = "in_progress"
    else:
        project_details_status = None

    horizon_success = profile.get("horizon_months") is not None
    if horizon_success:
        horizon_status = "success"
    elif goal_category_status == "success":
        horizon_status = "in_progress"
    else:
        horizon_status = None

    initial_ok = _confidence_ok(profile.get("initial_amount"), profile.get("initial_amount_confidence"))
    monthly_ok = _confidence_ok(profile.get("monthly_contribution"), profile.get("monthly_contribution_confidence"))
    effort_success = initial_ok or monthly_ok
    if effort_success:
        effort_status = "success"
    elif horizon_status == "success":
        effort_status = "in_progress"
    else:
        effort_status = None

    liquidity_success = _liquidity_conf_ok(profile)
    if liquidity_success:
        liquidity_status = "success"
    elif effort_status == "success":
        liquidity_status = "in_progress"
    else:
        liquidity_status = None

    risk_success = _confidence_ok(profile.get("risk_tolerance_score"), profile.get("risk_tolerance_score_confidence"))
    if risk_success:
        risk_status = "success"
    elif liquidity_status == "success":
        risk_status = "in_progress"
    else:
        risk_status = None

    wrapup_success = state in ("restitution", "restitution_done")
    if wrapup_success:
        wrapup_status = "success"
    elif risk_status == "success":
        wrapup_status = "in_progress"
    else:
        wrapup_status = None

    return [
        {"id": "opening", "label": "Ouverture", "status": opening_status},
        {"id": "goal_category", "label": "Catégorie", "status": goal_category_status},
        {"id": "project_details", "label": "Détails du projet", "status": project_details_status},
        {"id": "horizon", "label": "Horizon", "status": horizon_status},
        {"id": "effort", "label": "Effort", "status": effort_status},
        {"id": "liquidity", "label": "Liquidité", "status": liquidity_status},
        {"id": "risk", "label": "Risque", "status": risk_status},
        {"id": "wrapup", "label": "Restitution", "status": wrapup_status},
    ]

_DONT_KNOW_HORIZON_RE = re.compile(
    r"(je\s+ne\s+sais\s+pas|jsais\s+pas|j'en\s+sais\s+rien|aucune\s+id[ée]e|aide[\s-]*moi|tu\s+choisis|comme\s+tu\s+veux)",
    re.IGNORECASE,
)


def _is_purchase_goal(profile: dict) -> bool:
    goal = profile.get("goal") or {}
    gtype = str(goal.get("type") or "").lower()
    narrative = str(goal.get("narrative") or goal.get("description") or "").lower()
    return gtype in ("apport", "purchase", "achat") or "achat" in narrative or "acheter" in narrative


def _infer_horizon_from_budget(profile: dict) -> None:
    if profile.get("horizon_months") is not None or profile.get("horizon_bucket") is not None:
        return
    goal = profile.get("goal") or {}
    target = goal.get("target_amount") or profile.get("target_amount")
    monthly = profile.get("monthly_contribution")
    if target is None or monthly in (None, 0, "0"):
        return
    try:
        target_val = float(target)
        monthly_val = float(monthly)
    except (TypeError, ValueError):
        return
    initial = profile.get("initial_amount") or 0
    try:
        initial_val = float(initial)
    except (TypeError, ValueError):
        initial_val = 0
    remaining = max(target_val - initial_val, 0)
    if monthly_val <= 0:
        return
    months = int(math.ceil(remaining / monthly_val))
    if months < 1:
        months = 1
    profile["horizon_months"] = months
    if months <= 36:
        profile["horizon_bucket"] = "short"
    elif months <= 84:
        profile["horizon_bucket"] = "medium"
    else:
        profile["horizon_bucket"] = "long"


def _get_recent_question_ids(profile: dict) -> list[str]:
    return list(profile.get("recent_question_ids") or [])


def _record_recent_question_id(profile: dict, question_id: str, limit: int = 6) -> None:
    if not question_id:
        return
    recent = _get_recent_question_ids(profile)
    recent.append(question_id)
    profile["recent_question_ids"] = recent[-limit:]


def _pick_alternative_question(profile: dict, recent: list[str]) -> str | None:
    if profile.get("monthly_contribution") is None and profile.get("initial_amount") is None:
        if "q_budget_single" not in recent:
            return "q_budget_single"
    goal = profile.get("goal") or {}
    if goal.get("target_amount") is None and profile.get("target_amount") is None:
        if "Q_TARGET_AMOUNT" not in recent:
            return "Q_TARGET_AMOUNT"
    if profile.get("risk_tolerance_score") is None and "Q_RISK_CALIB" not in recent:
        return "Q_RISK_CALIB"
    return None

def process_turn(db: Session, session_id: str, message: str, llm_client: object | None = None) -> dict[str, Any]:
    # 0) Resolve session
    sid = uuid.UUID(session_id) if isinstance(session_id, str) else session_id
    sess = db.query(ChatbotSession).filter(ChatbotSession.id == sid).first()
    if not sess:
        raise ValueError("Session not found")

    # Load previous conversation summary (gracefully handle if columns don't exist yet)
    try:
        previous_summary = getattr(sess, 'conversation_summary', None)
        previous_facts = getattr(sess, 'conversation_facts', None) or []
    except (AttributeError, KeyError):
        previous_summary = None
        previous_facts = []

    # 1) Load last profile and turns
    last_profile_row = (
        db.query(ChatbotProfile)
        .filter(ChatbotProfile.session_id == sid)
        .order_by(ChatbotProfile.version.desc())
        .first()
    )
    profile = (last_profile_row.payload or {}) if last_profile_row else {}
    if not isinstance(profile, dict):
        profile = {}
    profile["goal_locked"] = _goal_locked(profile)
    profile.setdefault("goal_attempts", 0)
    profile.setdefault("goal_phase", None)
    asked = list(profile.get("asked_questions") or [])
    next_version = (last_profile_row.version + 1) if last_profile_row else 1

    turns_rows = (
        db.query(ChatbotConversationTurn)
        .filter(ChatbotConversationTurn.session_id == sid)
        .order_by(ChatbotConversationTurn.turn_index.asc())
        .all()
    )
    last_turns = [{"role": r.role, "content": r.content or ""} for r in turns_rows]
    last_turns.append({"role": "user", "content": message})
    turn_index = len(turns_rows) + 1

    # 2) Extractor
    ext = extractor.run_extractor(last_turns, profile, asked, llm=llm_client)
    extracted = ext.get("extracted") or []
    profile, diff = _apply_extracted(profile, extracted)
    _infer_horizon_from_budget(profile)
    _sync_goal_from_project_type(profile)
    profile["goal_locked"] = _goal_locked(profile)
    _update_goal_attempts(profile, turn_index)
    comp = _completeness_60s(profile)
    profile["completeness_score"] = round(comp, 4)
    profile["missing_fields"] = _normalize_str_list(ext.get("missing_fields"))

    # 2.5) Summarizer: update conversation summary
    summary_result = summarizer.run_summarizer(
        previous_summary=previous_summary,
        last_turns=last_turns[-10:],  # Last 10 turns max
        current_profile=profile,
        llm=llm_client,
    )
    conversation_summary = summary_result.get("summary", "") or previous_summary or ""
    new_facts = _normalize_str_list(summary_result.get("facts"))
    prev_facts = _normalize_str_list(previous_facts)
    conversation_facts = _dedupe_facts_preserve(prev_facts + new_facts)

    # 3) Compliance
    comp_out = compliance.run_compliance(
        profile,
        asked_questions=asked,
        conversation_summary=conversation_summary,
        conversation_facts=conversation_facts,
        llm=llm_client,
    )
    missing = _normalize_str_list(comp_out.get("missing_mandatory"))
    contradictions = comp_out.get("contradictions") or []
    disclaimer_ids = _normalize_str_list(comp_out.get("disclaimer_ids_to_show"))
    next_q = comp_out.get("next_suggested_question_id") or "q_goal"
    profile_missing = _normalize_str_list(profile.get("missing_fields"))
    profile["missing_fields"] = _dedupe_preserve(profile_missing + missing)

    # 4) Decide (spec system_orchestrator.md): repair / ask / show_project_summary / show_strategy_summary
    if contradictions:
        flow = "repair"
        next_q = (contradictions[0] or {}).get("repair_id") or comp_out.get("next_suggested_question_id") or "q_goal"
    else:
        dec = decide.run_decide(profile, message, asked, comp, turn_index=turn_index)
        action = dec.get("action") or "ask_next_question"
        next_q = dec.get("next_question_id")
        profile["goal_phase"] = dec.get("goal_phase")
        if action == "show_strategy_summary":
            flow = "restitution"
        elif action == "show_project_summary":
            flow = "show_project_summary"
        elif action == "goal_done":
            flow = "goal_done"
        else:
            flow = "coach"

    if profile.get("goal_phase") is None:
        profile["goal_phase"] = decide.compute_goal_phase(profile, turn_index)

    # Horizon dont_know -> propose options for purchase projects
    horizon_missing = profile.get("horizon_months") is None and profile.get("horizon_bucket") is None
    recent_questions = _get_recent_question_ids(profile)
    last_question = recent_questions[-1] if recent_questions else None
    if horizon_missing and _is_purchase_goal(profile):
        if _DONT_KNOW_HORIZON_RE.search(message or "") and (next_q == "q_horizon" or last_question == "q_horizon"):
            next_q = "q_time_or_budget"
            flow = "coach"

    # Deduplicate question IDs over last 6 turns
    if next_q and next_q in recent_questions and next_q not in (Q_GOAL_FREE, Q_GOAL_CLARIFY, Q_GOAL_FORCE_PICK):
        if next_q == "q_horizon":
            next_q = "q_time_or_budget"
            flow = "coach"
        else:
            alt_q = _pick_alternative_question(profile, recent_questions)
            next_q = alt_q

    # Track budget question attempts and stop after 2 uncertain turns
    if next_q == "q_budget_single" and flow in ("coach", "show_project_summary"):
        attempts = int(profile.get("budget_question_attempts") or 0)
        profile["budget_question_attempts"] = min(attempts + 1, 2)

    def _budget_conf_ok(field: str) -> bool:
        try:
            conf = float(profile.get(f"{field}_confidence"))
        except (TypeError, ValueError):
            conf = None
        if conf is None:
            return profile.get(field) is not None
        return conf >= 0.7

    def _liquidity_conf_ok() -> bool:
        raw = profile.get("liquidity_needs")
        if isinstance(raw, dict):
            value = raw.get("value")
            conf = raw.get("confidence")
        else:
            value = raw
            conf = None
        if value in (None, ""):
            return False
        if conf is None:
            return True
        try:
            return float(conf) >= 0.7
        except (TypeError, ValueError):
            return False

    attempts = int(profile.get("budget_question_attempts") or 0)
    if attempts >= 2:
        for field in ("initial_amount", "monthly_contribution"):
            if not _budget_conf_ok(field):
                profile[field] = None

    if next_q == "Q_LIQUIDITY" and flow in ("coach", "show_project_summary"):
        l_attempts = int(profile.get("liquidity_question_attempts") or 0)
        profile["liquidity_question_attempts"] = min(l_attempts + 1, 2)

    l_attempts = int(profile.get("liquidity_question_attempts") or 0)
    if l_attempts >= 2 and not _liquidity_conf_ok():
        profile["liquidity_needs"] = {"value": None, "confidence": 0.4}

    if next_q == Q_GOAL_FORCE_PICK and flow in ("coach", "show_project_summary"):
        profile["goal_phase"] = "goal_force_pick"

    # 5) Build reply
    reply = ""
    disclaimers_shown: list[str] = []
    proposal_preview: dict | None = None
    prompt_parts: list[str] = [load_prompt("extractor"), load_prompt("compliance")]

    if flow == "restitution":
        # Portfolio (déterministe) + Copywriter strategy_intro (prompt 6). Détails allocation dans proposal_preview.
        profile["completeness_score"] = comp  # ensure up-to-date
        prop = portfolio.run_portfolio(profile)
        alloc = prop.get("allocation") or []
        copyw = copywriter.run_copywriter(
            alloc,
            prop.get("rationale"),
            profile,
            "strategy_intro",
            disclaimer_ids,
            conversation_summary=conversation_summary,
            conversation_facts=conversation_facts,
            llm=llm_client,
        )
        reply = (copyw.get("summary_text") or "") + "\n\n" + (copyw.get("disclaimer_block") or "")
        prop_disclaimers = _normalize_str_list(prop.get("disclaimers") or [])
        disclaimers_shown = _dedupe_preserve(disclaimer_ids + prop_disclaimers)
        proposal_preview = {"allocation": alloc, "rationale": prop.get("rationale"), "disclaimers": disclaimers_shown}
        prompt_parts.extend([load_prompt("copywriter")])
    else:
        if flow == "show_project_summary":
            # Résumé Projet (prompt 5) + une question (get_question_text)
            reply = copywriter.run_copywriter_project_summary(
                profile,
                conversation_summary=conversation_summary,
                conversation_facts=conversation_facts,
            ) + "\n\n" + (
                coach.get_question_text(next_q) if next_q else "Souhaitez-vous préciser un dernier point ?"
            )
            prompt_parts.append(load_prompt("coach"))
        elif flow == "goal_done":
            reply = copywriter.run_copywriter_project_summary(
                profile,
                conversation_summary=conversation_summary,
                conversation_facts=conversation_facts,
            )
            prompt_parts.append(load_prompt("coach"))
        else:
            coach_msg = coach.run_coach(
                message,
                profile,
                missing,
                flow,
                next_q,
                conversation_summary=conversation_summary,
                conversation_facts=conversation_facts,
                llm=llm_client,
            )
            reply = coach_msg
            prompt_parts.append(load_prompt("coach"))
        if flow in ("coach", "show_project_summary") and next_q and next_q not in asked:
            asked.append(next_q)
        _record_recent_question_id(profile, next_q)

    # 6) RiskGuardian
    rg = risk_guardian.run_risk_guardian(message, reply, profile, None, llm=llm_client)
    prompt_parts.append(load_prompt("risk_guardian"))
    if not rg.get("allowed", True):
        reply = rg.get("replacement_message") or "Je ne peux pas répondre à cette demande. Souhaitez-vous reformuler ?"

    # 7) asked_questions
    profile["asked_questions"] = asked

    # 8) Persist: user turn
    user_turn = ChatbotConversationTurn(
        session_id=sid,
        turn_index=turn_index - 1,
        role="user",
        content=message,
        extracted_json=ext,
    )
    db.add(user_turn)
    db.flush()

    # 9) New profile if diff, first time, or completeness changed
    profile_snapshot_id = None
    prev_comp = float(last_profile_row.completeness_score or 0) if last_profile_row else -1
    if last_profile_row is None or diff or (comp != prev_comp):
        cp = ChatbotProfile(
            session_id=sid,
            version=next_version,
            payload=profile,
            completeness_score=comp,
            missing_fields=profile.get("missing_fields") or [],
        )
        db.add(cp)
        db.flush()
        profile_snapshot_id = cp.id
        ev = ChatbotAuditEvent(
            session_id=sid,
            event_type="ProfileUpdated",
            payload={"diff": diff, "source_turn_id": str(user_turn.id), "prompt_version_hash": _prompt_hash(prompt_parts)},
        )
        db.add(ev)

    # 10) Assistant turn
    asst_turn = ChatbotConversationTurn(
        session_id=sid,
        turn_index=turn_index,
        role="assistant",
        content=reply,
        profile_snapshot_id=profile_snapshot_id,
    )
    db.add(asst_turn)
    db.flush()

    # 11) DisclaimerShown
    for d in disclaimers_shown:
        db.add(ChatbotAuditEvent(session_id=sid, event_type="DisclaimerShown", payload={"disclaimer_id": d}))

    # 12) Proposal + ProposalGenerated if restitution
    if flow == "restitution" and profile_snapshot_id and proposal_preview:
        prof_row = db.query(ChatbotProfile).filter(ChatbotProfile.id == profile_snapshot_id).first()
        if prof_row:
            pp = ChatbotPortfolioProposal(
                profile_id=profile_snapshot_id,
                allocation=proposal_preview.get("allocation") or [],
                rationale=proposal_preview.get("rationale"),
                disclaimers=proposal_preview.get("disclaimers") or [],
            )
            db.add(pp)
            db.add(ChatbotAuditEvent(session_id=sid, event_type="ProposalGenerated", payload={"profile_id": str(profile_snapshot_id)}))

    # 13) Persist conversation summary and facts (gracefully handle if columns don't exist yet)
    try:
        if hasattr(sess, 'conversation_summary'):
            sess.conversation_summary = conversation_summary
        if hasattr(sess, 'conversation_facts'):
            sess.conversation_facts = conversation_facts
        if hasattr(sess, 'last_next_question_id'):
            sess.last_next_question_id = next_q
        db.flush()
    except AttributeError:
        # Columns don't exist yet - migration not applied, skip persistence
        pass

    db.commit()

    # Carte Résumé Projet (live update) pour l'UI — sauf en restitution où proposal_preview porte l'allocation
    project_summary = None if flow == "restitution" else copywriter.run_copywriter_project_summary(
        profile,
        conversation_summary=conversation_summary,
        conversation_facts=conversation_facts,
    )

    result = {
        "reply": reply,
        "profile_diff": diff if diff else None,
        "state": flow,
        "disclaimers_shown": disclaimers_shown,
        "proposal_preview": proposal_preview,
        "completeness_score": round(comp, 4),
        "project_summary": project_summary,
        "conversation_summary": conversation_summary,
        "conversation_facts": conversation_facts,
        "profile": profile,
        "next_question_id": next_q,
        "goal_phase": profile.get("goal_phase"),
        "goal_locked": profile.get("goal_locked"),
        "goal_confidence": profile.get("goal_confidence"),
        "goal_attempts": profile.get("goal_attempts"),
    }

    # Debug info (only if DEBUG_CHATBOT env var is set)
    import os
    if os.getenv("DEBUG_CHATBOT", "").lower() in ("true", "1", "yes"):
        result["debug"] = {
            "state": flow,
            "next_question_id": next_q,
            "completeness_score": round(comp, 4),
            "missing_fields": profile.get("missing_fields") or [],
            "asked_questions": asked,
            "disclaimers_shown": disclaimers_shown,
            "profile_diff": diff if diff else {},
            "profile": profile,
            "conversation_summary": conversation_summary,
            "conversation_facts": conversation_facts,
            "steps": build_steps(profile, flow, turn_index),
            "goal_phase": profile.get("goal_phase"),
            "goal_locked": profile.get("goal_locked"),
            "goal_confidence": profile.get("goal_confidence"),
            "goal_attempts": profile.get("goal_attempts"),
            "turn_index": turn_index,
            "goal_next_question_id": next_q,
        }

    return result
