---
status: treated
date: 2026-04-20
feedback_type: negative
source_question: "Est-ce que mon argent est garanti si j'investis dans vos offres exclusives ?"
user_comment: "Mauvaise réponse. La question porte sur les offres exclusives — 2 types : (a) Cloud Mining achat de puissance, (b) Dubai/Bali/... prêt 100% crypto. Pas de oui/non. Les offres exposent la mécanique et les contreparties ont des engagements sur le capital investi qui doit être restitué. Sur les garanties : se fier à la documentation, mais en aucun cas une garantie ne protège contre un risque de défaut (total ou partiel) de la contrepartie."
wiki_pages_used:
  - faq/exclusive-offers/guarantees-and-security-of-your-investment.md
  - faq/exclusive-offers/how-are-returns-generated-dubai-villa.md
  - faq/exclusive-offers/dubai-villa-risk-summary.md
  - faq/legal-compliance/risk-warning-summary.md
  - faq/exclusive-offers/guarantees-and-security-al-barari.md
channel_id: C0ASFKQFY2V
feedback_user: U01UY0Q7ZE1
treated_date: 2026-04-20
treated_action: bot_rule_added_and_wiki_fixed
---

# Est-ce que mon argent est garanti si j'investis dans vos offres exclusives ?

## Client question
> Est-ce que mon argent est garanti si j'investis dans vos offres exclusives ?

## Bot answer (extrait)
> Non, il n'y a pas de garantie formelle de capital sur les offres exclusives. Vous prêtez directement à une contrepartie externe (Solaria pour Dubai, par exemple) qui finance un projet immobilier. En échange de cette exposition directe — moins d'intermédiaires — vous percevez un rendement attractif (10,7% à 11,5% pour Dubai Villa, par exemple).
>
> Cela dit, le risque n'est pas sans structure. Chaque offre est conçue avec plusieurs niveaux d'atténuation du risque.
> [...]
> Un taux de 10,7% à 11,5% n'existe pas par hasard. Il reflète directement ce modèle de prêt direct : moins d'intermédiaires, taux meilleur pour vous, en échange d'une exposition à la contrepartie et au projet lui-même.

## Feedback
**Type:** negative
**User correction (Jean):** *"La question porte sur les offres exclusives. Encore une fois il y a 2 types d'offre exclusive : (a) Cloud Mining achat de puissance, (b) Dubai, Bali... prêt 100% crypto. Donc il ne faut pas répondre oui ou non, il faut dire que les offres exposent la mécanique et que les contreparties ont des engagements sur le capital investi qui doit être restitué. Sur les garanties il faut se fier à la documentation, mais en aucun cas une garantie ne protège contre un risque de défaut ou partiel de la contrepartie qui fournit une offre."*

## Diagnosis

Quatre défauts imbriqués.

### Défaut 1 — Yes/no en ouverture
*"Non, il n'y a pas de garantie formelle"*. Même famille de pattern que les yes/no déjà interdits (fiscal, investment-decision) étendue à la nature du produit : prend position au lieu d'exposer la mécanique. Le client n'a pas besoin d'un oui ou d'un non — il a besoin de comprendre la structure d'engagement.

### Défaut 2 — Absence du type d'offre
Règle déjà gravée (`feedback_offer_type_distinction.md`) mais revient : le bot saute directement sur Dubai / Bali sans rappeler que les offres exclusives sont de deux types — (a) Cloud Mining = achat de puissance auprès de Vancelian LTD ADGM, opéré par Hearst Solution FZCO ; (b) offres immobilières / prêts crypto (Dubai Al Barari, Munduk Bali, Niseko) = prêt 100% crypto à une contrepartie identifiée par offre. Sans cette distinction, la réponse traite les offres exclusives comme un bloc homogène, ce qui est faux.

### Défaut 3 — Mélange "garantie" vs "atténuation"
Le bot empile des éléments (pré-financement, marge de sécurité, collatéral de facto, terrain 650k USD, construction) sous le label *"atténuation du risque"*, qui se lit comme une liste de quasi-garanties. Cette énumération dilue la règle absolue et crée un effet rassurance-par-liste exactement contraire à la nature de ces produits. Toutes ces atténuations, quelle que soit leur combinaison, ne changent pas le plafond : aucune ne couvre le défaut de contrepartie.

