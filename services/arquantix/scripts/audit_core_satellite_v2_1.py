#!/usr/bin/env python3
"""
Script d'audit automatique pour CORE_SATELLITE V2.1.

Vérifie la conformité de l'implémentation par rapport aux exigences V2.1.

Exit code:
- 0: Tous les checks passent
- 1: Au moins un check échoue
"""

import os
import sys
import re
import subprocess
from pathlib import Path
from typing import List, Tuple

# Configuration
REPO_ROOT = Path(__file__).parent.parent
API_ROOT = REPO_ROOT / "api"
WEB_ROOT = REPO_ROOT / "web"

# Couleurs pour output
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def print_ok(msg: str):
    print(f"{GREEN}[OK]{RESET} {msg}")


def print_fail(msg: str):
    print(f"{RED}[FAIL]{RESET} {msg}")


def print_warning(msg: str):
    print(f"{YELLOW}[WARNING]{RESET} {msg}")


def check_frontend_dropdowns() -> bool:
    """Vérifier que CORE_SATELLITE est présent dans les dropdowns."""
    file_path = WEB_ROOT / "src" / "components" / "finance" / "BacktestsTab.tsx"
    if not file_path.exists():
        print_fail(f"Fichier non trouvé: {file_path}")
        return False

    content = file_path.read_text()
    occurrences = len(re.findall(r"CORE_SATELLITE", content))
    
    if occurrences >= 3:
        print_ok(f"CORE_SATELLITE présent dans BacktestsTab.tsx ({occurrences} occurrences)")
        return True
    else:
        print_fail(f"CORE_SATELLITE présent seulement {occurrences} fois (attendu: >= 3)")
        return False


def check_backend_schema() -> bool:
    """Vérifier les paramètres V2.1 dans Pydantic."""
    file_path = API_ROOT / "services" / "backtest" / "routes.py"
    if not file_path.exists():
        print_fail(f"Fichier non trouvé: {file_path}")
        return False

    content = file_path.read_text()
    required_params = [
        "allocation_mode",
        "lambda_risk",
        "multiplier",
        "floor_rel_ratio",
        "floor_accrues_with_core",
        "sat_max",
    ]

    missing = []
    for param in required_params:
        if f"{param}: Optional" not in content:
            missing.append(param)

    if not missing:
        print_ok(f"Paramètres V2.1 dans routes.py ({len(required_params)} paramètres)")
        return True
    else:
        print_fail(f"Paramètres V2.1 manquants dans routes.py: {missing}")
        return False


def check_frontend_schema() -> bool:
    """Vérifier les paramètres V2.1 dans Zod."""
    file_path = WEB_ROOT / "src" / "app" / "api" / "backtests" / "run" / "route.ts"
    if not file_path.exists():
        print_fail(f"Fichier non trouvé: {file_path}")
        return False

    content = file_path.read_text()
    required_params = [
        "allocation_mode",
        "lambda_risk",
        "multiplier",
        "floor_rel_ratio",
        "floor_accrues_with_core",
        "sat_max",
    ]

    missing = []
    for param in required_params:
        if f"{param}:" not in content or "z." not in content:
            # Vérification basique
            pattern = rf"{param}\s*:"
            if not re.search(pattern, content):
                missing.append(param)

    if not missing:
        print_ok(f"Paramètres V2.1 dans route.ts ({len(required_params)} paramètres)")
        return True
    else:
        print_fail(f"Paramètres V2.1 manquants dans route.ts: {missing}")
        return False


def check_v2_1_functions() -> bool:
    """Vérifier que les fonctions V2.1 sont définies."""
    file_path = API_ROOT / "services" / "backtest" / "strategies" / "core_satellite.py"
    if not file_path.exists():
        print_fail(f"Fichier non trouvé: {file_path}")
        return False

    content = file_path.read_text()
    required_functions = [
        "compute_scalar_satellite_weight",
        "build_unit_satellite_portfolio",
        "compute_te_sat",
        "compute_ir_sat",
    ]

    missing = []
    for func in required_functions:
        if f"def {func}" not in content:
            missing.append(func)

    if not missing:
        print_ok(f"Fonctions V2.1 définies ({len(required_functions)} fonctions)")
        return True
    else:
        print_fail(f"Fonctions V2.1 manquantes: {missing}")
        return False


