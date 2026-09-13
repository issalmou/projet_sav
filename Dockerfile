FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1 \
	PYTHONPATH=/app \
	HF_HUB_DISABLE_XET=1
# HF_HUB_DISABLE_XET : évite le protocole xet (hf-xet) de Hugging Face.
# Insuffisant à lui seul (le CDN de stockage réel reste le même quel que soit
# le protocole, et s'est révélé intermittent sur certains réseaux) — gardé
# par précaution ; la vraie protection contre cette instabilité réseau est le
# pré-téléchargement du modèle d'embeddings au build, plus bas, combiné à
# HF_HUB_OFFLINE (définie après ce pré-téléchargement).

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends build-essential libpq-dev \
	&& rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

# --extra-index-url CPU : ce conteneur n'a pas de GPU, la roue torch par
# défaut sur PyPI télécharge inutilement plusieurs Go de bibliothèques CUDA.
RUN python -m pip install --upgrade pip \
	&& pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Le code s'importe partout comme `app.xxx` (ex: CMD ci-dessous) : le
# contexte de build est le contenu du package `app`, il doit donc être copié
# dans un sous-dossier `app/` et non à la racine `/app`, sous peine de
# `ModuleNotFoundError: No module named 'app'` au démarrage d'uvicorn.
COPY . ./app

RUN useradd --create-home --uid 1000 appuser \
	&& chown -R appuser:appuser /app
USER appuser

# Pré-télécharge le modèle d'embeddings E5 dans l'image plutôt qu'au premier
# démarrage : le CDN Hugging Face qui sert ses poids (~470 Mo) s'est montré
# intermittent (de quelques secondes à plusieurs minutes, voire un blocage
# complet) sur certains réseaux — inacceptable au runtime, où un client
# attend une réponse. Le modèle est ainsi déjà en cache local
# (~/.cache/huggingface) quel que soit EMBEDDING_PROVIDER en prod ; retries
# car le téléchargement peut échouer une ou deux fois avant d'aboutir (il
# reprend où il s'est arrêté, cf. mécanisme de reprise de huggingface_hub).
RUN for i in 1 2 3 4 5; do \
		python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small')" \
		&& break; \
		echo "Échec du pré-téléchargement du modèle E5 (tentative $i/5), nouvel essai..."; \
		sleep 10; \
	done

# HF_HUB_OFFLINE (déclarée seulement ici, après le pré-téléchargement
# ci-dessus qui a besoin du réseau) : même avec le modèle déjà sur disque,
# huggingface_hub revalide par défaut chaque fichier auprès du CDN distant à
# chaque démarrage (~15-20 requêtes HEAD, ~10s+ constatés) avant d'utiliser le
# cache local. Le mode hors-ligne saute cette revalidation et lit directement
# le cache — sûr ici puisque le modèle vient d'être fixé pour cette image.
ENV HF_HUB_OFFLINE=1

EXPOSE 8000

# Migrations puis seed idempotent avant de démarrer l'API (identique à la
# commande définie dans docker-compose.yml, qui la remplace de toute façon
# quand le service est lancé via compose — présent ici pour un `docker run`
# autonome).
CMD ["sh", "-c", "cd app && alembic upgrade head && python -m app.database.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
