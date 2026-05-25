#!/bin/bash
# start_data_loader.sh - Lance le data loader local

echo "🚀 Démarrage du Data Loader..."
python data_loader.py --config config/config.ini
echo "✓ Data Loader terminé"
