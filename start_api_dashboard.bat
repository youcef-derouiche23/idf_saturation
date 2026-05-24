@echo off
REM Script de démarrage de l'API et du Dashboard (Windows)

setlocal enabledelayedexpansion

echo ======================================================
echo ^|^| Demarrage API FastAPI et Dashboard Streamlit
echo ======================================================

REM Verifier requirements.txt
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo ^|^| Installation des dependances...
    pip install -r requirements.txt
)

REM Demarrer l'API en arriere-plan
echo ^|^| Demarrage de l'API sur http://localhost:8000
start "API IDFM" uvicorn api.app:app --reload --host 0.0.0.0 --port 8000

REM Attendre que l'API demarre
timeout /t 2 /nobreak

echo ^|^| API demarree avec succes
echo ^|^| Demarrage du Dashboard Streamlit sur http://localhost:8501

REM Demarrer le dashboard
start "Dashboard IDFM" streamlit run dashboard/app.py

echo.
echo ======================================================
echo ^|^| Services lancés:
echo ^|^|   - API:       http://localhost:8000
echo ^|^|   - Dashboard: http://localhost:8501
echo ^|^|   - Docs API:  http://localhost:8000/docs
echo ======================================================

endlocal
