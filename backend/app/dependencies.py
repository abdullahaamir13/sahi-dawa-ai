"""Shared FastAPI dependencies: process-wide repository singletons."""

from functools import lru_cache

from app.services.catalogue import CatalogueRepository, default_catalogue_path
from app.services.history import HistoryRepository


@lru_cache(maxsize=1)
def get_catalogue_repository() -> CatalogueRepository:
    return CatalogueRepository.from_csv(default_catalogue_path())


@lru_cache(maxsize=1)
def get_history_repository() -> HistoryRepository:
    return HistoryRepository()
