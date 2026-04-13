#!/usr/bin/env python3
"""
Fusion contrôlée arquantix_quant + arquantix_admin → une base unique (ex. arquantix).

Prérequis :
  - PostgreSQL client tools : pg_dump, pg_restore, psql, créés (createdb) sur le serveur.
  - Sur la base SOURCE quant : Alembic à jour jusqu’à la migration 105
    (renommage `pages` → `legacy_json_pages` pour éviter collision Prisma).
  - Sauvegardes : pg_dump des deux bases AVANT exécution (voir --print-backup-commands).

Usage :
  python3 scripts/db_merge_quant_admin.py --dry-run \\
    --quant-url "postgresql://u:p@localhost:5443/arquantix_quant" \\
    --admin-url "postgresql://u:p@localhost:5443/arquantix_admin" \\
    --target-name arquantix \\
    --superuser-url "postgresql://postgres:...@localhost:5443/postgres"

  # Puis sans --dry-run quand le plan est validé.

Rollback : restaurer les dumps pris avant fusion ; repointer les .env vers les anciennes bases.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urlparse

try:
    import psycopg2
    from psycopg2.extensions import connection as PgConnection
except ImportError:
    psycopg2 = None  # type: ignore
    PgConnection = None  # type: ignore

# Tables présentes côté Alembic (cc6123) ET Prisma : la donnée CMS (admin) fait foi.
OVERLAP_ADMIN_WINS: Tuple[str, ...] = (
    "email_modules",
    "email_module_i18n",
    "email_template_entities",
)

SKIP_ON_ADMIN_COPY: Set[str] = set()  # reserved


@dataclass
class DsnParts:
    scheme: str
    netloc: str
    user: str
    password: str
    host: str
    port: int
    database: str

    @property
    def for_psql(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


def parse_pg_url(url: str) -> DsnParts:
    u = url.strip().strip('"').strip("'")
    for pfx in ("postgresql+asyncpg://", "postgres://"):
        if u.startswith(pfx):
            u = "postgresql://" + u.split("://", 1)[1]
            break
    parsed = urlparse(u)
    if parsed.scheme not in ("postgresql", "postgres"):
        raise ValueError(f"URL PostgreSQL attendue, reçu: {parsed.scheme!r}")
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    user = parsed.username or ""
    password = parsed.password or ""
    db = (parsed.path or "").lstrip("/").split("?")[0]
    if not db:
        raise ValueError("Nom de base manquant dans l’URL")
    return DsnParts(
        scheme="postgresql",
        netloc=f"{host}:{port}",
        user=user,
        password=password,
        host=host,
        port=port,
        database=db,
    )


def require_tools() -> None:
    for b in ("pg_dump", "pg_restore", "psql", "createdb"):
        if not shutil.which(b):
            raise SystemExit(f"Outil manquant dans le PATH : {b}")


def connect(url: str):
    if not psycopg2:
        raise SystemExit("psycopg2 requis : pip install psycopg2-binary (depuis api/)")
    return psycopg2.connect(url)


def list_public_tables(conn) -> Set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public' AND tablename NOT LIKE 'pg_%'
            ORDER BY tablename
            """
        )
        return {r[0] for r in cur.fetchall()}


