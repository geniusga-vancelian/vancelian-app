#!/usr/bin/env python3
"""
Crée ou met à jour la présentation `registration-risk-compliance` (brouillon courant)
avec un jeu de slides aligné sur les templates API (texte de synthèse).

Usage (depuis services/arquantix/api) :
  python3 scripts/upsert_registration_risk_deck.py

Le deck visuel riche (schémas, templates DS avancés) vit dans presentation-design-system :
  /deck/registration-risk-compliance
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_DIR))
os.chdir(API_DIR)

from dotenv import load_dotenv

load_dotenv(API_DIR / ".env.local")
load_dotenv(API_DIR / ".env")

from services.portfolio_engine.clients.models import Client as _Client  # noqa: F401 — init ORM Person↔Client
import services.presentations.models as _presentation_models  # noqa: F401

from database import SessionLocal  # noqa: E402
from services.presentations.models import (  # noqa: E402
    PresentationDeck,
    PresentationSlideTemplate,
)
from services.presentations.schemas import (  # noqa: E402
    PresentationDeckCreate,
    PresentationVersionCreate,
    SaveDraftBody,
    SaveDraftSlidePayload,
)
from services.presentations import service as pres  # noqa: E402


SLUG = "registration-risk-compliance"


def _tid(db, key: str):
    t = db.query(PresentationSlideTemplate).filter(PresentationSlideTemplate.key == key).first()
    if not t:
        raise SystemExit(f"Template manquant en base : {key} (alembic 095 appliqué ?)")
    return t.id


def main() -> None:
    db = SessionLocal()
    try:
        deck = db.query(PresentationDeck).filter(PresentationDeck.slug == SLUG).first()
        if not deck:
            deck = pres.create_deck(
                db,
                PresentationDeckCreate(
                    name="Registration × risques LCB-FT",
                    slug=SLUG,
                    description="Alignement parcours client et cartographie risques (Excel + PDF).",
                    deck_type="compliance",
                    create_initial_version=True,
                ),
            )
            db.refresh(deck)
            print("Deck créé :", deck.id)
        else:
            print("Deck existant :", deck.id)

        if not deck.current_version_id:
            print("Pas de version courante — création d’une version initiale.")
            nv = pres.create_version(db, deck.id, PresentationVersionCreate())
            pres.set_current_version(db, nv.id)
            db.refresh(deck)

        vid = deck.current_version_id
        assert vid

        t_title = _tid(db, "title")
        t_sec = _tid(db, "section-divider")
        t_2c = _tid(db, "two-column")
        t_met = _tid(db, "metrics")
        t_quote = _tid(db, "quote")
        t_close = _tid(db, "closing")

        slides: list[SaveDraftSlidePayload] = [
            SaveDraftSlidePayload(
                slide_template_id=t_title,
                sort_order=0,
                content_json={
                    "title": "Registration et cartographie LCB-FT",
                    "subtitle": "Vancelian — alignement parcours client & référentiel risques groupe (nov. 2025).",
                    "badge": "",
                },
            ),
            SaveDraftSlidePayload(
                slide_template_id=t_sec,
                sort_order=1,
                content_json={
                    "sectionTitle": "Deux lectures complémentaires",
                    "kicker": "PDF registration (5 blocs) · Grille Excel critères & scores",
                },
            ),
            SaveDraftSlidePayload(
                slide_template_id=t_2c,
                sort_order=2,
                slide_title="Complémentarité sources",
                content_json={
                    "leftTitle": "Vue parcours",
                    "leftBody": "Identification, coordonnées, résidence, profil financier, profil investisseur : ce qui est demandé et pourquoi.",
                    "rightCaption": "Vue LCB-FT : critères PP/PM, gravité, points, risk score, décisions (standard / EDD / refus).",
                },
            ),
            SaveDraftSlidePayload(
                slide_template_id=t_met,
                sort_order=3,
                slide_title="Seuils agrégés",
                content_json={
                    "metrics": [
                        {"label": "Faible", "value": "0–499"},
                        {"label": "Modéré", "value": "500–799"},
                        {"label": "Élevé", "value": "800–1799"},
                        {"label": "Refus", "value": "≥1800"},
                    ]
                },
            ),
            SaveDraftSlidePayload(
                slide_template_id=t_met,
                sort_order=4,
                slide_title="Gravité par critère",
                content_json={
                    "metrics": [
                        {"label": "Faible", "value": "0 pt"},
                        {"label": "Modéré", "value": "100"},
                        {"label": "Élevé", "value": "200"},
                        {"label": "Très élevé", "value": "800"},
                    ]
                },
            ),
            SaveDraftSlidePayload(
                slide_template_id=t_2c,
                sort_order=5,
                slide_title="Axe client PP (extraits)",
                content_json={
                    "leftTitle": "Identité & listes",
                    "leftBody": "VPN, IP, pièces, virement d’activation, pays GAFI/UE, PPE, médias défavorables, TRACFIN.",
                    "rightCaption": "Économie : profession, secteur, revenus, patrimoine, source des fonds — alimentent le score.",
                },
            ),
            SaveDraftSlidePayload(
                slide_template_id=t_quote,
                sort_order=6,
                content_json={
                    "quote": "PSAN enregistré AMF : obligations LCB-FT du cadre français et européen (LCB-FT, connaissance client).",
                    "author": "Synthèse référentiel",
                    "role": "Introduction classification risques",
                },
            ),
            SaveDraftSlidePayload(
                slide_template_id=t_close,
                sort_order=7,
                content_json={
                    "headline": "Suite : atelier Compliance × Produit",
                    "cta": "Voir deck visuel DS : /deck/registration-risk-compliance",
                },
            ),
        ]

        pres.save_draft(db, vid, SaveDraftBody(slides=slides))
        print("Brouillon enregistré sur version", vid, "—", len(slides), "slides.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
