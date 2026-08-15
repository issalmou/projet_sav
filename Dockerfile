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

RUN python -m pip install --upgrade pip \
	&& pip install -r requirements.txt

# Le code s'importe partout comme `app.xxx` (ex: CMD ci-dessous) : le
# contexte de build est le contenu du package `app`, il doit donc être copié
# dans un sous-dossier `app/` et non à la racine `/app`, sous peine de
# `ModuleNotFoundError: No module named 'app'` au démarrage d'uvicorn.
COPY . ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
