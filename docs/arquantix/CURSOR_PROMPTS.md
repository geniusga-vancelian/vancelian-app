# Prompts Cursor — diagnostics et exploitation Arquantix

Prompts prêts à coller en début de session ou avant une tâche ciblée. Ils complètent la [charte environnement](./CURSOR_CHARTE_ENVIRONNEMENT.md).

**Usage recommandé** : préfixer par *« Audit only. No code. No infra changes. »* quand la charte l’exige.

---

## Session bring-up après reboot Mac (stack `arquantixrecovery`)

Prompt prêt à coller pour une remise en état **lecture + vérifs + lancement minimal** (sans `down -v`, sans projet legacy `arquantix`).

- **Fichier source** : [prompts/SESSION_BRINGUP_AFTER_REBOOT.md](./prompts/SESSION_BRINGUP_AFTER_REBOOT.md)
- **Afficher dans le terminal** : `bash scripts/cursor_prompt_arquantix_bringup.sh`
- **Copier tout le fichier sous macOS** : `bash scripts/cursor_prompt_arquantix_bringup.sh | pbcopy` puis coller dans Cursor

---

## 1. Debug PDF en 1 run

```
Audit only. No code. No infra changes.

Je veux un debug PDF en 1 run, ultra ciblé, pour identifier en une seule passe où casse la génération du PDF de relevé d'opération.

Contexte

Le flux concerné est :
	•	Flutter : écran détail transaction
	•	BFF : /api/mobile/flutter/transactions/{id}/operation-statement.pdf
	•	API : /api/app/transactions/{id}/operation-statement.pdf

Le symptôme observé est :
	•	clic sur "Télécharger"
	•	message : "Impossible de générer le relevé pour le moment"

Je veux un diagnostic prouvé, pas des hypothèses.

Objectif

Obtenir, pour une seule transaction réelle, la chaîne complète :

Flutter → BFF → API → DB/snapshot → renderer PDF

et identifier exactement :
	•	le status HTTP réel
	•	la couche qui casse
	•	le message d'erreur réel
	•	le correctif minimal

⸻

Ce que je veux faire dans ce run unique

1. Choisir une transaction test unique

Je veux que tu me proposes comment sélectionner une seule transaction test valide :
	•	custody completed de préférence
	•	appartenant bien au bon client
	•	idéalement sans snapshot si cela simplifie le diagnostic

Tu dois expliquer comment la retrouver dans la base ou via l'API.

⸻

2. Instrumentation à lire, pas à inventer

Tu dois t'appuyer sur les logs déjà présents dans le code :
	•	Flutter : OPERATION_STATEMENT_PDF, TransactionScreen
	•	BFF : OPERATION_STATEMENT_PDF_BFF_ENTRY, OPERATION_STATEMENT_PDF_UPSTREAM_STATUS
	•	API : OPERATION_STATEMENT_PDF: ...

Je veux que tu me dises exactement :
	•	quelles lignes de logs je dois capturer
	•	dans quel ordre les lire
	•	ce qu'elles prouvent

⸻

3. Test direct hors Flutter

Je veux que tu me donnes la commande curl exacte à exécuter :
	•	via le BFF
	•	puis si nécessaire en direct sur l'API

avec le même token et le même transaction_id

Je veux relever :
	•	status
	•	headers
	•	Content-Type
	•	X-Vancelian-Error-Code
	•	si le corps est un %PDF ou un JSON erreur

⸻

4. Lecture de la cause

Je veux que tu me donnes un tableau de décision simple :
	•	si 503 + message WeasyPrint → conclusion / action
	•	si 404 + operation_statement_not_* → conclusion / action
	•	si 500 BFF sans log API → conclusion / action
	•	si 200 API directe mais échec via BFF → conclusion / action
	•	si snapshot hit + payload invalide → conclusion / action

Je veux du concret, pas du flou.

⸻

5. Vérification snapshot PR5

Pour la transaction testée, je veux savoir :
	•	si un snapshot existe
	•	comment l'inspecter
	•	ce qu'il faut vérifier dedans
	•	quand il faut le conserver
	•	quand il faut juste l'analyser sans le supprimer

Aucune suppression sans validation explicite.

⸻

Livrable attendu

A. Transaction test choisie
	•	laquelle
	•	pourquoi

B. Séquence exacte du run
	•	clic app ou curl
	•	logs à capturer
	•	commandes à lancer

C. Tableau d'interprétation
	•	symptôme → cause probable → action minimale

D. Critère de succès

À la fin du run, je dois pouvoir dire avec certitude :
	•	la couche qui casse
	•	la cause racine la plus probable
	•	la correction minimale à appliquer

Important
	•	Ne code pas
	•	Ne change pas l'infra
	•	Ne modifie pas l'environnement
	•	Ne propose pas de workaround

Je veux un run de diagnostic unique, ordonné, fiable et reproductible.
```