### Défaut 4 — Règle absolue absente + digression commerciale
La phrase clé de Jean — *"aucune garantie ne protège contre un risque de défaut (total ou partiel) de la contrepartie"* — n'apparaît pas dans la réponse du bot. Et la page wiki `guarantees-and-security-of-your-investment.md` (Bali) ne la contenait pas non plus explicitement (la page Al Barari disait *"Vancelian does not guarantee repayment"* mais sans poser le plafond absolu sur Solaria elle-même).

En plus, le bot termine par une digression commerciale : *"Un taux de 10,7% à 11,5% n'existe pas par hasard. Il reflète directement ce modèle de prêt direct : moins d'intermédiaires, taux meilleur pour vous..."*. Sur une question de garantie/risque, pivoter vers le pitch du rendement est un contre-sens éditorial. C'est une tentative de rassurance commerciale sur une question qui demandait une réponse factuelle sur la mécanique.

### Défaut transversal — Longueur
La réponse fait ~350 mots et 7 paragraphes alors qu'une réponse de 4-6 paragraphes aurait suffi. Le bot sur-développe systématiquement ; règle gravée le 2026-04-20 dans `<editorial_method>` DEPTH CONTROL et `<self_check>` point 10 : la réponse la plus courte possible en restant factuelle, laisser le client repréciser s'il veut plus de détail.

## Action taken

1. **bot.js — `<forbidden_patterns>` enrichi** : (i) yes/no sur question de garantie interdit (*"Non il n'y a pas de garantie formelle"*, *"Oui votre capital est garanti"*) ; (ii) pitching commercial sur le rendement dans une réponse risque/garantie interdit (*"le taux n'existe pas par hasard"*, *"moins d'intermédiaires, taux meilleur"*) ; (iii) énumération des "atténuations du risque" comme quasi-garanties interdite.

2. **bot.js — `<factual_discipline>` : nouveau bloc "Guarantee framing"** en 6 étapes obligatoires — (1) décliner le yes/no, (2) rappeler les 2 types d'offres (Cloud Mining vs prêt crypto), (3) engagement contractuel de restitution, (4) référer à la documentation spécifique, (5) **plafond absolu : aucune garantie ne couvre le défaut de contrepartie**, (6) close + redirect court.

3. **bot.js — nouvel `<example>` canonique** : question *"est-ce que mon argent est garanti sur les offres exclusives ?"* avec la structure correcte (5 paragraphes courts, plafond défaut contrepartie en gras).

4. **bot.js — `<editorial_method>` DEPTH CONTROL renforcé** : règle stricte de concision par défaut — target 3-6 paragraphes courts max, interdiction des sections non demandées ("atténuation", "pourquoi le taux", "pour aller plus loin"), narrative arc 6 étapes réservé aux questions produit/risque explicite, pas un template universel.

5. **bot.js — `<self_check>` point 10 ajouté** : LENGTH CHECK obligatoire avant d'envoyer — cette réponse peut-elle être raccourcie sans perdre le factuel ? Si oui, couper.

6. **Wiki — `guarantees-and-security-of-your-investment.md` (Bali)** : short_answer réécrit sans yes/no, nouvelle section en tête des Details *"Engagement mechanic and absolute limit"* posant le plafond défaut contrepartie. `last_reviewed: 2026-04-20`.

7. **Wiki — `guarantees-and-security-al-barari.md` (Dubai)** : short_answer réécrit sans yes/no, section *"No formal guarantee — but structured risk mitigation"* renommée et restructurée en *"Engagement mechanic and absolute limit"* posant le plafond explicite ; section "Residual risk" nettoyée de la rhétorique commerciale sur le taux. `last_reviewed: 2026-04-20`.

8. **Auto-memory** : nouvelle règle gravée *"Guarantee framing — no guarantee covers counterparty default"*.

Pattern à surveiller : toute réponse bot sur garantie/sécurité/protection qui ouvre par yes/no, qui empile des "atténuations" sans poser le plafond défaut contrepartie, ou qui pivote vers le pitch du rendement → candidat à reclassification.
