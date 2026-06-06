from __future__ import annotations

import uuid
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository[ModelT]:
    model: type[ModelT]

    def __init__(self, db: Session):
        self.db = db

    def add(self, instance: ModelT) -> ModelT:
        self.db.add(instance)
        self.db.flush()
        return instance

    def get(self, model_id: uuid.UUID) -> ModelT | None:
        return self.db.get(self.model, model_id)

    def list(self, limit: int = 100, offset: int = 0) -> list[ModelT]:
        stmt = select(self.model).limit(limit).offset(offset)
        return list(self.db.scalars(stmt).all())
