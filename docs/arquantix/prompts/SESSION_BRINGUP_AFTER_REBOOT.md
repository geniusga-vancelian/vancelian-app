# Prompt Cursor — bring-up session Arquantix (après reboot Mac)

Coller le bloc ci-dessous tel quel dans le chat Cursor (agent) pour une remise en état de travail **sans** actions destructives.

**Référence projet Docker** : `arquantixrecovery` + `docker-compose.arquantix-recovery.yml` (pas le namespace legacy `arquantix`).

---

## Texte à coller

```
Lis d'abord le runbook local Arquantix du dépôt, en particulier :
- docs/LOCAL_DOCKER_RECOVERY.md
- docs/arquantix/LOCAL_ENV_RUNBOOK.md
- tout script de démarrage local réellement utilisé par le projet

Contexte actuel après reboot Mac :
- Docker Desktop est déjà redémarré proprement
- la stack Docker valide est `arquantixrecovery`
- `vancelian-postgres` tourne aussi
- je ne veux PAS relancer Docker au hasard si la stack est déjà up
- je ne veux PAS utiliser le projet `arquantix`
- je ne veux PAS faire de manipulation destructive
- je veux remettre tout le projet en état de travail depuis Cursor, proprement

Contraintes absolues :
- Ne jamais utiliser :
  - docker compose down -v
  - docker volume prune
  - docker system prune --volumes
- Ne jamais toucher aux volumes
- Ne jamais lancer le projet legacy `arquantix`
- Toujours considérer comme référence :
  - project = `arquantixrecovery`
  - compose file = `docker-compose.arquantix-recovery.yml`

Ta mission :
1. Lire le runbook et les scripts de démarrage réellement utilisés
2. Vérifier l'état courant du projet local
3. Identifier ce qui est déjà lancé et ce qui manque encore pour travailler
4. Lancer uniquement ce qui manque
5. Me dire clairement l'état final

Je veux que tu vérifies au minimum :
- que Docker répond
- que la stack `arquantixrecovery` est bien up
- que l'API répond sur http://127.0.0.1:8000/health
- que le web est accessible sur http://127.0.0.1:3000
- que la DB recovery est bien celle attendue (Strapi / port 1337 retirés du compose)
- s'il faut aussi lancer autre chose hors Docker (par exemple un serveur host-side, un worker, un process Next local, etc.), fais-le seulement si le runbook ou le setup réel le demande explicitement

Très important :
- Ne redémarre pas tout "par principe"
- Ne fais pas un refactor
- Ne modifie pas les fichiers
- Fais seulement un bring-up propre de l'environnement de travail
- Si tout est déjà démarré, dis-le simplement et ne relance rien inutilement

À la fin, donne-moi un résumé clair :
1. ce qui tournait déjà
2. ce que tu as lancé
3. les URLs utiles
4. s'il reste une action manuelle ou non
```
