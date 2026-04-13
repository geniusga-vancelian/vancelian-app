-- =============================================================================
-- Backfill : persons.profile_json.collected.phone_e164  ←  admin_users.mobile_e164
-- =============================================================================
-- Contexte : comptes créés avant l’alignement login/signup ; collected vide
-- mais le mobile de connexion existe sur la ligne d’auth (voir
-- services/arquantix/CUSTOMER_CREATION_MODEL_AUDIT_REPORT.md).
--
-- Règles :
--   - Ne remplit QUE si collected.phone_e164 est absent ou vide (pas d’écrasement).
--   - Jointure stricte admin_users.person_id = persons.id.
--   - mobile_e164 admin non NULL et non vide après trim.
--
-- Ce fichier est volontairement **non destructif** : uniquement des SELECT.
-- Pour appliquer le backfill, utiliser le bloc commenté ci-dessous (décommenter
-- puis exécuter dans une session avec BEGIN/COMMIT) ou copier depuis le rapport.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1) PREVIEW — nombre de lignes qui seraient mises à jour
-- -----------------------------------------------------------------------------
SELECT COUNT(*) AS rows_to_update
FROM persons p
INNER JOIN admin_users u ON u.person_id = p.id
WHERE u.mobile_e164 IS NOT NULL
  AND trim(u.mobile_e164) <> ''
  AND (
    p.profile_json->'collected'->>'phone_e164' IS NULL
    OR trim(p.profile_json->'collected'->>'phone_e164') = ''
  );

-- -----------------------------------------------------------------------------
-- 2) PREVIEW — échantillon (id person, mobile auth, valeur collected actuelle)
-- -----------------------------------------------------------------------------
SELECT
  p.id AS person_id,
  trim(u.mobile_e164) AS admin_mobile_e164,
  p.profile_json->'collected'->>'phone_e164' AS collected_phone_before
FROM persons p
INNER JOIN admin_users u ON u.person_id = p.id
WHERE u.mobile_e164 IS NOT NULL
  AND trim(u.mobile_e164) <> ''
  AND (
    p.profile_json->'collected'->>'phone_e164' IS NULL
    OR trim(p.profile_json->'collected'->>'phone_e164') = ''
  )
ORDER BY p.updated_at DESC NULLS LAST
LIMIT 50;

-- -----------------------------------------------------------------------------
-- 3) UPDATE — décommenter et exécuter dans une transaction après backup
-- -----------------------------------------------------------------------------
/*
BEGIN;

UPDATE persons p
SET profile_json = jsonb_set(
  COALESCE(p.profile_json, '{}'::jsonb),
  '{collected,phone_e164}',
  to_jsonb(trim(both from u.mobile_e164::text)),
  true
)
FROM admin_users u
WHERE u.person_id = p.id
  AND u.mobile_e164 IS NOT NULL
  AND trim(u.mobile_e164) <> ''
  AND (
    p.profile_json->'collected'->>'phone_e164' IS NULL
    OR trim(p.profile_json->'collected'->>'phone_e164') = ''
  );

COMMIT;
*/

-- Filtres optionnels à ajouter au WHERE de l’UPDATE (cohorte « app » uniquement) :
--   AND COALESCE(u.mobile_app_allowed, true) = true
--   AND u.email ILIKE '%@signup.internal'

-- -----------------------------------------------------------------------------
-- 4) VÉRIFICATION POST-UPDATE — attendu : 0 pour la même cohorte que le backfill
-- -----------------------------------------------------------------------------
SELECT COUNT(*) AS remaining_gap_same_cohort
FROM persons p
INNER JOIN admin_users u ON u.person_id = p.id
WHERE u.mobile_e164 IS NOT NULL
  AND trim(u.mobile_e164) <> ''
  AND (
    p.profile_json->'collected'->>'phone_e164' IS NULL
    OR trim(p.profile_json->'collected'->>'phone_e164') = ''
  );
