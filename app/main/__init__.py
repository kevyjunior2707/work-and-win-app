# app/main/__init__.py
from flask import Blueprint

bp = Blueprint('main', __name__)

# Importe le module routes
# Ce fichier contiendra les routes principales (page d'accueil, tableau de bord user, etc.)
from app.main import routes