# Makefile pour Arquantix
# Usage: make boot, make stop, make status, make audit-doc

.PHONY: boot up boot-nodocker relance-tout stop status audit-doc seed-fields start-api-web help ds-web show-db-config doctor-db migrate-api db-merge-help

# Configuration
SCRIPT_DIR := scripts
TOOLS_DIR := tools

# Couleurs pour les messages
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help:
	@echo "$(GREEN)Arquantix - Commandes disponibles:$(NC)"
	@echo ""
	@echo "  $(YELLOW)make boot$(NC)        - Démarre tous les services (DB + API + Web)"
	@echo "  $(YELLOW)make up$(NC)          - Alias de make boot"
	@echo "  $(YELLOW)make boot-nodocker$(NC) - Idem boot sans vérif. Docker (DB déjà lancée)"
	@echo "  $(YELLOW)make relance-tout$(NC)  - DB (compose) + make boot (relance complète)"
	@echo "  $(YELLOW)make start-api-web$(NC) - Démarre API + Web seulement (DB déjà lancée)"
	@echo "  $(YELLOW)make stop$(NC)        - Arrête tous les services (API + Web)"
	@echo "  $(YELLOW)make stop-db$(NC)     - Arrête tous les services + DB"
	@echo "  $(YELLOW)make status$(NC)      - Affiche le status de tous les services"
	@echo "  $(YELLOW)make audit-doc$(NC)   - Audite la complétude de la documentation canonique"
	@echo "  $(YELLOW)make seed-fields$(NC) - Seed field definitions from CSV"
	@echo "  $(YELLOW)make ds-web$(NC)      - Ouvre le Design System dans Chrome (sim. smartphone)"
	@echo "  $(YELLOW)make show-db-config$(NC) / $(YELLOW)doctor-db$(NC) - Audit DATABASE_URL (API/Web/fichiers .env)"
	@echo "  $(YELLOW)make migrate-api$(NC)  - Alembic upgrade head (répertoire api)"
	@echo "  $(YELLOW)make db-merge-help$(NC) - Commandes pg_dump de backup + rappel fusion DB"
	@echo ""
	@echo "Exemples:"
	@echo "  make boot                    # Démarre tout"
	@echo "  AUDIT_DOCS=1 make boot       # Démarre tout + audit docs"
	@echo "  make stop                    # Arrête API + Web"
	@echo "  make stop-db                 # Arrête tout + DB"
	@echo ""

boot:
	@echo "$(GREEN)🚀 Démarrage Arquantix...$(NC)"
	@./$(SCRIPT_DIR)/arquantix-boot.sh

up: boot

# Si Docker/DB tournent déjà mais la vérification Docker échoue (ex. autre terminal):
boot-nodocker:
	@ARQUANTIX_SKIP_DOCKER=1 $(MAKE) boot

relance-tout:
	@bash ./$(SCRIPT_DIR)/arquantix-relance-tout.sh

start-api-web:
	@echo "$(GREEN)🚀 Démarrage API + Web (DB supposée déjà lancée)...$(NC)"
	@bash ./$(SCRIPT_DIR)/arquantix-start-api-web.sh

stop:
	@echo "$(YELLOW)🛑 Arrêt des services Arquantix...$(NC)"
	@./$(SCRIPT_DIR)/arquantix-stop.sh

stop-db:
	@echo "$(YELLOW)🛑 Arrêt des services Arquantix (avec DB)...$(NC)"
	@./$(SCRIPT_DIR)/arquantix-stop.sh --db

status:
	@./$(SCRIPT_DIR)/arquantix-status.sh

audit-doc:
	@echo "$(GREEN)📚 Audit de la documentation canonique...$(NC)"
	@python3 $(TOOLS_DIR)/audit_doc_completeness.py

seed-fields:
	@echo "$(GREEN)🌱 Seeding field definitions...$(NC)"
	@cd api && python3 -m alembic upgrade 008 || python3 -m alembic upgrade head
	@cd api && python3 scripts/seed_field_definitions.py

ds-web:
	@echo "$(GREEN)🎨 Lancement du Design System sur Chrome (simulation iPhone 13 Pro)...$(NC)"
	@cd mobile && flutter run -d chrome --target=lib/main_design_system.dart --web-browser-flag=--window-size=500,900

show-db-config doctor-db:
	@python3 $(SCRIPT_DIR)/db_config_audit.py

migrate-api:
	@echo "$(GREEN)▶ Alembic upgrade head (api)$(NC)"
	@cd api && python3 -m alembic upgrade head

db-merge-help:
	@echo "$(GREEN)Fusion quant+admin → arquantix (voir DB_UNIFICATION_PHASE_2_REPORT.md)$(NC)"
	@python3 $(SCRIPT_DIR)/db_merge_quant_admin.py --print-backup-commands