---

## 2. Audit infra complet avant prod

```
Audit only. No code. No infra changes.

Je veux un audit infra complet avant prod pour le projet Arquantix, orienté stabilité, déploiement, reproductibilité et sécurité opérationnelle.

Objectif

Identifier tout ce qui pourrait empêcher :
	•	un démarrage fiable
	•	un déploiement cohérent
	•	un rendu PDF correct
	•	un bon alignement app / BFF / backend / DB
	•	une mise en prod ou pré-prod stable

Je veux un audit structuré, sérieux, concret.

⸻

Périmètre

1. Configuration et environnements

Analyser :
	•	.env.arquantix
	•	.env
	•	services/arquantix/api/.env.local
	•	services/arquantix/web/.env.local
	•	toutes les variables utiles au runtime

Je veux savoir :
	•	quelles sont les sources de vérité
	•	où existent encore des ambiguïtés
	•	quelles variables sont critiques pour prod / staging / local
	•	quels risques de désalignement persistent

⸻

2. Docker / Compose

Analyser :
	•	docker-compose.arquantix.yml
	•	scripts de démarrage / reset / doctor
	•	volumes
	•	réseaux
	•	dépendances
	•	health checks

Je veux savoir :
	•	si la stack est redémarrable de manière fiable
	•	si les volumes critiques sont bien protégés
	•	si les noms de réseau / volumes sont cohérents
	•	si des scripts restent dangereux
	•	si des projets Docker parasites peuvent encore exister

⸻

3. Base de données et migrations

Je veux un audit sur :
	•	stratégie Alembic
	•	base canonique
	•	risques de DB vide / mauvaise DB / migration manquante
	•	cohérence API / web / Prisma / Alembic
	•	procédure de montée de version

Je veux savoir si la chaîne DB est suffisamment sûre pour un environnement sérieux.

⸻

4. BFF / Backend alignment

Je veux vérifier :
	•	comment le BFF choisit son backend
	•	quels risques existent sur BACKEND_URL, API_BASE_URL, NEXT_PUBLIC_BACKEND_URL
	•	comment prouver que le BFF parle au bon backend
	•	quels garde-fous ou logs manquent encore

⸻

5. PDF stack

Je veux un audit spécifique sur :
	•	WeasyPrint
	•	dépendances système
	•	différences local / Docker / staging / prod
	•	chemins de templates
	•	CSS / assets
	•	risques de génération cassée ou divergente selon l'environnement

⸻

6. Observabilité / exploitabilité

Je veux analyser :
	•	logs existants
	•	health endpoints
	•	commandes de vérification
	•	doctor script
	•	runbook

Je veux savoir si un ingénieur peut diagnostiquer un incident rapidement sans improviser.

⸻

7. Risques avant prod

Je veux une liste priorisée :
	•	P0
	•	P1
	•	P2

Avec pour chaque point :
	•	le risque
	•	la conséquence
	•	la probabilité
	•	la mitigation recommandée

⸻

Livrable attendu

Partie A — Cartographie infra
	•	composants
	•	dépendances
	•	sources de vérité

Partie B — Risques identifiés
	•	triés par gravité

Partie C — Gaps avant prod
	•	ce qui manque encore
	•	ce qui est acceptable
	•	ce qui est bloquant

Partie D — Recommandations
	•	minimales
	•	concrètes
	•	sans sur-ingénierie

Partie E — Checklist avant prod

Je veux une checklist exploitable, du type :
	•	env alignés
	•	migrations appliquées
	•	WeasyPrint OK
	•	BFF vers bon backend
	•	PDF smoke test
	•	rollback known
	•	etc.

Important
	•	Pas de code
	•	Pas de changement d'infra
	•	Pas de refactor
	•	Pas de workaround

Je veux un audit d'aptitude à l'exploitation sérieuse, pas un brainstorming.
```

