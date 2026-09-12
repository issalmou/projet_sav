# Plateforme IA SAV & Support Technique — Backend

## Présentation

Backend FastAPI de la plateforme IA SAV & Support Technique : authentification JWT, gestion des utilisateurs et des rôles, chat IA avec recherche documentaire (RAG) et mémoire conversationnelle, gestion des tickets de support, des produits et de leur garantie, ainsi que de la base documentaire.

## Architecture

- `api/` — routes FastAPI (`auth`, `users`, `roles`, `chat`, `clients`, `documents`, `products`, `tickets`, `warranties`)
- `core/` — configuration (`config.py`), sécurité JWT/bcrypt (`security.py`), RBAC (`permissions.py`), dépendances FastAPI partagées (`dependencies.py`), journalisation (`logger.py`)
- `models/` — modèles SQLAlchemy 2 (`User`, `Role`, `Product`, `ClientProduct`, `Ticket`, `Conversation`, `Message`, `Document`, `DocumentProduct`)
- `schemas/` — schémas Pydantic (entrée/sortie de l'API)
- `services/` — logique métier (un service par ressource)
- `ai/` — module IA : `providers/` (LLM multi-fournisseur + tool-calling natif), `embeddings/` (embeddings multi-fournisseur), `rag/` (extraction, chunking, ChromaDB, recherche sémantique), `agent/` (agent SAV LangGraph : graphe ReAct, outils métier sécurisés, contexte)
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

# LLM (fournisseur actif : gemini | openai | mistral | qwen | llama | ollama)
LLM_PROVIDER=...
# Agent LangGraph : nb max de tours (garde-fou anti-boucle)
AGENT_MAX_ITERATIONS=...
# Escalade automatique : nb de tentatives de diagnostic infructueuses avant ticket auto (défaut 2)
AGENT_ESCALATION_MAX_FAILED_ATTEMPTS=...
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
# Ollama (LLM local) — modèle instruct supportant le tool-calling (qwen2.5:3b
# retenu après comparaison réelle avec qwen2.5:7b sur ce projet : plus fiable
# pour enchaîner correctement les appels d'outils requis par l'agent, cf.
# core/config.py)
OLLAMA_BASE_URL=...
OLLAMA_MODEL=...
OLLAMA_API_KEY=...
OLLAMA_NUM_CTX=...

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

## Contrats métier (Client / Produit / Conversation / Ticket / Agent)

### Client ↔ Produit (avec quantité)

Un « client » est un `User` de rôle `client` (aucune entité `Client`). `client_products` associe des produits **existants** à un client, avec une quantité (`qte >= 1`, contrainte CHECK). Gestion réservée à `administrateur` / `responsable_sav` / superuser :

- `GET  /api/v1/clients/{client_id}/products` — le client lui-même ou le staff ; renvoie chaque produit **avec sa `qte`** ;
- `POST /api/v1/clients/{client_id}/products` — staff uniquement.
  Corps : `{"items": [{"product_id": "...", "qte": 3}, ...]}` (`qte` optionnel, défaut 1).
  Doublons de `product_id` fusionnés ; produit déjà affecté → **quantité mise à jour** (upsert) ; transaction unique ;
- `DELETE /api/v1/clients/{client_id}/products/{product_id}` — staff uniquement (retire l'affectation).

### Conversation ↔ Produit — création séparée de l'envoi de message

- `POST /api/v1/chat/conversations` `{"product_id": "..."}` → **201**, crée la conversation.
  `conversations.product_id` est **obligatoire** (colonne NOT NULL). Un `client` ne peut ouvrir une conversation que sur un produit qui lui est **affecté** (`client_products`) → `403` sinon ; produit inconnu → `404`.
- `POST /api/v1/chat/message` `{"conversation_id": "...", "content": "..."}` → **200**.
  `conversation_id` est **obligatoire** — plus aucune création implicite de conversation. La **propriété** de la conversation est vérifiée dans le service : un client ne peut jamais écrire dans la conversation d'un autre (`404`, jamais `200`). Aucun `product_id` accepté ici.
- Le produit d'une conversation est **immuable** et sert de **source de vérité** (RAG, agent, ticket).

### Agent SAV — LangGraph uniquement

Le seul moteur d'orchestration de l'IA est l'agent LangGraph (`app/ai/agent/`) — l'ancien moteur « legacy » (marqueurs texte `[STATUT:]` / `[PRODUIT:]` + regex) a été **entièrement supprimé** (plus de `AGENT_ENGINE`, plus de `DiagnosticService`).

- Graphe : boucle ReAct `agent → (outils ?) → tools → agent`, garde-fou anti-boucle (`AGENT_MAX_ITERATIONS`, défaut 6) → nœud `finalize`. Le nœud `finalize` neutralise les `tool_calls` restés sans réponse avant de rappeler le LLM (séquence valide pour toutes les API chat/completions).
- Tool-calling **natif multi-fournisseur** : `LLMProvider.agenerate_tools` implémenté pour Gemini (`google-genai` function calling) et les API compatibles OpenAI (OpenAI / Qwen / Llama / Ollama / Mistral). Le graphe appelle `LLMService` injecté — **aucun couplage à un fournisseur**. Les spécificités Ollama (pas de `tool_choice`, `num_ctx` dans la requête, ids de tool calls régénérés) sont confinées à `OllamaProvider`.
- Outils (fonctions métier sécurisées, `app/ai/agent/tools.py`) : `search_docs`, `get_warranty`, `check_ticket_status`, `submit_diagnosis`, `record_client_feedback`, `request_ticket_creation`, `create_ticket`, `escalate_to_technician`.
- **Sécurité déterministe** (jamais déléguée au LLM) : le produit / le client / la conversation viennent de `AgentContext` (conversation authentifiée) ; les outils n'acceptent que du texte libre / des booléens d'interprétation ; les **compteurs de diagnostic** (`Conversation.diagnostic_attempts`, seuil d'escalade) sont gérés et lus par le backend ; `submit_diagnosis` exige `search_performed` (pas de diagnostic sans documentation) ; `create_ticket` n'est possible qu'après un `request_ticket_creation` fait à un tour **antérieur** (`ticket_proposed_this_run` False) et tant que `pending_ticket_confirmation` est vrai (B2) ; `escalate_to_technician` n'est possible qu'à partir de `diagnostic_attempts >= AGENT_ESCALATION_MAX_FAILED_ATTEMPTS` (CDC §17) ; pas de doublon de ticket actif, et aucun `ticket_id` renvoyé si rien n'a été créé dans le tour (B3).

### Workflow de résolution interactive (CDC §14 / §17)

`compréhension → search_docs → hypothèse + submit_diagnosis(cause, étapes numérotées) → question au client → record_client_feedback(resolved) → si non résolu : nouvelle recherche / nouvelle hypothèse → à N échecs : escalate_to_technician`.

- L'état du diagnostic est persisté sur `Conversation` (`diagnostic_attempts`, `search_performed`, `awaiting_step_feedback`, `problem_resolved`) et le déroulé dans la table **`conversation_events`** (append-only : `search` / `diagnosis` / `feedback` / `escalation` / `ticket`). L'état LangGraph étant volatil, un **récapitulatif** de ces événements est réinjecté dans le prompt à chaque tour (`build_diagnostic_recap`).
- **Deux chemins d'escalade** : *demande explicite* du client (`request_ticket_creation` → confirmation au tour suivant → `create_ticket`) et *échec du diagnostic* (`escalate_to_technician`, sans confirmation, gate backend sur le seuil).

### Ticket automatique

`client_id = conversation.user_id`, `product_id = conversation.product_id` (jamais déduit du texte ni du LLM), `conversation_id = conversation.id`, `assigned_technician_id` = **technicien actif choisi au hasard** (`ORDER BY random()`) — `null` si aucun. La **description** est générée automatiquement (`app/ai/agent/ticket_summary.py`) à partir de la conversation et du journal de diagnostic — rubriques *Problème / Symptômes / Diagnostic / Étapes proposées / Résultats des tentatives / Documentation consultée / Conclusion / Raison de l'escalade* — avec **repli déterministe** si le LLM échoue (la description n'est jamais vide). Le **titre** suit la même logique (ligne `TITRE:` du LLM, sinon `conversation.title` non générique, sinon 1er message client).

### `GET /api/v1/tickets`

Périmètre appliqué **dans le service** : `client` → ses tickets (`client_id`) ; `technicien` → ses tickets assignés (`assigned_technician_id`) ; staff / superuser → tous. Non contournable par un paramètre. Filtre optionnel `?status=open|in_progress|resolved|closed`.

### Upload de document

`product_ids` **obligatoire** (au moins un produit existant) — permet le filtrage RAG par produit.

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
