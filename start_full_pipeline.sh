#!/bin/bash
# start_full_pipeline.sh - Démarrage complet du projet

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${PROJECT_DIR}/config/config.ini"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Main
main() {
    print_header "🚀 DÉMARRAGE COMPLET - PIPELINE IDFM"
    
    # Check prereqs
    print_header "1️⃣ VÉRIFICATION DES PRÉREQUIS"
    
    if ! command -v python3 &> /dev/null; then
        print_error "python3 non trouvé"
        exit 1
    fi
    print_success "Python3 trouvé"
    
    # Check PostgreSQL
    print_info "Vérification PostgreSQL..."
    if ! psql -h localhost -p 5433 -U idfm_user -d idfm_datamarts -c "SELECT 1" &> /dev/null; then
        print_error "PostgreSQL non accessible sur localhost:5433"
        print_info "Solutions:"
        print_info "  1. Docker: docker run --name postgres-idfm -e POSTGRES_PASSWORD=idfm_pass -e POSTGRES_USER=idfm_user -e POSTGRES_DB=idfm_datamarts -p 5433:5432 -d postgres:15"
        print_info "  2. Local: Vérifier que PostgreSQL est en écoute sur port 5433"
        exit 1
    fi
    print_success "PostgreSQL accessible"
    
    # Check CSV files
    print_header "2️⃣ VALIDATION DES FICHIERS CSV"
    python3 "${PROJECT_DIR}/test_csv_files.py"
    
    # Install dependencies
    print_header "3️⃣ INSTALLATION DES DÉPENDANCES"
    print_info "pip install -r requirements.txt..."
    pip install -q -r "${PROJECT_DIR}/requirements.txt"
    print_success "Dépendances installées"
    
    # Run pipeline
    print_header "4️⃣ LANCEMENT DU PIPELINE LOCAL"
    python3 "${PROJECT_DIR}/pipeline_local.py" --config "$CONFIG"
    
    # Success
    print_header "🎉 SUCCÈS!"
    print_success "Pipeline terminé"
    print_success "Données chargées dans PostgreSQL"
    
    echo ""
    print_info "Prochaines étapes:"
    echo ""
    echo -e "${YELLOW}Terminal 1 - API REST:${NC}"
    echo "  cd $PROJECT_DIR/api"
    echo "  python -m uvicorn app:app --reload --port 8000"
    echo ""
    echo -e "${YELLOW}Terminal 2 - Dashboard:${NC}"
    echo "  streamlit run $PROJECT_DIR/dashboard/app.py"
    echo ""
    echo -e "${YELLOW}URLs:${NC}"
    echo "  API Swagger: http://localhost:8000/docs"
    echo "  Dashboard: http://localhost:8501"
    echo ""
}

main "$@"
