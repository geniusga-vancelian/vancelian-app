#!/bin/bash

# Script pour arrêter tous les serveurs Arquantix démarrés en arrière-plan

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🛑 Arrêt des serveurs Arquantix...${NC}"
echo ""

# Arrêter les processus en arrière-plan (noms alignés avec arquantix-boot et start-all)
for service in "api" "web"; do
    pid_file="/tmp/arquantix-$service.pid"
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            kill "$pid" 2>/dev/null || true
            echo -e "${GREEN}✅ $service arrêté (PID: $pid)${NC}"
        else
            echo -e "${YELLOW}⚠️  $service n'était pas en cours d'exécution${NC}"
        fi
        rm -f "$pid_file"
    fi
done

# Arrêter les processus uvicorn
pkill -f "uvicorn main:app" 2>/dev/null && echo -e "${GREEN}✅ Processus uvicorn arrêté${NC}" || true

# Arrêter les processus Next.js
pkill -f "next dev" 2>/dev/null && echo -f "${GREEN}✅ Processus Next.js arrêté${NC}" || true

# Note: Strapi n'est plus utilisé dans ce projet

echo ""
echo -e "${GREEN}✨ Tous les serveurs ont été arrêtés${NC}"

