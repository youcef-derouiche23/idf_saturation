# ⚡ QUICK START - 2 Minutes

## 🎯 Objectif : Lancer tout en 2-3 commandes

---

## 1️⃣ Démarrer PostgreSQL (une fois)

```bash
docker run --name postgres-idfm \
  -e POSTGRES_PASSWORD=idfm_pass \
  -e POSTGRES_USER=idfm_user \
  -e POSTGRES_DB=idfm_datamarts \
  -p 5433:5432 -d postgres:15
```

Attendre 5 secondes ⏳

---

## 2️⃣ Lancer le Pipeline

```bash
cd /Users/youcef/Downloads/Projet_IDFM_Frequentation
bash start_full_pipeline.sh
```

Attendre 2-5 minutes (selon ton système) ⏳

Résultat attendu :
```
✅ Python3 trouvé
✅ PostgreSQL accessible
✅ TOUS LES FICHIERS SONT VALIDES!
✅ Dépendances installées
✅ Pipeline terminé avec succès!
```

---

## 3️⃣ Lancer l'API (Terminal 1)

```bash
cd /Users/youcef/Downloads/Projet_IDFM_Frequentation/api
python -m uvicorn app:app --reload --port 8000
```

```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

Ouvre dans le navigateur : 📍 http://localhost:8000/docs

---

## 4️⃣ Lancer le Dashboard (Terminal 2)

```bash
cd /Users/youcef/Downloads/Projet_IDFM_Frequentation
streamlit run dashboard/app.py
```

```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

Ouvre : 📍 http://localhost:8501

---

## 🎉 Voilà !

Tu as maintenant :
- ✅ PostgreSQL avec toutes les données
- ✅ API REST avec Swagger
- ✅ Dashboard Streamlit

**API Endpoints rapides :**

```bash
# Health check
curl http://localhost:8000/

# Auth
curl -X POST http://localhost:8000/auth/login \
  -d "username=admin&password=admin"

# Données
curl http://localhost:8000/docs
```

---

## 🐛 Problème ? 

```bash
# Vérifier PostgreSQL
psql -h localhost -p 5433 -U idfm_user -d idfm_datamarts

# Voir les logs
tail -f /Users/youcef/Downloads/Projet_IDFM_Frequentation/logs/pipeline_local_*.log

# Réinstaller dépendances
pip install -r /Users/youcef/Downloads/Projet_IDFM_Frequentation/requirements.txt

# Relancer
bash /Users/youcef/Downloads/Projet_IDFM_Frequentation/start_full_pipeline.sh
```

---

**Enjoy ! 🚀**
