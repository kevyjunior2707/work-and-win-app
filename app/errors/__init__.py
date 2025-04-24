# app/errors/__init__.py
from flask import Blueprint

bp = Blueprint('errors', __name__)

# Importe le module handlers
# Ce fichier contiendra les gestionnaires pour les erreurs (ex: page 404 Not Found)
from app.errors import handlers