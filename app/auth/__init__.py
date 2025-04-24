# app/auth/__init__.py
from flask import Blueprint

# Crée une instance de Blueprint nommée 'auth'
# Le premier argument 'auth' est le nom du blueprint
# Le deuxième __name__ aide Flask à localiser les ressources (templates, static)
bp = Blueprint('auth', __name__)

# Importe le module routes à la fin pour éviter les imports circulaires
# Ce fichier contiendra les routes pour /login, /register, /logout etc.
from app.auth import routes