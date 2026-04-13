# Point d'entrée minimal à la racine du dépôt (aligné sur l'ancien flux OneDrive).
# La logique détaillée vit dans services/arquantix/scripts/ et services/arquantix/Makefile.

.PHONY: start stop status help

start:
	@bash ./start-arquantix.sh

stop:
	@bash ./services/arquantix/scripts/arquantix-stop.sh

status:
	@bash ./services/arquantix/scripts/arquantix-status.sh 2>/dev/null || $(MAKE) -C services/arquantix status

help:
	@echo "Cibles racine :"
	@echo "  make start   — Stack complète : Docker (DB+Redis) + FastAPI + Next + Binance WS"
	@echo "  make stop    — Arrêt API + Web (+ option --db dans le script)"
	@echo "  make status  — État des services"
	@echo ""
	@echo "Docker DB+Redis seuls : make -f Makefile.arquantix arquantix-db-redis"
	@echo "Détail / alias : voir services/arquantix/Makefile (make boot, make relance-tout, …)"
