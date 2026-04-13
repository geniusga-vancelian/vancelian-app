/**
 * Affiche host/port/database pour Prisma.
 * Résolution : $DATABASE_URL (shell) sinon web/.env.local sinon web/.env (aligné sur Next.js).
 */
import { existsSync, readFileSync } from "fs";
import { join } from "path";

function parseDatabaseUrlFromFile(path: string): string | undefined {
  if (!existsSync(path)) return undefined;
  const text = readFileSync(path, "utf8");
  for (const line of text.split("\n")) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const m = t.match(/^DATABASE_URL\s*=\s*(.*)$/);
    if (!m) continue;
    let v = m[1].trim();
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
      v = v.slice(1, -1);
    }
    return v;
  }
  return undefined;
}

function mask(url: string): string {
  if (!url.includes("@")) return url;
  try {
    const u = new URL(url.replace(/^postgresql\+asyncpg:\/\//, "postgresql://"));
    const user = u.username || "";
    if (u.password) {
      return url.replace(`${user}:${u.password}@`, `${user}:***@`);
    }
  } catch {
    /* ignore */
  }
  return url.replace(/:([^:@/]+)@/, ":***@");
}

const root = process.cwd();
const fromEnv = process.env.DATABASE_URL;
const fromDotEnv = parseDatabaseUrlFromFile(join(root, ".env"));
const fromLocal = parseDatabaseUrlFromFile(join(root, ".env.local"));
// Next.js : .env.local surcharge .env pour une clé donnée seulement si elle est définie dans .env.local
const fromFiles =
  fromLocal !== undefined ? fromLocal : fromDotEnv !== undefined ? fromDotEnv : undefined;
const effective = fromEnv ?? fromFiles;

if (!effective) {
  console.log("[Prisma/Web] DATABASE_URL: (non défini — ni shell ni web/.env ni web/.env.local)");
  process.exit(1);
}

let host: string | null = null;
let port = "5432";
let database: string | null = null;
try {
  const normalized = effective.replace(/^postgresql\+asyncpg:\/\//, "postgresql://");
  const u = new URL(normalized);
  host = u.hostname;
  if (u.port) port = u.port;
  database = u.pathname.replace(/^\//, "").split("?")[0] || null;
} catch {
  console.log("[Prisma/Web] DATABASE_URL: (parse error)");
  console.log(`  raw (masked): ${mask(effective)}`);
  process.exit(1);
}

console.log(
  `[Prisma/Web] host=${host} port=${port} database=${database} url=${mask(effective)}`
);