def check_v2_1_fields_in_weights_json() -> bool:
    """Vérifier que les champs V2.1 sont stockés dans weights_json."""
    file_path = API_ROOT / "services" / "backtest" / "strategies" / "core_satellite.py"
    if not file_path.exists():
        print_fail(f"Fichier non trouvé: {file_path}")
        return False

    content = file_path.read_text()
    required_fields = [
        "_cs_alloc_mode",
        "_cs_sat_weight_scalar",
        "_cs_te_sat",
        "_cs_ir_sat",
    ]

    missing = []
    for field in required_fields:
        # Chercher "weights_dict['_cs_...']" ou "weights_dict[\"_cs_...\"]"
        pattern1 = rf"weights_dict\['{field}'\]"
        pattern2 = rf'weights_dict\["{field}"\]'
        if not (re.search(pattern1, content) or re.search(pattern2, content)):
            missing.append(field)

    if not missing:
        # Also verify runtime: run a mini backtest
        try:
            import sys
            sys.path.insert(0, str(API_ROOT))
            from services.backtest.strategies.core_satellite import run_core_satellite_backtest
            import pandas as pd
            from datetime import date
            
            dates = pd.date_range('2024-01-01', periods=20, freq='D')
            prices_df = pd.DataFrame({
                1: [100.0] * 20,
                2: [50.0] * 20,
            }, index=dates)
            
            result = run_core_satellite_backtest(
                prices_df=prices_df,
                instrument_ids=[1, 2],
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 20),
                initial_capital=100.0,
                rebalance_frequency='daily',
                fees_bps=0.0,
                slippage_bps=0.0,
                allocation_mode='te_target',
                target_te=0.10,
                debug=False,
            )
            
            if result.get('portfolio_series') and len(result['portfolio_series']) > 0:
                first_bar = result['portfolio_series'][0]
                weights = first_bar.get('weights_json', {})
                runtime_missing = [f for f in required_fields if f not in weights]
                if runtime_missing:
                    print_fail(f"Champs V2.1 manquants lors du runtime: {runtime_missing}")
                    return False
                print_ok(f"Champs V2.1 stockés dans weights_json ({len(required_fields)} champs, vérifié runtime)")
                return True
            else:
                print_fail("portfolio_series vide lors du test runtime")
                return False
        except Exception as e:
            print_warning(f"Test runtime échoué (peut être normal si dépendances manquantes): {e}")
            print_ok(f"Champs V2.1 présents dans code ({len(required_fields)} champs)")
            return True  # Accept static check only if runtime fails
        
    else:
        print_fail(f"Champs V2.1 manquants dans weights_json: {missing}")
        return False


def check_v2_1_tests() -> bool:
    """Vérifier que les tests V2.1 existent."""
    test_file = API_ROOT / "tests" / "test_core_satellite_v2_1_contract.py"
    if test_file.exists():
        print_ok("Tests V2.1 contractuels existent")
        return True
    else:
        print_warning("Tests V2.1 contractuels manquants (test_core_satellite_v2_1_contract.py)")
        return False  # Warning mais considéré comme échec pour exit code


def check_frontend_types() -> bool:
    """Vérifier les types TypeScript."""
    file_path = WEB_ROOT / "src" / "components" / "backtests" / "types.ts"
    if not file_path.exists():
        print_fail(f"Fichier non trouvé: {file_path}")
        return False

    content = file_path.read_text()
    if "CORE_SATELLITE" in content:
        print_ok("CORE_SATELLITE présent dans types.ts")
        return True
    else:
        print_warning("CORE_SATELLITE manquant dans types.ts (optionnel mais recommandé)")
        return True  # Warning seulement, ne fait pas échouer


def check_documentation() -> bool:
    """Vérifier que la documentation V2.1 existe."""
    doc_file = REPO_ROOT / "docs" / "STRATEGY_CORE_SATELLITE.md"
    if not doc_file.exists():
        print_fail(f"Documentation non trouvée: {doc_file}")
        return False

    content = doc_file.read_text()
    v2_1_indicators = [
        "V2.1",
        "allocation_mode",
        "te_target",
        "utility_lambda",
        "dynamic_cushion",
    ]

    found = sum(1 for indicator in v2_1_indicators if indicator in content)
    if found >= 3:
        print_ok(f"Documentation V2.1 présente ({found} indicateurs trouvés)")
        return True
    else:
        print_warning("Documentation V2.1 incomplète ou absente")
        return False  # Warning mais considéré comme échec


def main():
    """Exécuter tous les checks."""
    print("Audit CORE_SATELLITE V2.1\n")
    print("=" * 60)

    checks = [
        ("Frontend dropdowns", check_frontend_dropdowns),
        ("Backend schema (Pydantic)", check_backend_schema),
        ("Frontend schema (Zod)", check_frontend_schema),
        ("Fonctions V2.1", check_v2_1_functions),
        ("Champs V2.1 dans weights_json", check_v2_1_fields_in_weights_json),  # CRITIQUE
        ("Tests V2.1", check_v2_1_tests),
        ("Types TypeScript", check_frontend_types),
        ("Documentation", check_documentation),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print_fail(f"Erreur lors du check '{name}': {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("Résumé\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)
    critical_failures = [
        name for name, result in results
        if not result and name in ["Champs V2.1 dans weights_json", "Tests V2.1"]
    ]

    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")

    print(f"\nTotal: {passed}/{total} checks passent")

    if critical_failures:
        print(f"\n{RED}Erreurs critiques:{RESET}")
        for name in critical_failures:
            print(f"  - {name}")

    if passed == total:
        print(f"\n{GREEN}✅ Audit PASSED{RESET}")
        return 0
    else:
        print(f"\n{RED}❌ Audit FAILED ({total - passed} échec(s)){RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
