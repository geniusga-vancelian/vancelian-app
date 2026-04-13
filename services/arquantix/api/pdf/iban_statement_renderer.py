"""
Rendu HTML puis PDF (WeasyPrint) pour le relevé IBAN.

Mapping Flutter → blocs HTML (référence) :
  StatementHeader      → en-tête running (logo + titre) + section page 1 (deux cartes)
  StatementMetaSection → <h2 class="statement__meta">
  BalanceSummaryCard   → <section class="balance-summary">
  TransactionsTable    → <section class="operations"> + <table class="statement-table">
  StatementFooter      → <footer class="statement__footer"> (en tête du body pour running PDF)

Usage (FastAPI / tâche async) :
  html = render_iban_statement_html(context)
  pdf_bytes = html_to_pdf_bytes(html)
"""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

# Répertoire des templates PDF (sibling de ce package : api/templates/pdf)
_PDF_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "pdf"


def get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_PDF_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_iban_statement_html(context: dict) -> str:
    """Contexte dict tel que retourné par `iban_statement_mapper.payload_to_template_context`."""
    env = get_jinja_env()
    tpl = env.get_template("iban_statement.html")  # inclut Statement.html (gabarit PDF unifié)
    return tpl.render(**context)


def html_to_pdf_bytes(
    html_string: str,
    *,
    base_url: str | Path | None = None,
) -> bytes:
    """
    HTML complet → PDF. `base_url` doit pointer vers le dossier contenant le CSS
    (résolution du <link href="iban_statement.css">).
    """
    css_path = _PDF_TEMPLATE_DIR / "iban_statement.css"
    html_template = _PDF_TEMPLATE_DIR / "iban_statement.html"
    logger.info(
        "iban_statement_pdf: render_assets template_dir=%s html_exists=%s css_exists=%s base_url=%s",
        _PDF_TEMPLATE_DIR,
        html_template.is_file(),
        css_path.is_file(),
        base_url or _PDF_TEMPLATE_DIR,
    )

    try:
        from weasyprint import CSS, HTML
    except (OSError, ImportError) as exc:
        # Souvent dlopen (libs natives) ou environnement Python cassé — avant tout accès disque CSS.
        logger.error(
            "iban_statement_pdf: weasyprint_import_failed exc_type=%s detail=%s",
            type(exc).__name__,
            str(exc)[:500],
        )
        raise

    if not css_path.is_file():
        logger.error("iban_statement_pdf: missing_css path=%s", css_path)
        raise FileNotFoundError(str(css_path))

    bu = str(base_url or _PDF_TEMPLATE_DIR)
    return HTML(string=html_string, base_url=bu).write_pdf(
        stylesheets=[CSS(filename=str(css_path))],
    )


def render_iban_statement_pdf(context: dict) -> bytes:
    """Pipeline complet : même contexte Jinja que pour le HTML."""
    html = render_iban_statement_html(context)
    return html_to_pdf_bytes(html)
