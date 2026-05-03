-- Offres Vault Builder : URL publique canonique /projects/[slug] (plus /[slug] seul).
UPDATE pages
SET url_path = '/projects/' || slug
WHERE template = 'vault_builder'
  AND slug <> 'home'
  AND url_path <> '/projects/' || slug;
