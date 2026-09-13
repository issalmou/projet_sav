"""Mesure réelle (aucun mock) du temps d'exécution des routes de chat.

Exclu par défaut (marker `external`, comme les autres tests réseau réels du
projet) car il appelle le vrai fournisseur LLM configuré dans `.env`
(Gemini) et charge le vrai modèle E5. Lancer explicitement :

    pytest -m external -k test_chat_response_timing -s

`-s` est nécessaire pour voir les temps affichés (sinon capturés par pytest).
"""
import time

import pytest

from app.ai.embeddings.e5_embedding_provider import _load_model_cached
from app.ai.embeddings.warmup import _background_tasks, warm_embedding_model_in_background
from app.schemas.client_product import ClientProductItem
from app.schemas.user import UserCreate
from app.services.chat_service import ChatService
from app.services.client_product_service import ClientProductService
from app.services.user_service import UserService
from conftest import unique_email


@pytest.mark.external
@pytest.mark.asyncio
async def test_chat_response_timing(db_session, role_ids, product_id, monkeypatch):
    """Chronomètre, avec les vrais fournisseurs (.env), la création d'une
    conversation puis 2 tours de chat consécutifs — pour objectiver l'effet
    du cache E5/ChromaDB, de l'agent paresseux et du préchauffage en tâche de
    fond, plutôt que de le supposer.
    """

    # Ce test veut le VRAI préchauffage (le conftest global le neutralise par
    # défaut pour ne pas alourdir les autres tests) : import direct de la
    # fonction réelle, avant que le fixture autouse ne la remplace ailleurs.
    monkeypatch.setattr("app.services.chat_service.warm_embedding_model_in_background", warm_embedding_model_in_background)

    us = UserService(db_session)
    client = await us.create_user(
        UserCreate(email=unique_email("timing"), password="ValidPass1", role_id=role_ids["client"])
    )
    await ClientProductService(db_session).assign_products(
        client.id, [ClientProductItem(product_id=product_id, qte=1)]
    )

    service = ChatService(db_session)  # aucun override : vrai LLM (Gemini) + vrai embedder (E5)

    was_cached_before = _load_model_cached.cache_info().currsize > 0
    print(f"\n[TIMING] modèle E5 déjà en cache avant ce test : {was_cached_before}")

    # --- 1. Création de conversation : ne doit jamais construire l'agent -----
    t0 = time.perf_counter()
    conversation = await service.open_conversation(client, product_id)
    t_open = time.perf_counter() - t0
    print(f"[TIMING] open_conversation           : {t_open * 1000:8.1f} ms")

    # Le préchauffage vient d'être lancé en tâche de fond par open_conversation
    # ci-dessus : on l'attend explicitement ici pour PROUVER qu'il a bien
    # chargé le modèle avant le premier message (plutôt que de deviner via un
    # sleep arbitraire).
    tasks = list(_background_tasks)
    assert tasks, "le préchauffage n'a pas été planifié par open_conversation"
    t0 = time.perf_counter()
    await tasks[-1]
    t_warmup = time.perf_counter() - t0
    print(f"[TIMING] préchauffage E5 en arrière-plan : {t_warmup * 1000:8.1f} ms")
    assert _load_model_cached.cache_info().currsize > 0, "le modèle E5 doit être chargé après le préchauffage"

    # --- 2. Premier tour de chat : modèle déjà chaud grâce au préchauffage --
    t0 = time.perf_counter()
    result1 = await service.handle_message(client, conversation.id, "Mon produit ne s'allume plus, que faire ?")
    t_msg1 = time.perf_counter() - t0
    print(f"[TIMING] handle_message #1 (modèle déjà chaud) : {t_msg1 * 1000:8.1f} ms")

    # --- 3. Second tour : mesure de référence, sans rechargement de modèle --
    t0 = time.perf_counter()
    result2 = await service.handle_message(client, conversation.id, "J'ai déjà vérifié le câble, ça persiste.")
    t_msg2 = time.perf_counter() - t0
    print(f"[TIMING] handle_message #2                     : {t_msg2 * 1000:8.1f} ms")

    assert t_open < 1.0, f"open_conversation trop lent ({t_open:.2f}s) : l'agent ne devrait pas être construit sur cette route"
    assert result1.message.content
    assert result2.message.content

    await db_session.delete(await us.get_user_by_id(client.id))
    await db_session.commit()


__all__: list[str] = []
