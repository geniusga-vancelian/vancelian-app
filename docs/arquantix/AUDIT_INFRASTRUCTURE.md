# Audit Infrastructure Arquantix.com

**Date:** 2026-01-03  
**Objectif:** Comprendre la configuration actuelle et identifier les changements nécessaires

---

## 📊 Configuration Actuelle

### 1. CloudFront Distribution

- **ID:** `EPJ3WQCO04UWW`
- **Status:** `Deployed`
- **Domain:** `d2gtzmv0zk47i6.cloudfront.net`
- **Aliases:** `www.arquantix.com` (et potentiellement `arquantix.com`)

### 2. Origin CloudFront

**Origin actuel:**
- **ID:** `S3-arquantix-coming-soon-dev`
- **Domain:** `arquantix-coming-soon-dev.s3.me-central-1.amazonaws.com`
- **Type:** S3 Origin
- **Path:** (vide)

**Conclusion:** CloudFront pointe actuellement vers un bucket S3, pas vers ECS.

### 3. Bucket S3

- **Bucket:** `arquantix-coming-soon-dev`
- **Contenu:** Fichiers HTML statiques (ancienne version "Coming Soon")

### 4. Service ECS

- **Cluster:** `arquantix-cluster` (créé aujourd'hui)
- **Service:** `arquantix-coming-soon` (créé aujourd'hui)
- **Status:** ACTIVE, 1/1 tasks running
- **IP:** `51.112.143.34:3000`
- **Image:** `arquantix-coming-soon:latest` (buildée aujourd'hui)

### 5. ECR

- **Repository:** `arquantix-coming-soon`
- **Images:** Plusieurs images buildées récemment
- **Dernière:** 2026-01-03

---

## 🔍 Analyse: Ce qui a changé

### Configuration Originale (quelques jours auparavant)

D'après l'audit, la configuration originale était:
- **CloudFront** → **S3** (`arquantix-coming-soon-dev`)
- Site statique HTML simple ("Coming Soon")
- Pas de service ECS

### Configuration Actuelle

Aujourd'hui, nous avons créé:
- **Service ECS** avec application Next.js
- **Image Docker** dans ECR
- Mais **CloudFront pointe toujours vers S3** (ancienne version)

---

## ❓ Pourquoi ces modifications sont nécessaires?

### 1. Changement d'Architecture

**Avant:**
```
CloudFront → S3 (HTML statique)
```

**Maintenant:**
```
CloudFront → ALB/ECS (Application Next.js dynamique)
```

### 2. Raisons du changement

- **Nouvelle application Next.js** avec composants React
- **Carousel d'images** (nécessite un serveur)
- **Rendu côté serveur** (SSR)
- **Plus complexe** qu'un simple HTML statique

### 3. CloudFront Origin

CloudFront nécessite un **nom de domaine** (pas une IP) pour les Custom Origins. Options:
- **ALB** (Application Load Balancer) avec DNS
- **Nom de domaine** pointant vers l'IP ECS
- **Service Discovery** (plus complexe)

---

## 🎯 Solution Proposée

### Option 1: Utiliser l'ALB existant (si disponible)

Si un ALB existe déjà pour arquantix, l'utiliser:
1. Trouver l'ALB DNS
2. Mettre à jour CloudFront origin vers l'ALB
3. Configurer le target group vers ECS

### Option 2: Créer un ALB (recommandé)

1. Créer ALB dans le même VPC que ECS
2. Créer Target Group pointant vers ECS (IP:3000)
3. Configurer Listener (HTTP:80)
4. Mettre à jour CloudFront origin vers ALB DNS

### Option 3: Garder S3 mais déployer le build Next.js

Alternative:
1. Build Next.js en mode `static export`
2. Déployer les fichiers statiques vers S3
3. CloudFront continue de pointer vers S3

**Problème:** Perd le SSR et certaines fonctionnalités dynamiques.

---

## 📋 Recommandation

**Option 2 (ALB)** est la meilleure solution car:
- ✅ Compatible avec Next.js SSR
- ✅ Scalable (plusieurs instances ECS)
- ✅ Health checks automatiques
- ✅ Compatible CloudFront (nom de domaine)

---

## 🔧 Actions Requises

1. **Créer ALB** (si permissions disponibles)
2. **Configurer Target Group** vers service ECS
3. **Mettre à jour CloudFront** origin vers ALB DNS
4. **Invalidation CloudFront** cache
5. **Tester** https://arquantix.com

---

## 📝 Notes

- L'ancienne configuration (S3) fonctionnait car c'était du HTML statique
- La nouvelle application Next.js nécessite un serveur (ECS)
- CloudFront ne peut pas pointer directement vers une IP, d'où le besoin d'un ALB

---

**Conclusion:** Les modifications sont nécessaires car on passe d'une architecture statique (S3) à une architecture dynamique (ECS), ce qui nécessite un ALB comme intermédiaire pour CloudFront.

