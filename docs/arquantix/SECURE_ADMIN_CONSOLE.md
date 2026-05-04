# Espace admin sécurisé — `console.arquantix.com`

L'admin (CMS Next.js) **n'est plus accessible publiquement via `arquantix.com/admin`**.
Il vit désormais sur un **sous-domaine dédié** : `console.arquantix.com`.

## 1. Principe

| | Site public | Console admin |
|---|---|---|
| Hôte | `arquantix.com` | `console.arquantix.com` |
| ALB | rule prio 50 (assets) + default → web TG | rule prio 40 → web TG |
| Routes admin | **404 (fixed-response ALB prio 30)** | servies normalement |
| `/api/admin/*` | **404 (ALB prio 30 + middleware Next.js)** | servies normalement |
| `/` | redirect vers `/{locale}` | **redirect vers `/admin/login`** |
| Tout chemin non-`/admin` | servi par Next.js | **404 (middleware Next.js)** sauf exceptions ↓ |
| `/preview/*` | servi (status quo) | servi (utilisé par les iframes admin) |
| `/robots.txt` | host-aware (Allow:/, Disallow `/admin/`, ...) | host-aware (`Disallow: /`) |
| `/sitemap.xml` | servi | servi |
| `X-Robots-Tag` | absent | `noindex, nofollow, noarchive` (toutes réponses) |
| `<meta name="robots">` | absent | `noindex, nofollow, noarchive` (générée par RootLayout) |
| `/robots.txt` | `Allow:/` + Disallow `/admin/`, `/api/admin/`, `/api/`, `/preview/` | **`Disallow: /`** |

## 2. Composants AWS

### 2.1 Route53
- A alias `console.arquantix.com.` → ALB `arquantix-alb-718188586.us-east-1.elb.amazonaws.com.`
- TTL alias managé par AWS (≈ 60 s).

### 2.2 ACM
- Certificat `arquantix.com` + SAN `*.arquantix.com` (ARN `arn:aws:acm:us-east-1:411714852748:certificate/006a1832-...`).
- `console.arquantix.com` est couvert par le wildcard, **aucun cert supplémentaire à émettre**.

### 2.3 ALB rules (ordre de priorité)

| Prio | Host | Path | Action | But |
|---|---|---|---|---|
| 30 | `arquantix.com` | `/admin`, `/admin/*`, `/api/admin/*` | **fixed-response 404 (text/plain)** | bloquer tout accès public à l'admin |
| 40 | `console.arquantix.com` | `*` | forward → web TG | servir l'admin sur le sous-domaine privé |
| 50 | `arquantix.com` | `/api/site/media/*`, `/_next/*` | forward → web TG | assets publics + média |
| 100 | `api.arquantix.com` | `*` | forward → api TG | FastAPI |
| 999 | `maintenance-tg-binder.internal.invalid` | `*` | forward → maintenance TG | binding TG (mode maintenance, voir `MAINTENANCE_MODE.md`) |
| default | — | — | forward → web TG | site public Next.js |

> **Note** : la rule prio 50 ne contient plus `/admin*` ni `/api/admin/*` (elles ont été retirées au moment de la bascule sécu).

## 3. Code application

### 3.1 Middleware Next.js (`src/middleware.ts`)
Contrôle host-aware :
- détection via env `ADMIN_CONSOLE_HOSTS` (CSV, défaut `console.arquantix.com`)
- sur l'hôte console : `/` → 307 `/admin/login`, paths non-admin → 404, `X-Robots-Tag` ajouté à toutes les réponses (y compris `/_next/*`, `/api/admin/*`, redirects)
- sur les autres hôtes : `/admin*` et `/api/admin/*` → 404 (défense en profondeur si la rule ALB 30 venait à disparaître)
- `/robots.txt` et `/sitemap.xml` sont laissés passer sur console pour permettre le rendu de la version host-aware
- `/preview/*` est laissé passer sur console (les iframes admin de `/admin/pages/*` et `/admin/pages/*/add-module` y pointent en URL relative pour rendre l'aperçu d'une page, section, module commun, article, ou section-demo)

Le matcher inclut explicitement `/api/admin/:path*` pour que le middleware puisse aussi bloquer ces routes côté Next.js.

### 3.2 Métadonnées (`src/app/layout.tsx`)
`generateMetadata()` injecte `robots: { index:false, follow:false, nocache:true, googleBot:{ index:false, follow:false, noimageindex:true } }` quand :
- l'hôte est dans `ADMIN_CONSOLE_HOSTS`, **ou**
- le pathname commence par `/admin`

→ Next.js rend `<meta name="robots" content="noindex, nofollow, ...">` dans la page.

### 3.3 `/robots.txt` (`src/app/robots.ts`)
Endpoint dynamique (`force-dynamic`) qui renvoie :
- sur l'hôte console : `Disallow: /`
- ailleurs : `Allow: /` + Disallow `/admin/`, `/api/admin/`, `/api/`, `/preview/` + sitemap

