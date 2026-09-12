"""Agent SAV autonome (LangGraph) — unique moteur d'orchestration de l'IA.

- `SavAgent.run_turn` : un message client → une réponse (+ ticket éventuel).
- `app.ai.agent.tools` : outils métier sécurisés (RAG, garantie, tickets).
- `app.ai.agent.context.AgentContext` : source de vérité backend injectée dans
  les outils (produit / client / conversation), jamais fournie par le LLM.
"""
from app.ai.agent.context import AgentContext
from app.ai.agent.graph import AgentTurnResult, SavAgent

__all__ = ["AgentContext", "AgentTurnResult", "SavAgent"]
