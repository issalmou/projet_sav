# Plateforme IA SAV & Support Technique — Backend

## Présentation

Backend FastAPI de la plateforme IA SAV & Support Technique : authentification JWT, gestion des utilisateurs et des rôles, chat IA avec recherche documentaire (RAG) et mémoire conversationnelle, gestion des tickets de support, des produits et de leur garantie, ainsi que de la base documentaire.

## Architecture

- `api/` — routes FastAPI (`auth`, `users`, `chat`, `documents`, `products`, `tickets`, `warranties`, `dashboard`)
- `core/` — configuration (`config.py`), sécurité JWT/bcrypt (`security.py`), RBAC (`permissions.py`), dépendances FastAPI partagées (`dependencies.py`), journalisation (`logger.py`)
- `models/` — modèles SQLAlchemy 2 (`User`, `Role`, `Product`, `Ticket`, `Conversation`, `Message`, `Document`)
- `schemas/` — schémas Pydantic (entrée/sortie de l'API)
- `services/` — logique métier (un service par ressource)
- `ai/` — module IA : `providers/` (LLM multi-fournisseur), `embeddings/` (embeddings multi-fournisseur), `rag/` (extraction, chunking, ChromaDB, recherche sémantique)
- `database/` — moteur SQLAlchemy asynchrone, session, script de seed
- `alembic/` — migrations de schéma
- `tests/` — suite `pytest`

## Prérequis

- Environnement Anaconda `stage-pfa` (Python 3.11)
- PostgreSQL accessible via `DATABASE_URL`
- Dépendances Python listées dans `requirements.txt` (FastAPI, SQLAlchemy 2, Alembic, pydantic-settings, `google-genai`, `openai`, `mistralai`, `chromadb`, `sentence-transformers`, `pytest`...)

## Environnement

Toutes les commandes ci-dessous doivent être exécutées dans l'environnement Anaconda du projet :

```bash
conda activate stage-pfa
```

Aucun autre environnement (venv, virtualenv, Poetry, autre environnement conda) n'est utilisé par ce projet.

## Configuration

Variables lues depuis un fichier `.env` à la racine de `backend/` (voir `core/config.py` pour la liste complète, les valeurs par défaut et les commentaires). `SECRET_KEY` et `DATABASE_URL` sont **obligatoires** (pas de valeur par défaut) ; les autres variables ont une valeur par défaut raisonnable. Exemple de noms attendus, **sans valeur réelle** :

```env
# Application
APP_NAME=...
APP_ENV=...
DEBUG=...
API_V1_PREFIX=...
APP_VERSION=...

# Sécurité
SECRET_KEY=...
ALGORITHM=...
ACCESS_TOKEN_EXPIRE_MINUTES=...
REFRESH_TOKEN_EXPIRE_MINUTES=...
ALLOWED_ORIGINS=...

# Base de données
DATABASE_URL=...
DB_POOL_SIZE=...
DB_MAX_OVERFLOW=...
DB_POOL_TIMEOUT=...
DB_ECHO=...

# LLM (fournisseur actif : gemini | openai | mistral | qwen | llama)
LLM_PROVIDER=...
LLM_REQUEST_TIMEOUT_SECONDS=...
GEMINI_API_KEY=...
GEMINI_MODEL=...
OPENAI_API_KEY=...
OPENAI_MODEL=...
MISTRAL_API_KEY=...
MISTRAL_MODEL=...
QWEN_API_KEY=...
QWEN_MODEL=...
QWEN_BASE_URL=...
LLAMA_API_KEY=...
LLAMA_MODEL=...
LLAMA_BASE_URL=...

# Embeddings (fournisseur independant de LLM_PROVIDER : gemini | openai | mistral | qwen | llama | e5)
EMBEDDING_PROVIDER=...
GEMINI_EMBEDDING_MODEL=...
OPENAI_EMBEDDING_MODEL=...
MISTRAL_EMBEDDING_MODEL=...
QWEN_EMBEDDING_MODEL=...
LLAMA_EMBEDDING_MODEL=...
E5_EMBEDDING_MODEL=...

# Bootstrap (premier compte super admin, voir section Base de donnees)
FIRST_ADMIN_EMAIL=...
FIRST_ADMIN_PASSWORD=...

# Journalisation
LOG_LEVEL=...
LOG_JSON=...

# Multilingue
DEFAULT_LANGUAGE=...
SUPPORTED_LANGUAGES=...

# Documents / RAG
UPLOAD_DIR=...
MAX_UPLOAD_SIZE_MB=...
CHROMA_DB_DIR=...
```

## Base de données

Depuis `backend/app/` (répertoire contenant `alembic.ini`), appliquer les migrations Alembic :

```bash
PYTHONPATH=.. alembic upgrade head
```

Peupler les 4 rôles officiels du CDC et créer le premier compte super admin (idempotent — sans effet si déjà fait ; nécessite `FIRST_ADMIN_EMAIL`/`FIRST_ADMIN_PASSWORD` dans `.env`), depuis `backend/` :

```bash
PYTHONPATH=. python -m app.database.seed
```

## Lancement de l'API

Depuis `backend/` (répertoire parent du package `app`) :

```bash
uvicorn app.main:app --reload
```

## Tests

Depuis `backend/` :

```bash
PYTHONPATH=. python -m pytest app/tests/ -q
```

Les tests marqués `external` (appels réseau réels vers un fournisseur LLM/embedding externe — nécessitent une clé API valide et une connexion réseau) sont **exclus par défaut** de cette commande. Ils ne sont pas nécessaires pour une exécution locale normale de la suite de tests. Pour les exécuter explicitement :

```bash
PYTHONPATH=. python -m pytest app/tests/ -m external
```

## Documentation API

Une fois l'API lancée :

- Swagger UI : `/docs`
- ReDoc : `/redoc`
- Schéma OpenAPI brut : `/openapi.json`

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