def fk_edges(conn, tables: Set[str]) -> List[Tuple[str, str]]:
    """Arête (child, parent) : child dépend de parent (FK vers parent)."""
    if not tables:
        return []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.conrelid::regclass::text, c.confrelid::regclass::text
            FROM pg_constraint c
            JOIN pg_namespace n ON n.oid = c.connamespace
            WHERE c.contype = 'f' AND n.nspname = 'public'
            """
        )
        edges: List[Tuple[str, str]] = []
        for child_full, parent_full in cur.fetchall():
            child = child_full.split(".")[-1].strip('"')
            parent = parent_full.split(".")[-1].strip('"')
            if child in tables and parent in tables:
                edges.append((child, parent))
        return edges


def topological_sort_tables(tables: Set[str], edges: List[Tuple[str, str]]) -> List[str]:
    """Ordre tel que pour chaque arête (c,p), p apparaît avant c (parents d’abord pour CREATE ; inverse pour TRUNCATE data child-first)."""
    children: Dict[str, Set[str]] = defaultdict(set)
    parents: Dict[str, Set[str]] = defaultdict(set)
    for c, p in edges:
        children[p].add(c)
        parents[c].add(p)
    # Parents avant enfants : Kahn sur reversed graph (in-degree = nombre de parents pour un nœud = table)
    in_degree: Dict[str, int] = {t: len(parents[t]) for t in tables}
    q = deque(sorted(t for t in tables if in_degree[t] == 0))
    out: List[str] = []
    while q:
        t = q.popleft()
        out.append(t)
        for ch in sorted(children[t]):
            in_degree[ch] -= 1
            if in_degree[ch] == 0:
                q.append(ch)
    if len(out) != len(tables):
        remaining = tables - set(out)
        raise RuntimeError(f"Cycle ou graphe incomplet dans les FK : {remaining}")
    return out


def data_load_order(tables: Set[str], edges: List[Tuple[str, str]]) -> List[str]:
    """Pour INSERT : enfants après parents → ordre inverse de topological_sort_tables (parents first)."""
    parents_first = topological_sort_tables(tables, edges)
    return parents_first


def run_cmd(args: List[str], dry_run: bool) -> None:
    print("+", " ".join(args))
    if dry_run:
        return
    subprocess.check_call(args)


def ensure_target_database(super_dsn: DsnParts, target_name: str, dry_run: bool) -> None:
    """Crée la base cible si absente (connexion sur postgres)."""
    admin_url = f"postgresql://{super_dsn.user}:{super_dsn.password}@{super_dsn.host}:{super_dsn.port}/postgres"
    conn = connect(admin_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (target_name,),
            )
            if cur.fetchone():
                print(f"Base cible {target_name!r} existe déjà.")
                return
        cmd = [
            "createdb",
            "-h",
            super_dsn.host,
            "-p",
            str(super_dsn.port),
            "-U",
            super_dsn.user,
            target_name,
        ]
        env = os.environ.copy()
        env["PGPASSWORD"] = super_dsn.password
        print("+", " ".join(cmd))
        if dry_run:
            return
        subprocess.check_call(cmd, env=env)
    finally:
        conn.close()


def dump_restore_quant(quant_url: str, target_url: str, dump_path: str, dry_run: bool) -> None:
    run_cmd(["pg_dump", "--no-owner", "--no-acl", "-Fc", "-f", dump_path, quant_url], dry_run)
    if dry_run:
        return
    run_cmd(["pg_restore", "--no-owner", "--no-acl", "-d", target_url, "--verbose", dump_path], dry_run)


def pg_dump_schema_table(source_url: str, table: str, dry_run: bool) -> Optional[str]:
    fd, path = tempfile.mkstemp(suffix=".sql")
    os.close(fd)
    cmd = [
        "pg_dump",
        source_url,
        "--schema-only",
        "--no-owner",
        "--no-acl",
        "-f",
        path,
        "-t",
        f"public.{table}",
    ]
    print("+", " ".join(cmd))
    if dry_run:
        os.unlink(path)
        return None
    subprocess.check_call(cmd)
    return path


def pg_dump_data_table(source_url: str, table: str, out_sql: str, dry_run: bool) -> None:
    cmd = [
        "pg_dump",
        source_url,
        "--data-only",
        "--no-owner",
        "--no-acl",
        "--disable-triggers",
        "-f",
        out_sql,
        "-t",
        f"public.{table}",
    ]
    run_cmd(cmd, dry_run)


def psql_file(target_url: str, sql_path: str, dry_run: bool) -> None:
    cmd = ["psql", target_url, "-v", "ON_ERROR_STOP=1", "-f", sql_path]
    run_cmd(cmd, dry_run)


def truncate_overlap(target_url: str, tables: List[str], dry_run: bool) -> None:
    """TRUNCATE ... CASCADE dans l’ordre enfants → parents."""
    if not tables:
        return
    conn = connect(target_url)
    try:
        edges = fk_edges(conn, set(tables))
        # data delete order: children first
        rev = list(reversed(topological_sort_tables(set(tables), edges)))
        stmt = "TRUNCATE TABLE " + ", ".join(f'public."{t}"' for t in rev) + " CASCADE;"
        print("SQL:", stmt)
        if dry_run:
            return
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(stmt)
    finally:
        conn.close()


def print_backup_commands(quant: str, admin: str) -> None:
    print("\n--- Commandes de sauvegarde recommandées (exécuter AVANT fusion) ---\n")
    print(f'pg_dump --no-owner --no-acl -Fc -f backup_quant.dump "{quant}"')
    print(f'pg_dump --no-owner --no-acl -Fc -f backup_admin.dump "{admin}"')
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Fusion arquantix_quant + arquantix_admin → arquantix")
    parser.add_argument("--quant-url", required=True, help="URL base source métier (quant)")
    parser.add_argument("--admin-url", required=True, help="URL base source CMS (admin / Prisma)")
    parser.add_argument("--target-name", default="arquantix", help="Nom de la base cible")
    parser.add_argument(
        "--superuser-url",
        help="URL vers la base postgres (création DB). Ex: postgresql://postgres:pw@host:5443/postgres",
    )
    parser.add_argument("--dry-run", action="store_true", help="Affiche les étapes sans les exécuter")
    parser.add_argument(
        "--skip-quant-restore",
        action="store_true",
        help="Ne pas restaurer quant (cible déjà peuplée depuis quant)",
    )
    parser.add_argument("--print-backup-commands", action="store_true", help="Affiche les pg_dump de backup et quitte")
    args = parser.parse_args()

    if args.print_backup_commands:
        print_backup_commands(args.quant_url, args.admin_url)
        return 0

    require_tools()
    quant = parse_pg_url(args.quant_url)
    admin = parse_pg_url(args.admin_url)
    target_name = args.target_name

    if quant.database == target_name or admin.database == target_name:
        print("ERREUR: la base cible doit être distincte des sources.", file=sys.stderr)
        return 1

    super_dsn: Optional[DsnParts] = parse_pg_url(args.superuser_url) if args.superuser_url else None

    target_url = f"postgresql://{quant.user}:{quant.password}@{quant.host}:{quant.port}/{target_name}"

    print("=" * 72)
    print("PLAN DE FUSION")
    print(f"  quant  : {quant.host}:{quant.port}/{quant.database}")
    print(f"  admin  : {admin.host}:{admin.port}/{admin.database}")
    print(f"  cible  : {quant.host}:{quant.port}/{target_name}")
    print(f"  dry_run: {args.dry_run}")
    print("=" * 72)
    print_backup_commands(args.quant_url, args.admin_url)

    if super_dsn:
        ensure_target_database(super_dsn, target_name, args.dry_run)
    else:
        print("(!) Pas de --superuser-url : la base cible doit exister (createdb manuel).")

    tmpdir = tempfile.mkdtemp(prefix="arquantix_merge_")
    quant_dump = os.path.join(tmpdir, "quant.dump")

    try:
        if not args.skip_quant_restore:
            print("\n--- Étape 1 : pg_dump quant → restore cible ---\n")
            dump_restore_quant(args.quant_url, target_url, quant_dump, args.dry_run)
        else:
            print("\n--- Étape 1 : ignorée (--skip-quant-restore) ---\n")

        if args.dry_run:
            print("\n--- Étape 2–4 : analyse des tables (nécessite connexion réelle) — ignoré en dry-run ---\n")
            return 0

        a_conn = connect(args.admin_url)
        t_conn = connect(target_url)
        try:
            admin_tables = list_public_tables(a_conn)
            target_tables = list_public_tables(t_conn)
        finally:
            a_conn.close()
            t_conn.close()

        missing_on_target = admin_tables - target_tables
        overlap = set(OVERLAP_ADMIN_WINS) & target_tables & admin_tables

        print("\n--- Tables admin absentes de la cible (DDL + données) ---")
        for t in sorted(missing_on_target):
            print(f"  + {t}")

        print("\n--- Recouvrement (données admin prioritaires) ---")
        for t in sorted(overlap):
            print(f"  ~ {t}")

        # DDL pour tables manquantes
        print("\n--- Étape 2 : schéma des tables manquantes ---\n")
        a2 = connect(args.admin_url)
        try:
            edges_missing = fk_edges(a2, missing_on_target)
        finally:
            a2.close()

        order_create = topological_sort_tables(missing_on_target, edges_missing)
        for tbl in order_create:
            if tbl in SKIP_ON_ADMIN_COPY:
                continue
            path = pg_dump_schema_table(args.admin_url, tbl, args.dry_run)
            if path:
                try:
                    psql_file(target_url, path, False)
                finally:
                    os.unlink(path)

        # Overlap : truncate + data (admin gagne)
        print("\n--- Étape 3 : recouvrement (TRUNCATE + données admin) ---\n")
        if overlap:
            truncate_overlap(target_url, sorted(overlap), args.dry_run)
            a3 = connect(args.admin_url)
            try:
                oe = fk_edges(a3, overlap)
                overlap_data_order = data_load_order(overlap, oe)
            finally:
                a3.close()
            for tbl in overlap_data_order:
                fsql = os.path.join(tmpdir, f"data_overlap_{tbl}.sql")
                pg_dump_data_table(args.admin_url, tbl, fsql, False)
                psql_file(target_url, fsql, False)
                if os.path.exists(fsql):
                    os.unlink(fsql)

        # Données : tables créées à l’étape 2 (admin-only sur la cible)
        print("\n--- Étape 4 : données des tables nouvellement créées ---\n")
        a4 = connect(args.admin_url)
        try:
            re = fk_edges(a4, missing_on_target)
            data_order = data_load_order(missing_on_target, re)
        finally:
            a4.close()

        for tbl in data_order:
            if tbl in SKIP_ON_ADMIN_COPY:
                continue
            fsql = os.path.join(tmpdir, f"data_new_{tbl}.sql")
            pg_dump_data_table(args.admin_url, tbl, fsql, False)
            psql_file(target_url, fsql, False)
            if os.path.exists(fsql):
                os.unlink(fsql)

        print("\n--- Terminé. Étapes manuelles : ---")
        print("  1. Pointer api/.env* et web/.env* vers DATABASE_URL=.../" + target_name)
        print("  2. cd api && alembic current  (doit afficher 105 ou tête)")
        print("  3. cd web && npx prisma migrate status")
        print("  4. make doctor-db  (API et Web même base)")
    finally:
        if os.path.exists(quant_dump):
            os.unlink(quant_dump)
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
