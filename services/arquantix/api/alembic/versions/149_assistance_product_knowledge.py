"""Phase 2c multi-agents — table `product_knowledge` + seed initial.

Crée la base de connaissances **factuelle** consultée par l'agent
`product` (vrai agent Phase 2c) pour répondre à des questions structurées
de type *« combien de temps prend un dépôt SEPA ? »*, *« quel délai pour
un retrait ? »*, *« combien de temps pour la review KYC ? »*.

──────────────────────────────────────────────────────────────────────
Pourquoi cette table

L'agent `product` (Phase 2c) est appelé soit directement par le router,
soit via `consult_specialist(target=product, purpose=...)` depuis un
sub-agent compliance qui veut composer une réponse riche.

Son tool L0 `read_product_knowledge(slug)` lit cette table pour ramener
un texte canonique, vérifié, court (200-500 mots) — bien plus
fiable qu'une hallucination LLM sur des délais réglementaires.

Phase 5 (RAG) viendra remplacer le seed manuel par une ingestion
vectorielle des fiches produit officielles depuis le CMS.

──────────────────────────────────────────────────────────────────────
Colonnes

  - `slug`        : VARCHAR(80) PK — clé canonique (ex. "deposit_delay_sepa_in")
  - `topic`       : VARCHAR(40) — catégorie (delay, definition, comparison, ...)
  - `title`       : VARCHAR(200) — libellé humain
  - `body`        : TEXT — markdown court (200-500 mots)
  - `metadata`    : JSONB — {applies_to, source, valid_until, ...}
  - `is_active`   : BOOLEAN — soft-delete pour retirer un slug obsolète
                    sans perdre l'historique d'audit
  - `updated_at`  : TIMESTAMPTZ

Pas de `created_by` ni `id` UUID : le slug suffit comme PK et la
sémantique est versionnée par mise à jour `body` + `updated_at`.

──────────────────────────────────────────────────────────────────────
Index

  - `topic`                     — listing par catégorie (rare)
  - `is_active` (partial)       — la majorité des reads filtrent active

──────────────────────────────────────────────────────────────────────
Seed

10 entrées initiales couvrant les 5 `purpose` whitelistés dans
`consult_purposes.py` :

  - explain_deposit_delay        (3 slugs : sepa_in, card, crypto_in)
  - explain_withdrawal_delay     (2 slugs : sepa_out, crypto_out)
  - explain_kyc_review_delay     (1 slug)
  - explain_swap_settlement      (1 slug)
  - explain_product_basics       (3 slugs : livret, scpi, vault)

Migration purement additive. Aucune autre table touchée.

Revision ID: 149
Revises: 148
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "149"
down_revision = "148"
branch_labels = None
depends_on = None


# ─────────────────────────────────────────────────────────────────────
# Seed initial — 10 entrées couvrant les 5 purposes whitelistés.
# Reste volontairement court et factuel : les délais sont des
# fourchettes prudentes (haut de fourchette communiquée). Le RAG
# (Phase 5) remplacera ce seed par des contenus ingérés depuis le CMS.
# ─────────────────────────────────────────────────────────────────────

_SEED_ROWS: list[dict] = [
    # ── Délais de dépôt ───────────────────────────────────────────
    {
        "slug": "deposit_delay_sepa_in",
        "topic": "delay",
        "title": "Délai d'un dépôt par virement SEPA",
        "body": (
            "Un dépôt par virement SEPA arrive **généralement en 1 à 2 "
            "jours ouvrés** sur ton compte Vancelian, et jusqu'à **3 "
            "jours ouvrés** selon la banque émettrice et l'heure du "
            "virement.\n\n"
            "Repères utiles :\n\n"
            "- Virement émis avant **midi un jour ouvré** : crédit "
            "souvent le lendemain ouvré.\n"
            "- Virement émis le **vendredi après-midi ou un week-end** : "
            "comptabilisé le lundi suivant.\n"
            "- **Jours fériés** (France ou pays émetteur) : rajoute un "
            "jour ouvré au délai.\n\n"
            "Le délai peut être plus long si la banque émettrice "
            "demande une vérification anti-fraude (rare). Tant que la "
            "transaction n'apparaît pas dans la liste de tes "
            "transactions Vancelian, c'est qu'elle est encore en "
            "cours côté banque émettrice."
        ),
        "metadata": {
            "applies_to": "FR/EU",
            "currency": "EUR",
            "source": "internal_doc_v1",
        },
    },
    {
        "slug": "deposit_delay_card",
        "topic": "delay",
        "title": "Délai d'un dépôt par carte bancaire",
        "body": (
            "Un dépôt par carte bancaire est **immédiat** dans la "
            "très grande majorité des cas : ton solde est crédité dès "
            "que la transaction est validée par ta banque (quelques "
            "secondes).\n\n"
            "Cas où le crédit peut prendre **jusqu'à 24 h** :\n\n"
            "- Vérification anti-fraude automatique côté ta banque ou "
            "côté Vancelian.\n"
            "- Première utilisation d'une carte sur ton compte "
            "Vancelian (contrôle 3DS).\n"
            "- Dépôt important après une période d'inactivité.\n\n"
            "Si après 24 h la transaction n'apparaît toujours pas, "
            "vérifie d'abord que ta banque ne l'a pas refusée "
            "(notification de paiement, SMS) puis contacte le support."
        ),
        "metadata": {
            "applies_to": "FR/EU",
            "currency": "EUR",
            "source": "internal_doc_v1",
        },
    },
    {
        "slug": "deposit_delay_crypto_in",
        "topic": "delay",
        "title": "Délai d'un dépôt en crypto-actifs",
        "body": (
            "Un dépôt en crypto-actifs (BTC, ETH, USDC, etc.) est "
            "crédité **après confirmation sur la blockchain**.\n\n"
            "Repères usuels :\n\n"
            "- **Bitcoin (BTC)** : ~10-60 minutes (1 à 6 confirmations "
            "selon le montant).\n"
            "- **Ethereum (ETH) / ERC-20** : ~5-15 minutes (12 à 30 "
            "confirmations).\n"
            "- **USDC sur réseau rapide** (Solana, Polygon) : quelques "
            "minutes.\n\n"
            "Le délai dépend de la **congestion du réseau** au moment "
            "du transfert. Si la transaction est visible sur le "
            "blockchain explorer mais pas sur ton compte Vancelian "
            "après 2 h, contacte le support en fournissant le hash de "
            "transaction."
        ),
        "metadata": {
            "applies_to": "global",
            "source": "internal_doc_v1",
        },
    },
    # ── Délais de retrait ─────────────────────────────────────────
    {
        "slug": "withdrawal_delay_sepa_out",
        "topic": "delay",
        "title": "Délai d'un retrait par virement SEPA",
        "body": (
            "Un retrait depuis ton compte Vancelian vers ton compte "
            "bancaire **personnel vérifié** prend généralement **1 à "
            "2 jours ouvrés**.\n\n"
            "Étapes :\n\n"
            "1. Ta demande est validée immédiatement côté Vancelian.\n"
            "2. Le virement SEPA est émis le **prochain jour ouvré** "
            "(cut-off banking : ~14h en semaine).\n"
            "3. Ta banque destinataire crédite ton compte sous **1 "
            "jour ouvré** après réception.\n\n"
            "Pour un premier retrait, un contrôle anti-fraude "
            "supplémentaire peut ajouter 24 h. Les retraits ne "
            "transitent **jamais** par un compte tiers : seul un IBAN "
            "à ton nom et préalablement vérifié est accepté."
        ),
        "metadata": {
            "applies_to": "FR/EU",
            "currency": "EUR",
            "source": "internal_doc_v1",
        },
    },
    {
        "slug": "withdrawal_delay_crypto_out",
        "topic": "delay",
        "title": "Délai d'un retrait en crypto-actifs",
        "body": (
            "Un retrait en crypto-actifs vers une adresse externe "
            "(self-custody ou autre exchange) est traité **dans "
            "l'heure** suivant ta demande, après les contrôles de "
            "sécurité standards.\n\n"
            "Étapes :\n\n"
            "1. Validation 2FA + confirmation de l'adresse (anti-typo).\n"
            "2. Mise en file d'attente dans le batch de la blockchain "
            "concernée.\n"
            "3. Diffusion sur le réseau + confirmations selon la "
            "blockchain (BTC : ~30 min, ETH : ~5 min).\n\n"
            "Le retrait peut prendre **jusqu'à 24 h** si une "
            "vérification supplémentaire est déclenchée (montant "
            "inhabituel, première utilisation d'une nouvelle adresse). "
            "Une fois la transaction broadcast, son délai dépend "
            "uniquement du réseau."
        ),
        "metadata": {
            "applies_to": "global",
            "source": "internal_doc_v1",
        },
    },
    # ── Délai review KYC ──────────────────────────────────────────
    {
        "slug": "kyc_review_typical_delay",
        "topic": "delay",
        "title": "Délai de validation d'un dossier KYC ou d'un justificatif",
        "body": (
            "La validation d'un nouveau dossier KYC ou d'un "
            "justificatif complémentaire prend **24 à 72 heures "
            "ouvrées** dans la grande majorité des cas.\n\n"
            "Repères :\n\n"
            "- **Justificatif simple** (pièce d'identité claire, "
            "justificatif de domicile récent) : souvent validé en "
            "**moins de 24 h**.\n"
            "- **Dossier complet** (premier KYC, multiples documents) : "
            "**24-72 h**.\n"
            "- **Cas nécessitant un complément** (qualité d'image "
            "insuffisante, document expiré) : tu reçois une notification "
            "avec ce qui manque.\n\n"
            "Tu peux suivre l'état de ton dossier dans **Profil → Mes "
            "informations**. Les week-ends et jours fériés ne sont pas "
            "comptés dans le délai."
        ),
        "metadata": {
            "applies_to": "global",
            "source": "internal_doc_v1",
        },
    },
    # ── Délai swap / settlement ───────────────────────────────────
    {
        "slug": "swap_settlement_immediate",
        "topic": "delay",
        "title": "Délai d'un échange (swap) entre actifs",
        "body": (
            "Un échange (swap) entre deux actifs sur Vancelian — par "
            "exemple **EUR → BTC** ou **USDC → ETH** — est "
            "**immédiat** dès que tu confirmes l'opération.\n\n"
            "- Le taux affiché à la confirmation est **garanti** "
            "(quote ferme, valable quelques secondes).\n"
            "- Les actifs sont crédités sur ton compte dans la **même "
            "seconde** que le débit de l'actif source.\n"
            "- Aucune confirmation blockchain n'est requise (les actifs "
            "sont en custody Vancelian, pas sur l'on-chain).\n\n"
            "Si tu veux ensuite **retirer** les actifs reçus vers une "
            "adresse externe ou un compte bancaire, le délai standard "
            "du retrait s'applique (cf. *Délai d'un retrait*)."
        ),
        "metadata": {
            "applies_to": "global",
            "source": "internal_doc_v1",
        },
    },
    # ── Bases produit (3 slugs) ───────────────────────────────────
    {
        "slug": "product_basics_vault",
        "topic": "definition",
        "title": "Le coffre Vancelian (vault)",
        "body": (
            "Le **coffre Vancelian** est ton espace de **conservation "
            "sécurisée** d'actifs numériques. Il fonctionne comme un "
            "compte de dépôt : tes actifs y restent à ta disposition, "
            "tu peux à tout moment retirer ou échanger.\n\n"
            "Caractéristiques principales :\n\n"
            "- **Conservation institutionnelle** : tes actifs sont "
            "détenus chez un dépositaire régulé.\n"
            "- **Multi-actifs** : EUR, BTC, ETH, USDC et autres "
            "selon les actifs disponibles.\n"
            "- **Pas de frais de garde** sur la version standard.\n"
            "- **Frais de transaction** appliqués sur les achats / "
            "ventes / swaps (visibles avant confirmation).\n\n"
            "Tu peux consulter le détail du coffre dans **Portefeuille "
            "→ Mon coffre**."
        ),
        "metadata": {
            "applies_to": "FR/EU",
            "source": "internal_doc_v1",
        },
    },
    {
        "slug": "product_basics_scpi",
        "topic": "definition",
        "title": "Investir en SCPI sur Vancelian",
        "body": (
            "Une **SCPI** (Société Civile de Placement Immobilier) "
            "est un produit d'**investissement immobilier indirect** : "
            "tu achètes des parts d'une société qui détient un parc "
            "immobilier locatif diversifié.\n\n"
            "Caractéristiques :\n\n"
            "- **Rendement potentiel** versé sous forme de **loyers "
            "trimestriels** (pas garanti — dépend de la performance "
            "locative).\n"
            "- **Horizon long terme recommandé** : 8 ans minimum pour "
            "amortir les frais d'entrée.\n"
            "- **Liquidité limitée** : la revente des parts dépend "
            "du marché secondaire ; pas de revente immédiate garantie.\n"
            "- **Fiscalité** : revenus fonciers + imposition selon ton "
            "régime.\n\n"
            "Le risque de **perte en capital** existe : la valeur des "
            "parts peut baisser. Vérifie toujours le DICI et les "
            "conditions spécifiques de chaque SCPI avant souscription."
        ),
        "metadata": {
            "applies_to": "FR",
            "horizon_min_years": 8,
            "source": "internal_doc_v1",
        },
    },
    {
        "slug": "product_basics_livret_vancelian",
        "topic": "definition",
        "title": "Le compte d'épargne rémunéré Vancelian",
        "body": (
            "Le **compte d'épargne rémunéré Vancelian** te permet "
            "de placer ton solde en euros à un **taux d'intérêt** "
            "communiqué à l'avance.\n\n"
            "Caractéristiques :\n\n"
            "- **Disponibilité** : tu peux retirer ou redéposer à "
            "tout moment, sans pénalité.\n"
            "- **Rémunération** : intérêts calculés au prorata du "
            "temps de détention, versés mensuellement.\n"
            "- **Plafond de dépôt** précisé à l'ouverture.\n"
            "- **Sécurité** : protection des dépôts dans la limite "
            "réglementaire applicable.\n\n"
            "Le taux et les conditions sont susceptibles d'évoluer. "
            "Le détail à jour est disponible dans la fiche produit "
            "depuis l'app."
        ),
        "metadata": {
            "applies_to": "FR/EU",
            "source": "internal_doc_v1",
        },
    },
]


def upgrade() -> None:
    op.create_table(
        "product_knowledge",
        sa.Column("slug", sa.String(length=80), primary_key=True, nullable=False),
        sa.Column("topic", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="public",
    )

    op.create_index(
        "ix_product_knowledge_topic",
        "product_knowledge",
        ["topic"],
        schema="public",
    )
    op.create_index(
        "ix_product_knowledge_active",
        "product_knowledge",
        ["is_active"],
        schema="public",
        postgresql_where=sa.text("is_active = true"),
    )

    bind = op.get_bind()
    insert_stmt = sa.text(
        """
        INSERT INTO public.product_knowledge
          (slug, topic, title, body, metadata_json)
        VALUES
          (:slug, :topic, :title, :body, CAST(:metadata_json AS jsonb))
        ON CONFLICT (slug) DO NOTHING
        """
    )
    for r in _SEED_ROWS:
        bind.execute(
            insert_stmt,
            {
                "slug": r["slug"],
                "topic": r["topic"],
                "title": r["title"],
                "body": r["body"],
                "metadata_json": json.dumps(r["metadata"]),
            },
        )


def downgrade() -> None:
    op.drop_index(
        "ix_product_knowledge_active",
        table_name="product_knowledge",
        schema="public",
    )
    op.drop_index(
        "ix_product_knowledge_topic",
        table_name="product_knowledge",
        schema="public",
    )
    op.drop_table("product_knowledge", schema="public")
