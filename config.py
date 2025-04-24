# config.py (VERSION v5 - Avec lien Telegram intégré)

import os
from dotenv import load_dotenv

# Chemin vers le répertoire de base de l'application
basedir = os.path.abspath(os.path.dirname(__file__))
# Charge les variables d'environnement depuis le fichier .env
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """Classe de configuration de base."""
    # Clé secrète pour la sécurité des sessions et formulaires CSRF
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'une-cle-secrete-tres-difficile-a-deviner'

    # Configuration de la base de données
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuration pour l'envoi d'emails (Exemple avec Gmail, à adapter)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.googlemail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = [os.environ.get('ADMIN_EMAIL') or 'votre-email-admin@exemple.com']

    # Configuration de la pagination
    COMPLETIONS_PER_PAGE = 15
    USERS_PER_PAGE = 15
    HISTORY_PER_PAGE = 20

    # Configuration de la traduction (Flask-Babel)
    # Assurez-vous que ceci est un dictionnaire
    LANGUAGES = {'en': 'English', 'fr': 'Français', 'it': 'Italiano'}
    BABEL_DEFAULT_LOCALE = 'fr'
    BABEL_DEFAULT_TIMEZONE = 'UTC'

    # Configuration pour les uploads (preuves)
    UPLOAD_FOLDER = os.path.join(basedir, 'app/static/uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # Configuration spécifique à l'application
    MINIMUM_WITHDRAWAL_AMOUNT = float(os.environ.get('MINIMUM_WITHDRAWAL_AMOUNT') or 10.0)
    SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL') or ADMINS[0]
    # <<< LIEN TELEGRAM INTÉGRÉ ICI COMME VALEUR PAR DÉFAUT >>>
    SUPPORT_TELEGRAM_LINK = os.environ.get('SUPPORT_TELEGRAM_LINK') or 'https://t.me/kevkevjunior'