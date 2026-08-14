# Plateforme IA SAV & Support Technique — Backend

## Accélération GPU pour les embeddings locaux (E5)

`EMBEDDING_PROVIDER=e5` utilise `sentence-transformers` (modèle `intfloat/multilingual-e5-small`), qui tourne localement via `torch`. `pip install -r requirements.txt` installe par défaut la version **CPU** de `torch` — portable sur n'importe quelle machine, y compris sans GPU.

Pour utiliser un GPU NVIDIA (accélère nettement le calcul des embeddings) :

1. Vérifier que le driver NVIDIA est installé et voir la version CUDA supportée :
   ```
   nvidia-smi
   ```
2. Choisir le tag CUDA correspondant dans la liste des builds disponibles pour la version de `torch` installée (`https://download.pytorch.org/whl/torch/`), par exemple `cu126`, `cu130`, `cu132`...
3. Réinstaller `torch` avec ce build (remplace la version CPU) :
   ```
   
   ```
   (remplacer `cuXXX` par le tag choisi, ex. `cu130`)
4. Vérifier que le GPU est détecté :
   ```pip install torch --index-url https://download.pytorch.org/whl/cu130 --force-reinstall
   python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
   ```

`E5EmbeddingProvider` (`ai/embeddings/e5_embedding_provider.py`) détecte automatiquement `torch.cuda.is_available()` et utilise le GPU s'il est présent, sinon le CPU — aucune configuration supplémentaire n'est nécessaire côté application une fois `torch` réinstallé.

Cette étape est **spécifique à la machine** (dépend du GPU et du driver installés) et n'est donc pas figée dans `requirements.txt`, pour ne pas casser l'installation sur une machine sans GPU compatible.
