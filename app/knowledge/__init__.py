from flask import Blueprint

knowledge_bp = Blueprint(
    "knowledge", __name__, template_folder="templates", url_prefix="/knowledge"
)

from app.knowledge import routes  # noqa: E402, F401
