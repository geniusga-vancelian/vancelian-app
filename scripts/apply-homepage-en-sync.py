import json
import os
import subprocess
import sys
import urllib.request

url = os.environ["SYNC_JSON_URL"]
db = os.environ["DATABASE_URL"]
path = "/tmp/homepage-en-sync.json"
urllib.request.urlretrieve(url, path)
with open(path) as f:
    payload = json.load(f)


def psql(sql: str) -> None:
    subprocess.check_call(["psql", db, "-v", "ON_ERROR_STOP=1", "-c", sql])


def esc(v) -> str:
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


for m in payload.get("media", []):
    psql(
        f"""
    INSERT INTO media (id, key, url, filename, mime_type, size, width, height, alt, created_at)
    VALUES ({esc(m['id'])}, {esc(m['key'])}, {esc(m['url'])}, {esc(m['filename'])}, {esc(m['mimeType'])},
            {m.get('size') if m.get('size') is not None else 'NULL'},
            {m.get('width') if m.get('width') is not None else 'NULL'},
            {m.get('height') if m.get('height') is not None else 'NULL'},
            {esc(m.get('alt'))}, NOW())
    ON CONFLICT (id) DO UPDATE SET
      key = EXCLUDED.key, url = EXCLUDED.url, filename = EXCLUDED.filename,
      mime_type = EXCLUDED.mime_type, size = EXCLUDED.size,
      width = EXCLUDED.width, height = EXCLUDED.height, alt = EXCLUDED.alt;
    """
    )

locale = payload["locale"]
page_slug = payload["pageSlug"].replace("'", "''")

for sec in payload.get("sections", []):
    data_json = json.dumps(sec["data"], ensure_ascii=False).replace("'", "''")
    key = sec["key"].replace("'", "''")
    for status in ("PUBLISHED", "DRAFT"):
        psql(
            f"""
        UPDATE section_contents sc
        SET data = '{data_json}'::jsonb, updated_at = NOW()
        FROM sections s, pages p
        WHERE sc.section_id = s.id AND s.page_id = p.id
          AND p.slug = '{page_slug}' AND s.key = '{key}'
          AND sc.locale = '{locale}' AND sc.status = '{status}';
        """
        )
        psql(
            f"""
        INSERT INTO section_contents (id, section_id, locale, status, data, updated_at, translation_status)
        SELECT md5(random()::text || clock_timestamp()::text), s.id, '{locale}', '{status}', '{data_json}'::jsonb, NOW(), 'ORIGINAL'
        FROM sections s JOIN pages p ON p.id = s.page_id
        WHERE p.slug = '{page_slug}' AND s.key = '{key}'
          AND NOT EXISTS (
            SELECT 1 FROM section_contents sc2
            WHERE sc2.section_id = s.id AND sc2.locale = '{locale}' AND sc2.status = '{status}'
          );
        """
        )

pi = payload.get("pageI18n")
if pi:
    title = (pi.get("title") or "").replace("'", "''")
    desc = (pi.get("description") or "").replace("'", "''")
    og_t = (pi.get("ogTitle") or "").replace("'", "''")
    og_d = (pi.get("ogDescription") or "").replace("'", "''")
    psql(
        f"""
    INSERT INTO page_i18n (id, page_id, locale, title, description, og_title, og_description)
    SELECT md5(random()::text || clock_timestamp()::text), p.id, '{locale}', '{title}', '{desc}', NULLIF('{og_t}',''), NULLIF('{og_d}','')
    FROM pages p WHERE p.slug = '{page_slug}'
    ON CONFLICT (page_id, locale) DO UPDATE SET
      title = EXCLUDED.title, description = EXCLUDED.description,
      og_title = EXCLUDED.og_title, og_description = EXCLUDED.og_description;
    """
    )

print("Homepage EN sync OK", flush=True)
