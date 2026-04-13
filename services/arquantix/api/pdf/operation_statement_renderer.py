"""
Rendu HTML puis PDF (WeasyPrint) pour le relevé d’opération (pipeline ``operation_statement_*``).

Le HTML est produit via le gabarit autonome ``operation_statement.html`` (relevé unitaire, distinct du relevé IBAN).
Les styles passent par ``operation_statement.css`` (importe ``statement_common.css``, pas ``iban_statement.css``).
"""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

_PDF_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "pdf"


def get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_PDF_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_operation_statement_html(context: dict) -> str:
    """Contexte dict tel que retourné par ``custody_operation_payload_to_template_context``."""
    env = get_jinja_env()
    tpl = env.get_template("operation_statement.html")
    return tpl.render(**context)


def html_to_pdf_bytes(html_string: str, *, base_url: str | Path | None = None) -> bytes:
    """HTML complet → PDF avec ``operation_statement.css``."""
    css_path = _PDF_TEMPLATE_DIR / "operation_statement.css"
    html_template = _PDF_TEMPLATE_DIR / "operation_statement.html"
    logger.info(
        "operation_statement_pdf: render_assets template_dir=%s html_exists=%s css_exists=%s base_url=%s",
        _PDF_TEMPLATE_DIR,
        html_template.is_file(),
        css_path.is_file(),
        base_url or _PDF_TEMPLATE_DIR,
    )

    try:
        from weasyprint import CSS, HTML
    except (OSError, ImportError) as exc:
        logger.error(
            "operation_statement_pdf: weasyprint_import_failed exc_type=%s detail=%s",
            type(exc).__name__,
            str(exc)[:500],
        )
        raise

    if not css_path.is_file():
        logger.error("operation_statement_pdf: missing_css path=%s", css_path)
        raise FileNotFoundError(str(css_path))

    bu = str(base_url or _PDF_TEMPLATE_DIR)
    return HTML(string=html_string, base_url=bu).write_pdf(
        stylesheets=[CSS(filename=str(css_path))],
    )


def render_operation_statement_pdf(context: dict) -> bytes:
    html = render_operation_statement_html(context)
    return html_to_pdf_bytes(html)
