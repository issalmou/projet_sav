# Scénario de démonstration — Plateforme IA SAV (Semaine 8)

Ce scénario suit strictement le flux du CDC :

```
Client → Chat → RAG → Diagnostic → Solution
                                  → (si non résolu) Ticket → Escalade
```

Chaque étape indique si elle se fait **en direct via l'API (Swagger)** ou **via script** (pour les parties non exposées en HTTP — voir note en fin de document). Rien n'est ajouté qui ne soit pas déjà implémenté et testé.

## Prérequis

- API démarrée (Docker : `docker compose up -d`, ou local : `uvicorn app.main:app --reload` depuis `backend/`)
- Swagger accessible : `http://localhost:8000/docs`
- Rôles et premier admin déjà seedés (`python -m app.database.seed`)

## Partie A — Préparation (une fois, avant la démo)

1. **Connexion staff.** `POST /auth/login` avec le compte administrateur (`FIRST_ADMIN_EMAIL`).
2. **Créer le produit démo.** `POST /products/` :
   ```json
   { "reference": "PAC-DEMO-01", "name": "Pompe à chaleur", "category": "products", "warranty_months": 60 }
   ```
3. **Déposer un document réel de la base de connaissances.** `POST /documents/upload` (staff Responsable SAV/admin), fichier `knowledge_base/products/Les avantages des pompes à chaleur.docx`, `category=products`, `product_ids=[<id du produit créé>]`.
4. **Indexer le document.** Aucune route API n'appelle l'indexation (upload et indexation sont deux étapes distinctes dans `DocumentService`, jamais reliées par une route) — à exécuter une fois, depuis `backend/` :
   ```bash
   PYTHONPATH=. python -c "
   import asyncio
   from app.database.session import AsyncSessionLocal
   from app.services.document import DocumentService

   async def main():
       async with AsyncSessionLocal() as s:
           result = await DocumentService(s).index_pending_documents()
           print(f'{len(result)} document(s) indexé(s)')

   asyncio.run(main())
   "
   ```

## Partie B — Chat + RAG (en direct, Swagger)

1. Se connecter avec un compte **Client** (`POST /auth/login`).
2. `POST /chat/message` :
   ```json
   { "content": "Quels sont les avantages d'une pompe à chaleur ?", "product_id": "<id du produit>" }
   ```
   → La réponse doit citer des éléments du document réellement déposé (preuve que le RAG retrouve le bon contexte, pas une réponse générique du LLM seul).
3. `GET /chat/conversations/{id}` → historique complet, prompt système + contexte documentaire visibles côté serveur (logs) si besoin d'appuyer la démonstration.

## Partie C — Diagnostic → Escalade → Ticket (script, voir note)

Le diagnostic/l'escalade n'ont pas de route HTTP dédiée : cette logique vit entièrement
dans l'agent LangGraph (`app.ai.agent`), piloté via `POST /chat/message` — le même
endpoint que la Partie B, pas un service séparé. Exécuter, depuis `backend/` :

```bash
PYTHONPATH=. python app/demo/demo_diagnostic.py --live
```

Ce script :
1. Envoie une première question technique sur une panne de pompe à chaleur → le RAG ne
   trouve rien de pertinent (notre base documentaire couvre les avantages/primes, pas le
   dépannage) → le garde-fou backend (B6) impose quand même search_docs PUIS
   submit_diagnosis avant toute réponse ; l'agent propose une vérification, conformément
   à la règle CDC §14 (jamais d'escalade dès le 1er message).
2. Envoie une seconde question confirmant que le problème persiste → l'agent enregistre
   l'échec (record_client_feedback), relance un nouveau diagnostic (obligatoire tant que
   le seuil d'échecs n'est pas atteint), et transmet la demande explicite de ticket.
3. Confirme au 3e message → **ticket réellement créé et persisté en base**, transmis à
   un technicien.

Le mode `--live` utilise le vrai LLM configuré : la décision finale (résolu/escaladé) n'est pas scriptée, c'est une vraie réponse du modèle. Pour une démonstration garantie reproductible (ex. présentation enregistrée), utiliser `--deterministic` à la place (séquence de réponses fixes correspondant à l'enchaînement réel imposé par le garde-fou B6).

## Partie D — Traitement du ticket (en direct, Swagger)

1. Reconnexion staff (Responsable SAV/Administrateur).
2. `GET /tickets/` → le ticket créé par le script apparaît, statut `open`.
3. `PATCH /tickets/{id}` → assigner un technicien (`assigned_technician_id`).
4. Reconnexion **Technicien** assigné → `PATCH /tickets/{id}` → statut `resolved` ou `closed`.

## Partie E — Garantie (en direct, Swagger, bonus rapide)

`GET /warranties/{product_id}` → confirme la garantie du produit (24 mois par défaut sur l'exemple).

---

## Note — pourquoi certaines étapes passent par un script

Le diagnostic/l'escalade (Partie C) passent désormais par `POST /chat/message`, comme
la Partie B — la seule raison d'utiliser `demo_diagnostic.py` plutôt que Swagger est de
rejouer une séquence de messages en une seule commande. Seule l'indexation des documents
(`services/document.py::index_pending_documents`) n'a **jamais été exposée par une route
API** — ce n'était pas une exigence explicite du CDC. Plutôt que d'ajouter maintenant une
route non prévue (décision qui vous appartient), la démonstration l'utilise directement
en Python, exactement comme le fait déjà la suite de tests. Si vous souhaitez exposer
cette route pour de futures démonstrations, c'est une décision à valider séparément.
