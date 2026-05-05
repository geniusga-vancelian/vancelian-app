---
title: "Custody : où sont stockés vos fonds chez Vancelian"
slug: custody-overview
category: trust-security
audience: client
status: draft
last_reviewed: 2026-05-04
sources:
  - vancelian-internal/legal/custody-architecture-2026.md
related:
  - regulation-overview.md
  - infrastructure-security.md
tags: ["custody", "cold storage", "ségrégation", "fonds clients", "trust", "security"]
questions:
  - Où sont stockés mes fonds ?
  - Qui détient mes cryptos ?
  - Vancelian peut-il accéder à mon argent ?
  - Que se passe-t-il si Vancelian fait faillite ?
  - Est-ce que mes fonds sont en cold storage ?
  - Mes euros sont-ils ségrégués ?
  - Where are my funds stored?
  - Who holds my crypto?
  - What happens if Vancelian goes bankrupt?
---

# Custody : où sont stockés vos fonds chez Vancelian

## Réponse courte

Vos fonds sont **séparés** des fonds propres de Vancelian. Les **euros**
sont conservés sur des comptes ségrégués chez des établissements de
paiement réglementés en Europe. Les **crypto-actifs** sont stockés
majoritairement en **cold storage** chez des dépositaires
institutionnels régulés (custody qualifiée), avec une part minoritaire
en hot wallet pour assurer la liquidité opérationnelle. En cas
d'incident sur Vancelian (faillite, fermeture), les actifs ségrégués
restent **votre propriété** et ne peuvent pas servir à rembourser les
créanciers de Vancelian.

## Détails

### Ségrégation des fonds

Le principe fondamental est la **ségrégation comptable et juridique**
entre :

* Les **fonds clients** (vos dépôts, vos cryptos) — qui restent
  juridiquement votre propriété.
* Les **fonds propres** de Vancelian — qui appartiennent à la société.

Cette séparation est **imposée par la réglementation** PSAN / MiCA et
est auditée régulièrement.

### Euros / monnaie fiat

Les euros déposés sur Vancelian sont :

* Détenus sur des **comptes de cantonnement** (ring-fenced accounts)
  ouverts auprès d'établissements de paiement régulés (EME / EP) au
  sein de l'Espace Économique Européen.
* Ces comptes sont **ségrégués** comptablement : ils ne peuvent pas
  être utilisés pour les opérations courantes de Vancelian.
* En cas de défaut de Vancelian, ces fonds sont restitués aux clients
  selon la procédure de protection des fonds clients prévue par la
  réglementation européenne (DSP2 / cantonnement).

### Crypto-actifs

L'architecture crypto de Vancelian repose sur deux niveaux :

1. **Cold storage** (majorité des fonds clients)
   * Clés privées stockées **hors-ligne**, dans des coffres physiques
     sécurisés (HSM, multi-signature).
   * Confiés à des **dépositaires qualifiés** régulés (custody
     institutionnelle).
   * Aucun accès direct possible depuis Internet.

2. **Hot wallet opérationnel** (minorité — liquidité quotidienne)
   * Volume strictement limité, calibré sur les flux de retrait
     attendus.
   * Multi-signature, monitoring 24/7.
   * Couverture par police d'assurance dédiée chez certains
     partenaires.

### Que se passe-t-il en cas de faillite de Vancelian ?

* Les **euros ségrégués** sont restitués via le mécanisme de
  cantonnement (procédure réglementaire).
* Les **crypto-actifs** restent stockés chez le dépositaire qualifié,
  qui reconnaît votre propriété juridique. Une procédure de
  restitution est déclenchée.
* Les **fonds propres** de Vancelian (et eux seuls) servent à régler
  les créanciers commerciaux de la société.

Aucun mécanisme parfait n'existe — un dépositaire peut lui-même faire
défaut. C'est pourquoi Vancelian **diversifie ses partenaires custody**
et publie régulièrement des rapports d'attestation de réserves
(*proof of reserves* lorsqu'applicable).

### Vancelian peut-il toucher à votre argent ?

Non au sens propriété. Oui au sens opérationnel **uniquement** sur :

* Les **opérations que vous initiez** (achat, vente, retrait,
  allocation à un Vault).
* Les **frais affichés** dans les conditions générales.
* Les **opérations imposées** par la régulation (gel sur sanctions
  internationales, demande TRACFIN).

Aucune équipe Vancelian ne peut effectuer d'opération discrétionnaire
sur les comptes clients en dehors de ces cas.

## Sources

- *vancelian-internal/legal/custody-architecture-2026.md* — note
  interne (à finaliser pour version client publique). Référence aux
  conventions custody en vigueur.
