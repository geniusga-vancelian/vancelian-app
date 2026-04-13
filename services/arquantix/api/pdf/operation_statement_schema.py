"""
Schéma canonique du document « relevé d'opération » (PDF unifié).

Indépendant de ``IbanStatementPayload`` : le rendu custody PR3+ consomme uniquement ce contrat.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


class OperationRefPayload(BaseModel):
    source_system: Literal["custody", "exchange"]
    source_id: str = Field(..., description="UUID de l'entité source")


class OperationStatementPdfLine(BaseModel):
    """Une ligne du tableau « Opérations » (custody : typiquement une seule ligne)."""

    booking_date: date
    description: str
    amount_in: Optional[Decimal] = None
    amount_out: Optional[Decimal] = None
    balance_after: Decimal


class OperationStatementBalanceContext(BaseModel):
    """
    Contexte de soldes « compte » : pertinent pour custody cash uniquement en V1.

    Pour Exchange : ``applicable=False`` — pas de solde bancaire sur le relevé.
    """

    applicable: bool = False


class OperationStatementAssetImpact(BaseModel):
    """Flux entrant/sortant sur un actif ou une devise (cœur du relevé Exchange)."""

    flow: Literal["in", "out"]
    asset: str
    amount: Decimal
    unit_kind: Literal["fiat", "crypto"] = "fiat"


class OperationStatementFeeItem(BaseModel):
    amount: Decimal
    asset: str


class OperationStatementReferences(BaseModel):
    order_id: Optional[str] = None
    external_reference: Optional[str] = None


class OperationStatementDetailRow(BaseModel):
    """Ligne libellé / valeur (carte « exécution », méta hors IBAN)."""

    label: str
    value: str


class OperationStatementPersonBlock(BaseModel):
    """Titulaire + adresse pour l’en-tête (custody via ``custody_pdf`` ; exchange via ce bloc)."""

    full_name: str
    address_line_1: str
    postal_code: str
    city: str
    country: str


class OperationStatementCustodyPdfSection(BaseModel):
    """
    Données nécessaires au gabarit PDF custody (soldes + identifiants compte).

    Pour le cash custody on expose toujours ce bloc lorsque le PDF est émis.
    """

    statement_title: str = "Relevé d'opération"
    document_title: str = "Relevé d'opération — Vancelian"
    period_heading: str
    hide_balance_summary: bool = False

    client_full_name: str
    address_line_1: str
    postal_code: str
    city: str
    country: str

    account_currency: str
    iban: str
    bic: str
    account_number: str

    opening_balance: Decimal
    closing_balance: Decimal
    money_in: Optional[Decimal] = None
    money_out: Optional[Decimal] = None

    lines: list[OperationStatementPdfLine] = Field(default_factory=list)


class OperationStatementPayload(BaseModel):
    """
    Charge utile canonique pour le pipeline ``operation_statement_*``.

    ``custody_pdf`` est rempli pour les relevés custody ; d'autres sections (exchange PR4)
    pourront s'ajouter sans réutiliser le modèle IBAN.
    """

    operation_ref: OperationRefPayload
    operation_type: str = Field(
        ...,
        description="Taxonomie V1 : deposit | withdrawal | transfer_internal | exchange_buy | exchange_sell",
    )
    status: str
    title: str
    subtitle: Optional[str] = None

    amount: Decimal
    currency: str
    direction: Literal["credit", "debit"]

    booking_date: Optional[date] = None
    generated_at: datetime = Field(..., description="Horodatage de génération du document (UTC)")

    custody_pdf: Optional[OperationStatementCustodyPdfSection] = Field(
        default=None,
        description="Projection rendu custody (compte IBAN + lignes type relevé bancaire).",
    )

    balance_context: Optional[OperationStatementBalanceContext] = Field(
        default=None,
        description="Méta soldes : Exchange → applicable=false ; custody délégué à custody_pdf pour l’instant.",
    )

    person: Optional[OperationStatementPersonBlock] = Field(
        default=None,
        description="Titulaire pour cartes en-tête lorsque custody_pdf est absent (Exchange).",
    )

    execution_detail_rows: list[OperationStatementDetailRow] = Field(
        default_factory=list,
        description="Détails d’exécution (prix, paire, sens) — hors logique IBAN.",
    )

    asset_impacts: list[OperationStatementAssetImpact] = Field(
        default_factory=list,
        description="Flux multi-jambes (Exchange) ; structure centrale du document.",
    )

    fees: list[OperationStatementFeeItem] = Field(default_factory=list)

    references: Optional[OperationStatementReferences] = None

    # Champs réservés PR5 (snapshot / régénération) — optionnels en V1 schéma
    metadata_snapshot: Optional[dict] = Field(
        default=None,
        description="PR5 : copie minimale figée des faits affichés (voir addendum V1)",
    )
