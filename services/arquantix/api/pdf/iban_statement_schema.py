"""
Contrat de données JSON pour le relevé IBAN (nourriture Jinja2 / PDF).

Aligné sur la grammaire Flutter (IbanStatementDocument) et extensible (totaux, méta).
Les montants sont des Decimal en entrée ; le mapper produit les chaînes d’affichage fr_FR.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class IbanStatementPeriod(BaseModel):
    date_from: date = Field(..., description="Début de période (inclus)")
    date_to: date = Field(..., description="Fin de période (inclus)")


class IbanStatementClient(BaseModel):
    full_name: str
    address_line_1: str
    postal_code: str
    city: str
    country: str


class IbanStatementAccount(BaseModel):
    """Compte affiché sur le relevé (nom libre + identifiants)."""

    account_name: Optional[str] = Field(None, description="Libellé du compte (ex. Euro)")
    currency: str = Field(..., min_length=3, max_length=3)
    iban: str
    bic: str
    account_number: str


class IbanStatementSummary(BaseModel):
    opening_balance: Decimal
    closing_balance: Decimal
    money_in: Optional[Decimal] = Field(None, description="Total crédits sur la période (optionnel)")
    money_out: Optional[Decimal] = Field(None, description="Total débits sur la période (optionnel)")


class IbanStatementTransaction(BaseModel):
    booking_date: date
    description: str
    amount_out: Optional[Decimal] = None
    amount_in: Optional[Decimal] = None
    balance_after: Decimal


class IbanStatementPayload(BaseModel):
    """
    Charge utile « API / base » avant rendu template.
    Exemple JSON : voir docstring de `iban_statement_mapper.payload_to_template_context`.
    """

    statement_title: str = Field(
        default="Relevé de compte bancaire",
        description="Titre principal sous le logo (équivalent Flutter titre)",
    )
    generated_at: datetime = Field(..., description="Horodatage génération (UTC conseillé)")
    period: IbanStatementPeriod
    client: IbanStatementClient
    account: IbanStatementAccount
    summary: IbanStatementSummary
    transactions: list[IbanStatementTransaction] = Field(default_factory=list)

    support_phone: str = Field(default="+33 1 23 45 67 89")
    document_title: Optional[str] = Field(
        None,
        description="Balise <title> du HTML ; défaut dérivé du titre du relevé",
    )
    period_heading_override: Optional[str] = Field(
        None,
        description="Si défini, remplace le libellé de période (relevé multi-opérations)",
    )
    hide_balance_summary: bool = Field(
        default=False,
        description="Masque le bloc « Soldes du compte » (relevé minimal)",
    )
