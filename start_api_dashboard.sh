#!/bin/bash

# Script de démarrage de l'API et du Dashboard

set -e

echo "🚀 Démarrage de l'API FastAPI et du Dashboard Streamlit"
echo "=================================================="

# Vérifier que requirements.txt est installé
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installation des dépendances..."
    pip install -r requirements.txt
fi

# Démarrer l'API en arrière-plan
echo "🔧 Démarrage de l'API sur http://localhost:8000"
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!

sleep 2

# Vérifier que l'API est bien lancée
if ! curl -s http://localhost:8000/ > /dev/null; then
    echo "❌ Erreur : l'API n'a pas démarré correctement"
    kill $API_PID 2>/dev/null || true
    exit 1
fi

echo "✅ API démarrée (PID: $API_PID)"

# Démarrer le dashboard
echo "📊 Démarrage du Dashboard Streamlit sur http://localhost:8501"
streamlit run dashboard/app.py

# Cleanup
kill $API_PID 2>/dev/null || true
