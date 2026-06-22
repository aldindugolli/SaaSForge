from typing import Optional, List, Type, TypeVar, Generic
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from app.core.extensions import db

T = TypeVar("T")


class ServiceError(Exception):
    """Base exception for service layer errors."""

    def __init__(self, message: str, code: str = "service_error", details: Optional[dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(ServiceError):
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, code="validation_error", details=details)


class NotFoundError(ServiceError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, code="not_found")


class PermissionError(ServiceError):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, code="permission_denied")


class BaseService(Generic[T]):
    """Base service with common CRUD operations."""

    def __init__(self, model: Type[T]):
        self.model = model

    def get_by_id(self, id: str) -> Optional[T]:
        return db.session.get(self.model, id)

    def get_all(self, **filters) -> List[T]:
        query = self.model.query
        for key, value in filters.items():
            if value is not None:
                query = query.filter(getattr(self.model, key) == value)
        return query.all()

    def create(self, **kwargs) -> T:
        instance = self.model(**kwargs)
        db.session.add(instance)
        try:
            db.session.commit()
            return instance
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ServiceError(f"Failed to create {self.model.__name__}: {str(e)}")

    def update(self, id: str, **kwargs) -> T:
        instance = self.get_by_id(id)
        if not instance:
            raise NotFoundError(f"{self.model.__name__} not found")
        for key, value in kwargs.items():
            if value is not None:
                setattr(instance, key, value)
        try:
            db.session.commit()
            return instance
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ServiceError(f"Failed to update {self.model.__name__}: {str(e)}")

    def delete(self, id: str) -> bool:
        instance = self.get_by_id(id)
        if not instance:
            raise NotFoundError(f"{self.model.__name__} not found")
        db.session.delete(instance)
        try:
            db.session.commit()
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ServiceError(f"Failed to delete {self.model.__name__}: {str(e)}")
