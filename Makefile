# Point d'entrée minimal à la racine du dépôt (aligné sur l'ancien flux OneDrive).
# La logique détaillée vit dans services/arquantix/scripts/ et services/arquantix/Makefile.

.PHONY: start stop status status-watch help setup doctor doctor-fix

# Onboarding Arquantix (Docker recovery) — voir docs/arquantix/QUICK_START.md
setup:
	@$(MAKE) -f Makefile.arquantix setup

doctor:
	@$(MAKE) -f Makefile.arquantix doctor

doctor-fix:
	@DRY_RUN=$${DRY_RUN:-0} $(MAKE) -f Makefile.arquantix doctor-fix

status:
	@$(MAKE) -f Makefile.arquantix status

status-watch:
	@STATUS_REFRESH_SEC=$${STATUS_REFRESH_SEC:-3} $(MAKE) -f Makefile.arquantix status-watch

start:
	@bash ./start-arquantix.sh

stop:
	@bash ./services/arquantix/scripts/arquantix-stop.sh

help:
	@echo "Cibles racine :"
	@echo "  make setup   — Arquantix : Docker recovery (API+Web+DB+Redis), smoke /health — voir docs/arquantix/QUICK_START.md"
	@echo "  make doctor  — Diagnostic DX (SAFE / WARNING / CRITICAL + suggestion si CRITICAL)"
	@echo "  make doctor-fix — Correctifs sûrs (compose up, restart api/web ; DRY_RUN=1 pour simulation)"
	@echo "  make status / make status-watch — Dashboard terminal stack recovery (lecture seule)"
	@echo "  make start   — Stack complète : Docker (DB+Redis) + FastAPI + Next + Binance WS"
	@echo "  make stop    — Arrêt API + Web (+ option --db dans le script)"
	@echo ""
	@echo "Docker Arquantix (Makefile.arquantix) : make -f Makefile.arquantix arquantix-up | arquantix-down | arquantix-logs"
	@echo "Détail / alias : voir services/arquantix/Makefile (make boot, make relance-tout, …)"
