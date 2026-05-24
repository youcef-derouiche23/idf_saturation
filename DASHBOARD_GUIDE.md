# 📊 Guide Complet - Tableau de Bord IDFM

## 🎯 Objectif
Répondre à : **"Où et quand le réseau souffre-t-il le plus ?"**

## 🚀 Démarrage en 2 Minutes

### Terminal 1 - API
```bash
cd /Users/youcef/Downloads/Projet_IDFM_Frequentation
uvicorn api.app:app --reload --port 8000
```

### Terminal 2 - Dashboard
```bash
cd /Users/youcef/Downloads/Projet_IDFM_Frequentation
streamlit run dashboard/app.py
```

Ouvrez : **http://localhost:8501**

---

## 📍 Page 1 : Fréquentation par Stations/Lignes

### Ce que tu vois
```
📊 Stations : 782
🚇 Lignes : 6
⏰ Créneaux : 25
```

### Interprétation
| Métrique | 🟢 Bon | 🟠 Attention | 🔴 Critique |
|----------|--------|-------------|------------|
| Fréquentation/h | < 1K | 1K-5K | > 5K |

### Actions
- **> 5 000 validations** = 🔴 Station saturée
- Solution : Ajouter rames, renforcer personnel

---

## 📋 Page 2 : Régularité et Ponctualité

### Ce que tu vois
```
Ponctualité moyenne : 92.5%
Rang (1 = pire) : Ligne 4
```

### Interprétation
- **🟢 > 95%** = Objectif atteint (excellent)
- **🟠 80-95%** = À surveiller
- **🔴 < 80%** = Critique (action urgente)

### Questions à poser
1. Cette ligne est-elle aussi saturée que les autres ?
2. Les retards viennent-ils des pics d'affluence ?
3. Besoin de maintenance ou de personnel supplémentaire ?

---

## 📈 Page 3 : Évolution Temporelle

### Ce que tu vois
```
Fréquentation totale : 2.3M validations
Variation vs S-1 : +5.2%
```

### Patterns à chercher
1. **Lun-Ven vs Week-end** : Très différent
2. **Jours fériés** : Trafic anormal
3. **Vacances scolaires** : Réduction de 20-30%

### Interprétation
- Si variation > +20% = ⚠️ Événement ou incident
- Si variation < -20% = 📉 Grève ou perturbation

---

## 🤖 Page 4 : Dataset Saturation (ML)

### Ce que tu vois
```
Créneaux saturés : 18,500 (21.5%)
Créneaux normaux : 67,268 (78.5%)
```

### Utilité
Ce dataset prépare l'IA à prédire la saturation :
- **Input (Features)** : Ligne, Heure, Jour-type, Validations, Ponctualité
- **Output (Label)** : Est_saturation (0=normal, 1=saturé)

### Cas d'usage IA
```
Heure : 7h30
Jour : Lundi
Ligne : 4
Validations : 5,800
Ponctualité : 88%

IA prédit : "SATURÉ en 95% de confiance"
Alerte : "Renfort recommandé à 7h20"
```

---

## 🎨 Légende des Couleurs

### Fréquentation
- 🟢 Vert = Faible (< 1 000)
- 🟠 Orange = Normal (1K-5K)
- 🔴 Rouge = Saturé (> 5K)

### Ponctualité
- 🟢 Vert = Bon (> 95%)
- 🟠 Orange = Acceptable (80-95%)
- 🔴 Rouge = Critique (< 80%)

### Tendances
- ⬆️ Flèche haut = Augmentation
- ⬇️ Flèche bas = Diminution

---

## 📊 Métriques Clés à Retenir

### Fréquentation
- **Validations** = Nombre de badgeages (proxy des passagers)
- **Saturation threshold** = 5 000 validations/heure
- **Peak hours** = 7-9h (matin) et 17-19h (soir)

### Régularité
- **Taux ponctualité** = % de trains à l'heure
- **Objectif IDFM** = 95% minimum
- **Délai moyen** = Temps supplémentaire en cas de retard

### Évolution
- **Jour-types** = DIJFP (lun-ven), SAMEDI, DIMANCHE
- **Variation vs S-1** = Par rapport à la semaine précédente
- **Fréquentation cumulée** = Total journalier

---

## 💡 Cas d'Usage - Exemple Concret

### Situation : Lundi 8h, Ligne 4

**Dashboard affiche :**
```
Fréquentation : 5,800 validations 🔴 SATURÉ
Ponctualité : 87% 🟠 CRITIQUE
Variation vs lundi précédent : +12% ⚠️
```

**Interprétation :**
1. La ligne est surchargée (> 5 000)
2. Les trains prennent du retard (< 95%)
3. Le trafic est anormalement élevé

**Action :**
- ➕ Ajouter 2 rames supplémentaires
- 👥 Renforcer personnel aux stations clés
- 📱 Informer usagers (retards attendus)

**Résultat :**
- Embarquement + rapide
- Satisfaction clients +15%
- Moindre réclamations

---

## 🔐 Accès & Authentification

### Credentials
- **Username** : admin
- **Password** : admin

### Ports
- **API** : http://localhost:8000
- **Dashboard** : http://localhost:8501
- **API Docs** : http://localhost:8000/docs

---

## 🛠️ Commandes Utiles

```bash
# Restart API
pkill uvicorn
uvicorn api.app:app --reload

# Restart Dashboard
pkill streamlit
streamlit run dashboard/app.py

# Check data
python test_csv_files.py

# View logs
tail -f logs/*.log
```

---

## 📞 Support

| Question | Réponse |
|----------|---------|
| Comment lancer le dashboard ? | `streamlit run dashboard/app.py` |
| Où sont les données ? | `./data/*.csv` |
| Comment modifier les seuils ? | `config/config.ini` → `[thresholds]` |
| Où voir les erreurs API ? | `http://localhost:8000/docs` |
| Combien de données ? | 85,768 créneaux spatio-temporels |

---

**✅ Tu es prêt à utiliser le dashboard !**

Des questions ? Consulte le README.md ou les logs d'erreur en terminal.
