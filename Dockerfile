FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1 \
	PYTHONPATH=/app

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

EXPOSE 8000

# Migrations puis seed idempotent avant de démarrer l'API (identique à la
# commande définie dans docker-compose.yml, qui la remplace de toute façon
# quand le service est lancé via compose — présent ici pour un `docker run`
# autonome).
CMD ["sh", "-c", "cd app && alembic upgrade head && python -m app.database.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
