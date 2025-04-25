# config.py (VERSION v7 - Utilisation work.and.win.online@gmail.com)

import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """Classe de configuration de base."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'une-cle-secrete-tres-difficile-a-deviner'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Configuration Email (Flask-Mail) ---
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.googlemail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    # Utilise la nouvelle adresse comme défaut si non défini dans .env
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'work.and.win.online@gmail.com'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') # Doit être défini dans .env ou variables serveur !
    ADMINS = [os.environ.get('ADMIN_EMAIL') or 'votre-email-admin@exemple.com']
    # Utilise la nouvelle adresse comme expéditeur par défaut
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or ('Work and Win', 'work.and.win.online@gmail.com') # Tuple (Nom, Email)

    # --- Configuration Babel ---
    LANGUAGES = {'en': 'English', 'fr': 'Français', 'it': 'Italiano'}
    BABEL_DEFAULT_LOCALE = 'fr'
    BABEL_DEFAULT_TIMEZONE = 'UTC'

    # --- Configuration Uploads ---
    UPLOAD_FOLDER = os.path.join(basedir, 'app/static/uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # --- Configuration Application ---
    MINIMUM_WITHDRAWAL_AMOUNT = float(os.environ.get('MINIMUM_WITHDRAWAL_AMOUNT') or 10.0)
    # <<< Utilise la nouvelle adresse comme email de support par défaut >>>
    SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL') or 'work.and.win.online@gmail.com'
    SUPPORT_TELEGRAM_LINK = os.environ.get('SUPPORT_TELEGRAM_LINK') or 'https://t.me/kevkevjunior'

    # --- Pagination ---
    COMPLETIONS_PER_PAGE = 15
    USERS_PER_PAGE = 15
    HISTORY_PER_PAGE = 20