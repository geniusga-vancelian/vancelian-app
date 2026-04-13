#!/usr/bin/env python3
"""
Registration legacy normalization — dry-run, analysis, gated apply, post-verify.

Standard 4-step flow (see REGISTRATION_LEGACY_NORMALIZATION_RUNBOOK.md):

  1) Dry-run + JSON
     python3 scripts/run_registration_legacy_normalization.py \\
       --json-out /tmp/registration_legacy_dry_run.json

  2) Analyze
     python3 scripts/run_registration_legacy_normalization.py analyze /tmp/registration_legacy_dry_run.json

  3) Apply (after validation + explicit confirmation)
     python3 scripts/run_registration_legacy_normalization.py apply \\
       --pre-validate-json /tmp/registration_legacy_dry_run.json \\
       --snapshot-out /tmp/registration_legacy_snapshot.json \\
       --log-file /tmp/registration_legacy_apply.log \\
       --json-out /tmp/registration_legacy_apply.json

  4) Post-verify + delta
     python3 scripts/run_registration_legacy_normalization.py \\
       --json-out /tmp/registration_legacy_after.json
     python3 scripts/run_registration_legacy_normalization.py delta \\
       --before /tmp/registration_legacy_dry_run.json \\
       --after /tmp/registration_legacy_after.json \\
       --apply-json /tmp/registration_legacy_apply.json \\
       --write-summary REGISTRATION_LEGACY_NORMALIZATION_EXECUTION_SUMMARY.md
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(api_dir))

from services.portfolio_engine.clients.models import Client as _Client  # noqa: F401, E402 — mapper init

from database import SessionLocal  # noqa: E402

from services.registration.legacy_normalization import (  # noqa: E402
    apply_auto_fixes,
    diagnose_registration_components,
    result_to_dict,
)
from services.registration.legacy_normalization_analysis import (  # noqa: E402
    analyze_legacy_normalization_report,
    build_execution_summary_markdown,
    compute_post_apply_delta,
    format_console_analysis,
    format_post_apply_delta,
    format_validation_result,
    load_report,
    validate_safe_to_apply,
)


def _configure_apply_logging(log_path: Path | None) -> None:
    if not log_path:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root = logging.getLogger()
    root.addHandler(fh)
    root.setLevel(logging.INFO)
    logging.getLogger("services.registration.legacy_normalization").setLevel(logging.INFO)


def cmd_analyze(json_path: str) -> int:
    data = load_report(json_path)
    a = analyze_legacy_normalization_report(data)
    print(format_console_analysis(a))
    return 0


def cmd_validate(json_path: str, ns: argparse.Namespace) -> int:
    data = load_report(json_path)
    a = analyze_legacy_normalization_report(data)
    print(format_console_analysis(a))
    print()
    v = validate_safe_to_apply(
        a,
        max_ambiguous_pct=ns.max_ambiguous_pct,
        max_multiple_match_abs=ns.max_multiple_match_abs,
        max_multiple_match_pct_of_ambiguous=ns.max_multiple_match_pct_ambiguous,
        max_orphan_fd_abs=ns.max_orphan_fd_abs,
    )
    print(format_validation_result(v, a))
    return 0 if v.safe else 2


def cmd_delta(ns: argparse.Namespace) -> int:
    before = load_report(ns.before)
    after = load_report(ns.after)
    apply_data = load_report(ns.apply_json) if ns.apply_json else None
    delta = compute_post_apply_delta(before, after, apply_data)
    print(format_post_apply_delta(delta))
    if ns.write_summary:
        md = build_execution_summary_markdown(delta, before, after, apply_data)
        Path(ns.write_summary).write_text(md, encoding="utf-8")
        print(f"\nWrote summary: {ns.write_summary}")
    return 0


def cmd_apply(ns: argparse.Namespace) -> int:
    session = SessionLocal()
    try:
        if ns.pre_validate_json:
            dry_data = load_report(ns.pre_validate_json)
        else:
            res = apply_auto_fixes(session, dry_run=True)
            dry_data = result_to_dict(res)

        a = analyze_legacy_normalization_report(dry_data)
        v = validate_safe_to_apply(
            a,
            max_ambiguous_pct=ns.max_ambiguous_pct,
            max_multiple_match_abs=ns.max_multiple_match_abs,
            max_multiple_match_pct_of_ambiguous=ns.max_multiple_match_pct_ambiguous,
            max_orphan_fd_abs=ns.max_orphan_fd_abs,
        )

        print(format_console_analysis(a))
        print()
        print(format_validation_result(v, a))

        if not v.safe:
            print("\nApply aborted (validation failed).", file=sys.stderr)
            return 2

        if ns.snapshot_out:
            snap = {
                "source": "pre-apply snapshot of auto_fixable rows",
                "timestamp_utc": dry_data.get("timestamp_utc"),
                "auto_fixable": dry_data.get("auto_fixable"),
            }
            Path(ns.snapshot_out).write_text(
                json.dumps(snap, indent=2, default=str), encoding="utf-8"
            )
            print(f"\nSnapshot written: {ns.snapshot_out}")

        if not ns.yes:
            ans = input("\nApply auto-fixes? Type YES to continue: ").strip()
            if ans != "YES":
                print("Aborted (no changes committed).")
                return 3

        _configure_apply_logging(Path(ns.log_file) if ns.log_file else None)

        result = apply_auto_fixes(session, dry_run=False)
        payload = result_to_dict(result)
        text = json.dumps(payload, indent=2, default=str)
        print("\n--- Apply result ---")
        print(text)
        if ns.json_out:
            Path(ns.json_out).write_text(text, encoding="utf-8")

        if result.errors:
            return 1

        if ns.post_verify_json_out:
            session.expire_all()
            post = apply_auto_fixes(session, dry_run=True)
            post_d = result_to_dict(post)
            Path(ns.post_verify_json_out).write_text(
                json.dumps(post_d, indent=2, default=str), encoding="utf-8"
            )
            print(f"\nPost-verify dry-run written: {ns.post_verify_json_out}")
            cmp_before = dry_data
            delta = compute_post_apply_delta(cmp_before, post_d, payload)
            print()
            print(format_post_apply_delta(delta))

        return 0
    finally:
        session.close()


def cmd_run_legacy(ns: argparse.Namespace) -> int:
    """Original behaviour: dry-run, diagnose-only, or apply without validation gate."""
    session = SessionLocal()
    try:
        if ns.diagnose_only:
            result = diagnose_registration_components(session)
        elif ns.apply:
            if not ns.yes:
                print(
                    "Refused: bare --apply without safety gate. Use:\n"
                    "  ... apply --pre-validate-json <dry.json> [--yes]\n"
                    "Or pass --i-understand-unsafe-apply to force legacy direct apply.",
                    file=sys.stderr,
                )
                return 4
            result = apply_auto_fixes(session, dry_run=False)
        else:
            result = apply_auto_fixes(session, dry_run=True)
        payload = result_to_dict(result)
        text = json.dumps(payload, indent=2, default=str)
        print(text)
        if ns.json_out:
            Path(ns.json_out).write_text(text, encoding="utf-8")
        return 1 if result.errors else 0
    finally:
        session.close()


def main() -> int:
    argv = sys.argv[1:]
    if argv and argv[0] == "analyze":
        if len(argv) < 2:
            print("Usage: ... analyze <report.json>", file=sys.stderr)
            return 1
        return cmd_analyze(argv[1])

    if argv and argv[0] == "validate":
        p = argparse.ArgumentParser(prog="validate")
        p.add_argument("json_path")
        p.add_argument("--max-ambiguous-pct", type=float, default=10.0)
        p.add_argument("--max-multiple-match-abs", type=int, default=50)
        p.add_argument("--max-multiple-match-pct-ambiguous", type=float, default=30.0)
        p.add_argument("--max-orphan-fd-abs", type=int, default=100)
        ns, rest = p.parse_known_args(argv[1:])
        if rest:
            print(f"Unknown args: {rest}", file=sys.stderr)
            return 1
        return cmd_validate(ns.json_path, ns)

    if argv and argv[0] == "delta":
        p = argparse.ArgumentParser(prog="delta")
        p.add_argument("--before", required=True)
        p.add_argument("--after", required=True)
        p.add_argument("--apply-json", default=None)
        p.add_argument("--write-summary", default=None, metavar="PATH.md")
        ns, rest = p.parse_known_args(argv[1:])
        if rest:
            print(f"Unknown args: {rest}", file=sys.stderr)
            return 1
        return cmd_delta(ns)

    if argv and argv[0] == "apply":
        p = argparse.ArgumentParser(prog="apply")
        p.add_argument(
            "--pre-validate-json",
            required=True,
            help="Dry-run report JSON to validate before apply (required)",
        )
        p.add_argument("--snapshot-out", default=None)
        p.add_argument("--log-file", default=None)
        p.add_argument("--json-out", default=None)
        p.add_argument(
            "--yes",
            action="store_true",
            help="Skip interactive confirmation (use only in CI or automation)",
        )
        p.add_argument(
            "--post-verify-json-out",
            default=None,
            help="After successful apply, run dry-run again and write JSON + print delta",
        )
        p.add_argument("--max-ambiguous-pct", type=float, default=10.0)
        p.add_argument("--max-multiple-match-abs", type=int, default=50)
        p.add_argument("--max-multiple-match-pct-ambiguous", type=float, default=30.0)
        p.add_argument("--max-orphan-fd-abs", type=int, default=100)
        ns, rest = p.parse_known_args(argv[1:])
        if rest:
            print(f"Unknown args: {rest}", file=sys.stderr)
            return 1
        return cmd_apply(ns)

    # Legacy CLI
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="UNSAFE unless --yes: use `apply` subcommand instead",
    )
    parser.add_argument(
        "--i-understand-unsafe-apply",
        action="store_true",
        help="Allow direct --apply without pre-validation (legacy / emergencies)",
    )
    parser.add_argument("--yes", action="store_true", help="With unsafe --apply only")
    parser.add_argument(
        "--diagnose-only",
        action="store_true",
        help="Faster report using diagnose only",
    )
    parser.add_argument("--json-out", metavar="PATH", default=None)
    ns = parser.parse_args(argv)

    if ns.apply and not ns.i_understand_unsafe_apply:
        print(
            "Direct --apply is disabled by default. Use:\n"
            "  python3 scripts/run_registration_legacy_normalization.py apply "
            "--pre-validate-json <dry.json>\n"
            "Or pass --i-understand-unsafe-apply --yes for emergency legacy apply.",
            file=sys.stderr,
        )
        return 4

    if ns.apply and ns.i_understand_unsafe_apply and not ns.yes:
        print(
            "Refused: add --yes to confirm unsafe direct apply.",
            file=sys.stderr,
        )
        return 4

    return cmd_run_legacy(ns)


if __name__ == "__main__":
    raise SystemExit(main())
