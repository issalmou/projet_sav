"""Fournisseurs LLM interchangeables.

Chaque module de ce paquet implémente `LLMProvider` (base.py) pour un
fournisseur donné. Le reste de l'application ne doit importer que
`app.ai.providers.factory.LLMProviderFactory`, jamais un provider concret.
"""
