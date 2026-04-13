"""
Demo catalog for exclusive offers (V1).
"""
from typing import List, Dict, Any


EXCLUSIVE_OFFERS: List[Dict[str, Any]] = [
    {
        "project_id": "PROJ-DXB-VILLA-001",
        "title": "Villa Dubai - Construction",
        "location": "Dubai, UAE",
        "duration_months": 24,
        "target_apr_range": "12-16%",
        "min_ticket": 50000,
        "summary": "Développement d'une villa premium avec sortie à 24 mois.",
        "risk_notes": "Risque de construction et d'exécution; dépendance au marché local.",
        "docs_link": "https://example.com/docs/villa-dubai",
    },
    {
        "project_id": "PROJ-BALI-7V-002",
        "title": "Bali - Promotion 7 villas",
        "location": "Bali, Indonesia",
        "duration_months": 30,
        "target_apr_range": "14-18%",
        "min_ticket": 35000,
        "summary": "Promotion de 7 villas haut de gamme avec stratégie de vente progressive.",
        "risk_notes": "Risque de commercialisation et volatilité touristique.",
        "docs_link": "https://example.com/docs/bali-7-villas",
    },
    {
        "project_id": "PROJ-PAR-RENO-003",
        "title": "Paris - Rénovation immeuble",
        "location": "Paris, France",
        "duration_months": 18,
        "target_apr_range": "8-12%",
        "min_ticket": 40000,
        "summary": "Rénovation et repositionnement d'un immeuble résidentiel.",
        "risk_notes": "Risque de coûts de rénovation et délais administratifs.",
        "docs_link": "https://example.com/docs/paris-reno",
    },
]


def list_offers() -> List[Dict[str, Any]]:
    return EXCLUSIVE_OFFERS
