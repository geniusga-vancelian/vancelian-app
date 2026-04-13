ALTER TABLE "project_i18n"
ADD COLUMN IF NOT EXISTS "key_information" JSONB;

CREATE TABLE IF NOT EXISTS "key_information_categories" (
  "id" TEXT PRIMARY KEY,
  "key" TEXT NOT NULL UNIQUE,
  "label" TEXT NOT NULL,
  "info_title" TEXT,
  "info_content" TEXT,
  "sort_order" INTEGER NOT NULL DEFAULT 0,
  "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS "key_information_categories_sort_order_idx"
ON "key_information_categories"("sort_order");

INSERT INTO "key_information_categories" ("id", "key", "label", "sort_order")
VALUES
  ('kic_investissement_minimum', 'investissement_minimum', 'Investissement minimum', 10),
  ('kic_financement_total', 'financement_total', 'Financement total', 20),
  ('kic_rendement_annuel', 'rendement_annuel', 'Rendement annuel', 30),
  ('kic_fenetre_sortie', 'fenetre_sortie', 'Fenêtre de sortie', 40),
  ('kic_frais_sortie_6_mois', 'frais_sortie_6_mois', 'Frais de sortie à 6 mois', 50),
  ('kic_echeance_investissement', 'echeance_investissement', 'Échéance de l''investissement', 60),
  ('kic_frequence_paiement', 'frequence_paiement', 'Fréquence de paiement', 70),
  (
    'kic_bonus_surperformance',
    'bonus_surperformance',
    'Bonus de surperformance',
    80
  )
ON CONFLICT ("key") DO NOTHING;