---

## 3. Redémarrage from scratch via script, sans accroc

```
Je veux mettre en place un redémarrage from scratch du projet Arquantix après reboot du PC, via un script sûr, reproductible, non destructif, et aligné avec la configuration locale canonique.

Contexte

Je veux pouvoir redémarrer mon poste, ouvrir le projet, lancer une seule commande ou un seul script, et retrouver un environnement local fonctionnel sans accroc.

Je veux éviter :
	•	stacks Docker parallèles
	•	mauvaise DB
	•	mauvais COMPOSE_PROJECT_NAME
	•	mauvaises variables d'environnement
	•	démarrage partiel
	•	confusion entre services

Objectif

Créer ou durcir un script de démarrage unique, safe, qui :
	•	vérifie l'environnement
	•	démarre la bonne stack
	•	vérifie la santé minimale
	•	échoue proprement si quelque chose est incohérent
	•	ne détruit rien

⸻

Contraintes strictes

Tu n'as pas le droit de :
	•	changer COMPOSE_PROJECT_NAME
	•	créer une nouvelle stack
	•	modifier DB_NAME
	•	créer une nouvelle DB
	•	supprimer des volumes
	•	lancer down -v
	•	faire un reset destructif

Le script doit être :
	•	lisible
	•	idempotent
	•	non destructif
	•	orienté développeur local

⸻

Ce que je veux auditer d'abord

Avant toute modification, analyse l'existant :
	•	Makefile.arquantix
	•	scripts/start-arquantix.sh
	•	scripts/dev-reset.sh
	•	scripts/arquantix_local_doctor.sh
	•	docker-compose.arquantix.yml
	•	docs/arquantix/LOCAL_ENV_RUNBOOK.md

Je veux savoir :
	•	ce qui existe déjà
	•	ce qui est redondant
	•	ce qui est dangereux
	•	quel est le meilleur point d'entrée unique

⸻

Ce que je veux obtenir

1. Une commande officielle unique

Exemple :

bash scripts/start-arquantix.sh

ou une cible Make si c'est meilleur.

Je veux qu'il y ait une seule façon officielle de démarrer.

2. Vérifications préalables

Le script doit vérifier au minimum :
	•	Docker disponible
	•	.env.arquantix présent
	•	DB_NAME=arquantix
	•	projet / compose cohérent
	•	ports principaux non incohérents si pertinent
	•	services nécessaires définis

3. Démarrage

Le script doit lancer la stack standard, sans variations parasites.

4. Vérifications post-démarrage

Le script doit vérifier :
	•	API health
	•	éventuellement OpenAPI
	•	conteneurs critiques up
	•	doctor script si utile
	•	message final clair

5. Gestion d'erreur propre

Si quelque chose ne va pas, le script doit :
	•	afficher une erreur claire
	•	s'arrêter
	•	ne rien casser
	•	indiquer quoi vérifier ensuite

⸻

Livrable attendu

Partie A — Audit de l'existant
	•	point d'entrée recommandé
	•	dangers à éviter
	•	redondances

Partie B — Modifications proposées
	•	fichiers modifiés
	•	pourquoi

Partie C — Script final
	•	ou cible finale
	•	comportement
	•	usage exact

Partie D — Documentation

Mettre à jour le runbook local si nécessaire avec :
	•	la commande officielle
	•	les prérequis
	•	les échecs connus
	•	les limites

Important

Je veux une solution top niveau mais sobre :
	•	pas sur-ingénierée
	•	pas destructrice
	•	pas dépendante d'une mémoire humaine fragile

Commence par un audit, puis propose la solution minimale la plus robuste.
```

