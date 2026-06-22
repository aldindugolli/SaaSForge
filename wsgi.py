"""WSGI entry point for production."""
from app import create_app

app = create_app()
