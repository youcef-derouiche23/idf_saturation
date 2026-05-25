#!/bin/bash
# run_spark_pipeline.sh - Lance le pipeline complet Spark (feeder → processor → datamart)
# 
# Utilisation : bash run_spark_pipeline.sh [--skip-feeder] [--skip-processor] [--skip-datamart]
# 
# Exemple :
#   bash run_spark_pipeline.sh                    # Lance tout
#   bash run_spark_pipeline.sh --skip-feeder      # Saute feeder
#   bash run_spark_pipeline.sh --skip-datamart    # Saute datamart

set -e  # Exit on error

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${PROJECT_DIR}/config/config.ini"
LOG_DIR="${PROJECT_DIR}/logs"

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Flags
SKIP_FEEDER=false
SKIP_PROCESSOR=false
SKIP_DATAMART=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --skip-feeder) SKIP_FEEDER=true ;;
        --skip-processor) SKIP_PROCESSOR=true ;;
        --skip-datamart) SKIP_DATAMART=true ;;
    esac
done

# Helper functions
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

# Check prerequisites
check_prerequisites() {
    print_header "🔍 VÉRIFICATION DES PRÉREQUIS"
    
    # Check Spark
    if ! command -v spark-submit &> /dev/null; then
        print_error "spark-submit non trouvé. Installez Spark."
        exit 1
    fi
    print_success "Spark trouvé"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "python3 non trouvé"
        exit 1
    fi
    print_success "Python3 trouvé"
    
    # Check config file
    if [ ! -f "$CONFIG" ]; then
        print_error "config.ini non trouvé: $CONFIG"
        exit 1
    fi
    print_success "Config trouvée: $CONFIG"
    
    # Create log directory
    mkdir -p "$LOG_DIR"
    print_success "Répertoire logs: $LOG_DIR"
}

# Run feeder
run_feeder() {
    if [ "$SKIP_FEEDER" = true ]; then
        print_info "⏭️  Feeder ignoré (--skip-feeder)"
        return 0
    fi
    
    print_header "🔄 ÉTAPE 1 : FEEDER (Ingestion CSV → Parquet/HDFS)"
    
    FEEDER_SCRIPT="${PROJECT_DIR}/feeder.py"
    FEEDER_LOG="${LOG_DIR}/feeder_$(date +%Y%m%d_%H%M%S).log"
    
    if [ ! -f "$FEEDER_SCRIPT" ]; then
        print_error "feeder.py non trouvé: $FEEDER_SCRIPT"
        exit 1
    fi
    
    print_info "Lancement feeder..."
    print_info "Fichier log: $FEEDER_LOG"
    
    if spark-submit \
        --master local[*] \
        --driver-memory 4g \
        --executor-memory 4g \
        "$FEEDER_SCRIPT" --config "$CONFIG" 2>&1 | tee "$FEEDER_LOG"; then
        print_success "Feeder terminé avec succès"
        return 0
    else
        print_error "Feeder échoué"
        return 1
    fi
}

# Run processor
run_processor() {
    if [ "$SKIP_PROCESSOR" = true ]; then
        print_info "⏭️  Processor ignoré (--skip-processor)"
        return 0
    fi
    
    print_header "🔄 ÉTAPE 2 : PROCESSOR (Transformation Silver)"
    
    PROCESSOR_SCRIPT="${PROJECT_DIR}/processor.py"
    PROCESSOR_LOG="${LOG_DIR}/processor_$(date +%Y%m%d_%H%M%S).log"
    
    if [ ! -f "$PROCESSOR_SCRIPT" ]; then
        print_error "processor.py non trouvé: $PROCESSOR_SCRIPT"
        exit 1
    fi
    
    print_info "Lancement processor..."
    print_info "Fichier log: $PROCESSOR_LOG"
    
    if spark-submit \
        --master local[*] \
        --driver-memory 4g \
        --executor-memory 4g \
        "$PROCESSOR_SCRIPT" --config "$CONFIG" 2>&1 | tee "$PROCESSOR_LOG"; then
        print_success "Processor terminé avec succès"
        return 0
    else
        print_error "Processor échoué"
        return 1
    fi
}

# Run datamart
run_datamart() {
    if [ "$SKIP_DATAMART" = true ]; then
        print_info "⏭️  Datamart ignoré (--skip-datamart)"
        return 0
    fi
    
    print_header "🔄 ÉTAPE 3 : DATAMART (Gold Tables)"
    
    DATAMART_SCRIPT="${PROJECT_DIR}/datamart.py"
    DATAMART_LOG="${LOG_DIR}/datamart_$(date +%Y%m%d_%H%M%S).log"
    
    if [ ! -f "$DATAMART_SCRIPT" ]; then
        print_error "datamart.py non trouvé: $DATAMART_SCRIPT"
        exit 1
    fi
    
    print_info "Lancement datamart..."
    print_info "Fichier log: $DATAMART_LOG"
    
    if spark-submit \
        --master local[*] \
        --driver-memory 4g \
        --executor-memory 4g \
        "$DATAMART_SCRIPT" --config "$CONFIG" 2>&1 | tee "$DATAMART_LOG"; then
        print_success "Datamart terminé avec succès"
        return 0
    else
        print_error "Datamart échoué"
        return 1
    fi
}

# Show summary
show_summary() {
    print_header "📊 RÉSUMÉ DU PIPELINE"
    
    echo "Répertoire projet: $PROJECT_DIR"
    echo "Fichier config: $CONFIG"
    echo "Répertoire logs: $LOG_DIR"
    
    echo ""
    echo "Étapes exécutées:"
    
    if [ "$SKIP_FEEDER" = true ]; then
        echo "  ⏭️  Feeder (ignoré)"
    else
        echo "  ✅ Feeder"
    fi
    
    if [ "$SKIP_PROCESSOR" = true ]; then
        echo "  ⏭️  Processor (ignoré)"
    else
        echo "  ✅ Processor"
    fi
    
    if [ "$SKIP_DATAMART" = true ]; then
        echo "  ⏭️  Datamart (ignoré)"
    else
        echo "  ✅ Datamart"
    fi
    
    echo ""
    echo "📁 Fichiers log:"
    ls -lh "${LOG_DIR}"/*.log 2>/dev/null | tail -3 || echo "Aucun log trouvé"
}

# Main execution
main() {
    print_header "🚀 PIPELINE BIG DATA - IDFM FRÉQUENTATION"
    echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Utilisateur: $(whoami)"
    
    # Check prerequisites
    check_prerequisites
    
    # Run pipeline
    if ! run_feeder; then
        print_error "Pipeline interrompu à feeder"
        exit 1
    fi
    
    if ! run_processor; then
        print_error "Pipeline interrompu à processor"
        exit 1
    fi
    
    if ! run_datamart; then
        print_error "Pipeline interrompu à datamart"
        exit 1
    fi
    
    # Show summary
    show_summary
    
    print_header "🎉 PIPELINE TERMINÉ AVEC SUCCÈS!"
    echo -e "${GREEN}Les données sont maintenant disponibles dans:${NC}"
    echo "  - HDFS /raw (feeder)"
    echo "  - HDFS /silver (processor)"
    echo "  - PostgreSQL datamarts (datamart)"
    echo ""
    echo -e "${YELLOW}Prochaines étapes:${NC}"
    echo "  1. Lancer l'API: cd api && python -m uvicorn app:app --reload"
    echo "  2. Lancer le dashboard: streamlit run dashboard/app.py"
    echo "  3. Consulter l'API: http://localhost:8000/docs"
}

main "$@"