---

## 4. Design PDF — structure HTML (`operation_statement.html`)

```
Audit only. No business logic change. Only HTML structure.

Le template PDF actuel ne respecte pas le design cible.

Objectif :
Refactoriser la structure HTML de operation_statement.html pour obtenir un layout bancaire premium.

Contraintes :
- ne pas modifier le backend
- ne pas modifier les données
- uniquement HTML + classes CSS

À faire :

1. Header layout
Créer un layout en 2 colonnes :

Gauche :
- Account holder
- Address

Droite :
- Currency
- IBAN
- BIC / SWIFT
- Account Number

Structure attendue :

<div class="header">
  <div class="header-left">...</div>
  <div class="header-right">...</div>
</div>

2. Ligne label / valeur

Chaque ligne doit être :

<div class="row">
  <span class="label">...</span>
  <span class="value">...</span>
</div>

Alignement horizontal obligatoire.

3. Table transactions

Utiliser un vrai tableau structuré :

<table class="transactions">
  <thead>...</thead>
  <tbody>...</tbody>
</table>

Chaque colonne séparée clairement.

4. Sections

Créer des sections distinctes :

- header
- balances
- transactions
- footer

Avec classes :

.section
.section-title

5. Ne PAS utiliser de layout vertical brut ou <br>

Objectif :
structure claire, stable, propre pour CSS.

Livrable :
HTML propre, lisible, structuré, prêt pour stylisation.
```

---

## 5. Design PDF — CSS premium (`operation_statement.css`)

```
No HTML change. Only CSS improvement.

Objectif :
Transformer le PDF en rendu bancaire premium.

À corriger :

1. Typographie

- font-family: Inter, Helvetica, Arial
- title: 28px bold
- section titles: 18px semi-bold
- labels: 12px grey (#777)
- values: 14px bold (#111)

2. Spacing

- section margin: 32px
- row spacing: 12px
- table row padding: 14px

3. Header cards

.header-left, .header-right {
  background: #f5f5f7;
  border-radius: 12px;
  padding: 20px;
}

4. Grid header

.header {
  display: flex;
  gap: 24px;
}

.header-left, .header-right {
  flex: 1;
}

5. Table

.transactions {
  width: 100%;
  border-collapse: collapse;
}

.transactions th {
  text-align: left;
  font-size: 12px;
  color: #888;
  border-bottom: 1px solid #ddd;
}

.transactions td {
  padding: 14px 0;
  border-bottom: 1px solid #eee;
}

6. Amounts

.credit {
  color: #0a8f3c;
}

.debit {
  color: #c0392b;
}

7. Footer

.footer {
  margin-top: 40px;
  font-size: 10px;
  color: #777;
}

Objectif final :
- rendu aéré
- lisible
- premium
- proche d'une banque type Revolut / BNP
```

*(Les classes réelles du dépôt utilisent le préfixe `opstmt-` et `opstmt-header`, `opstmt-transactions`, etc., pour cohabiter avec le reste du template.)*

---

## 6. Génération PDF locale (sans Flutter)

L’outil est implémenté : `services/arquantix/api/scripts/generate_pdf_preview.py` + cible `make -f Makefile.arquantix pdf-preview ARGS='...'`. Voir [LOCAL_ENV_RUNBOOK.md](./LOCAL_ENV_RUNBOOK.md) §9.

---

**Dernière mise à jour :** 2026-04-13
