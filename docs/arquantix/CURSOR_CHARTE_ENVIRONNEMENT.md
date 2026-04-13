# Charte Cursor — stabilité environnement Arquantix

**Usage** : référence humaine et IA. La règle `.cursor/rules/arquantix-environment-stability.mdc` applique ces principes automatiquement dans Cursor.

**Contexte** : le projet a déjà subi un incident critique (changement de `COMPOSE_PROJECT_NAME`, stacks Docker multiples, bases `*_fresh` / `clean2` / `recover`, désalignement app / backend / DB).

---

## Règle absolue

**Aucune modification d’environnement sans validation explicite.**

---

## Interdictions strictes

Sans accord écrit préalable, ne pas :

- modifier `COMPOSE_PROJECT_NAME`
- créer un nouveau projet Docker (`clean`, `clean2`, `recover`, etc.)
- modifier les volumes Docker
- créer une nouvelle base de données (`*_fresh`, `*_test`, etc.)
- changer `DB_NAME`
- modifier `DATABASE_URL`
- lancer ou proposer `docker compose down -v`
- modifier les ports
- modifier les fichiers `.env` sans validation explicite
- créer une stack parallèle
- lancer ou conseiller un **`docker compose`** avec un `--project-name` différent de **`COMPOSE_PROJECT_NAME`** dans `.env.arquantix` pour « contourner » un projet officiel cassé **sans** validation explicite et **sans** renvoyer vers `docs/arquantix/LOCAL_ENV_RUNBOOK.md` (section projet officiel vs conteneurs actifs)

Si une solution implique l’une de ces actions : **s’arrêter et demander confirmation.**

---

## Process obligatoire (backend, PDF, API, DB, Docker, env)

1. **Audit** — Compréhension, fichiers concernés, risques.
2. **Diagnostic** — Causes possibles, **aucune modification**.
3. **Plan minimal** — Solution la plus simple, **sans** modification d’infra si possible.
4. **Validation** — Attendre validation avant d’écrire du code ou de modifier la config.

---

## Principe de stabilité

- **Une seule base PostgreSQL logique** : même `DB_NAME` / `DATABASE_URL` partout (voir `LOCAL_ENV_RUNBOOK.md`) — le nom peut être p.ex. `arquantix_fresh` selon l’historique local ; ne pas confondre avec le nom du **projet Compose**.
- **Un seul projet Compose officiel** pour `docker-compose.arquantix.yml` : la valeur de **`COMPOSE_PROJECT_NAME`** dans `.env.arquantix` (par défaut **`arquantix`**). Toute divergence entre ce nom et le label réel des conteneurs (`com.docker.compose.project` sur `arquantix-api`) est **critique** : le Makefile ne pilote pas la stack active.
- Une seule source de vérité documentée (`LOCAL_ENV_RUNBOOK.md`) ; diagnostics non destructifs : `scripts/arquantix_local_doctor.sh`.

---

## Interdiction des contournements infra

Il est **strictement interdit** de contourner un problème **fonctionnel** par une modification d’**infrastructure**.

Exemples interdits :

- créer une nouvelle base de données pour résoudre un bug ;
- créer une **nouvelle** stack Docker (nouveau `--project-name` ad hoc) pour éviter un conflit **sans** procédure documentée — si l’état Compose est cassé, la voie supportée est **arrêt du projet fautif** puis retour au projet officiel (`LOCAL_ENV_RUNBOOK.md` §3), pas un nom de projet permanent de secours ;
- modifier la configuration globale pour masquer un problème métier.

**Objectif** : résoudre les problèmes à la **bonne couche** (code, logique métier, API, contrats de données), pas en déplaçant ou dupliquant l’infra.

---

## Justification obligatoire des modifications d’infrastructure

Toute modification d’infrastructure doit être **justifiée par un besoin fonctionnel explicite**.

Pour toute proposition touchant l’infra, il faut :

- expliquer **pourquoi** la modification est **nécessaire** ;
- démontrer que ce n’est **pas** un contournement d’un bug à traiter ailleurs ;
- proposer des **alternatives sans modification d’infra** quand c’est possible.

**Sans justification claire : la modification est interdite.**

---

## Mode « fail fast » (cause non établie)

Si la cause d’un problème **n’est pas identifiée avec certitude**, **aucune solution ne doit être proposée** (ni code, ni infra, ni « test rapide » risqué).

Dans ce cas, fournir **uniquement** :

- un **diagnostic** structuré (faits observés, incertitudes) ;
- des pistes de **vérification** : logs, tests, `curl`, audits non destructifs, questions ciblées.

**Interdit** tant que la cause n’est pas établie :

- présenter des solutions **hypothétiques** comme des plans d’action définitifs ;
- modifier du code ou de l’infrastructure **« pour tester »** sans hypothèse validée et sans accord explicite.

---

## Gestion des erreurs

**À faire** : logs, analyse des réponses HTTP, tests `curl`, audit runtime, scripts **non destructifs** (ex. `scripts/arquantix_local_doctor.sh`).

**Interdit** : recréer un environnement, contourner par une nouvelle DB, changer la config globale « pour voir ».

---

## Mode debug autorisé

Logs Flutter / backend / BFF, `curl`, diagnostics lecture seule uniquement.

---

## Livrable attendu (réponses IA)

Chaque réponse sur un sujet sensible doit structurer :

- **A.** Diagnostic  
- **B.** Cause probable  
- **C.** Plan minimal  
- **D.** Risques  

---

## En cas de doute

**Poser une question — ne pas improviser.**

Toute violation de ces règles est considérée comme **critique**.

**Formule de démarrage recommandée** : *« Audit only. No code. No infra changes. »*

---

## Documentation liée

- `docs/arquantix/LOCAL_ENV_RUNBOOK.md`
- `docs/arquantix/CURSOR_PROMPTS.md` — prompts réutilisables (debug PDF 1 run, audit pré-prod, redémarrage local)
- `scripts/arquantix_local_doctor.sh`