### 3.4 Cookie de session
`arq_admin_session` — `path:'/'`, sans `domain` explicite → **scope au host courant**. Une session ouverte sur `console.arquantix.com` n'est **pas partagée** avec `arquantix.com` (ni avec une autre machine du sous-domaine). C'est intentionnel.

## 4. Commandes utiles

### 4.1 Vérifier l'état des rules ALB
```bash
LISTENER_443=$(aws elbv2 describe-listeners --region us-east-1 \
  --load-balancer-arn $(aws elbv2 describe-load-balancers --region us-east-1 \
    --names arquantix-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text) \
  --query 'Listeners[?Port==`443`].ListenerArn | [0]' --output text)

aws elbv2 describe-rules --region us-east-1 --listener-arn "$LISTENER_443" \
  --query 'Rules[].{Prio:Priority,Host:Conditions[?Field==`host-header`] | [0].HostHeaderConfig.Values,Path:Conditions[?Field==`path-pattern`] | [0].PathPatternConfig.Values,Action:Actions[0].Type}' \
  --output table
```

### 4.2 Smoke tests
```bash
# Doit être 307 + X-Robots-Tag
curl -sI https://console.arquantix.com/

# Doit être 200
curl -sI https://console.arquantix.com/admin/login

# Doit être 404 (ALB) — pas le HTML 404 Next.js
curl -sI https://arquantix.com/admin/login
curl -sI https://arquantix.com/api/admin/login

# Doit être Disallow: /
curl -s https://console.arquantix.com/robots.txt
```

### 4.3 Login admin
```bash
curl -X POST https://console.arquantix.com/api/admin/login \
  -H 'content-type: application/json' \
  -d '{"email":"<email>","password":"<mdp>"}' \
  -c /tmp/admin.cookies -i

# Puis utiliser /tmp/admin.cookies pour les autres requêtes
curl https://console.arquantix.com/admin/articles -b /tmp/admin.cookies
```

## 5. Procédure de désactivation (si besoin)

> ⚠️ Réouvre `arquantix.com/admin` au public. À éviter sauf raison forte.

```bash
LISTENER_443=$(...)
RULE_30_ARN=$(aws elbv2 describe-rules --region us-east-1 --listener-arn "$LISTENER_443" \
  --query 'Rules[?Priority==`30`] | [0].RuleArn' --output text)

# Étape 1 : supprimer le 404 fixed-response
aws elbv2 delete-rule --region us-east-1 --rule-arn "$RULE_30_ARN"

# Étape 2 : remettre /admin* et /api/admin/* dans la rule prio 50
RULE_50_ARN=$(aws elbv2 describe-rules --region us-east-1 --listener-arn "$LISTENER_443" \
  --query 'Rules[?Priority==`50`] | [0].RuleArn' --output text)

aws elbv2 modify-rule --region us-east-1 --rule-arn "$RULE_50_ARN" \
  --conditions '[{"Field":"host-header","HostHeaderConfig":{"Values":["arquantix.com"]}},{"Field":"path-pattern","PathPatternConfig":{"Values":["/admin*","/api/admin/*","/api/site/media/*","/_next/*"]}}]'
```

Le code Next (middleware) bloque toujours `/admin*` sur les hôtes non-console : pour réautoriser, ajouter le host concerné à `ADMIN_CONSOLE_HOSTS` dans la task def, ou retirer le bloc défense en profondeur du middleware.

## 6. Ce qui reste à faire (sécurité — itérations futures)

Ce setup ferme l'accès public via `/admin` et empêche l'indexation. **La barrière réseau reste limitée** : `console.arquantix.com` est joignable depuis Internet. Le login + 2FA + rate-limit constituent la vraie défense.

À auditer / ajouter dans des itérations séparées :

1. **2FA admin obligatoire** — auditer `src/lib/auth.ts` et `src/app/api/admin/login/route.ts` ; ajouter TOTP/WebAuthn si manquant.
2. **Rate-limit global sur `/api/admin/*`** — utiliser le Redis ElastiCache déjà en place.
3. **Logs des connexions admin** — IP, user-agent, succès/échec ; rétention 90 j minimum.
4. **Verrouillage temporaire** — N tentatives échouées → blocage 15 min.
5. **Couche réseau supplémentaire (optionnelle, gros chantier)** :
   - `Cloudflare Access` : nécessite migration DNS Route53 → Cloudflare. Permet SSO Google Workspace + IP allowlist + journalisation, **avant** d'arriver à l'app.
   - `IP allowlist via WAF` : règle WAFv2 attachée à l'ALB qui n'autorise `console.arquantix.com` que pour des IPs blanches.
   - `Cognito Hosted UI` devant le login Next : lourd, pas recommandé sauf SSO entreprise.
6. **Communication équipe** : la nouvelle URL est `https://console.arquantix.com/admin/login`. Les sessions précédentes sur `arquantix.com` sont invalidées (cookie scope différent) → re-login obligatoire.
