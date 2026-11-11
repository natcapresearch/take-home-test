from fastapi import FastAPI
from src.backend.app.errors.errors import *  # noqa: F403
from src.backend.app.errors.registry import registry


def add_exception_handlers(app: FastAPI):
    for exception, handler in registry:
        app.add_exception_handler(exception, handler)
