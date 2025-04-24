# config.py (VERSION COMPLÈTE AVEC INDENTATION CORRIGÉE)

import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    # --- Configuration Générale Flask & Sécurité ---
    # Utilise 4 espaces pour l'indentation ici
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'vous-devez-absolument-definir-une-vraie-cle'
    FLASK_DEBUG = os.environ.get('FLASK_DEBUG') == '1'

    # --- Configuration Base de Données ---
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Configuration Multilingue (Flask-Babel) ---
    LANGUAGES = ['en', 'fr', 'es', 'pt', 'de', 'ar', 'hi', 'zh'] # Compléter
    BABEL_TRANSLATION_DIRECTORIES = os.path.join(basedir, 'translations')
    # Optionnel: Définir une langue par défaut si la détection échoue
    # BABEL_DEFAULT_LOCALE = 'fr'

    # --- Configuration Email (Optionnel - Lignes lues mais non utilisées si Flask-Mail enlevé) ---
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = [os.environ.get('ADMIN_EMAIL')] # Email pour erreurs critiques

    # --- Configuration Spécifique à l'Application ---
    ADMIN_USER_ID = '5004789999' # ID conceptuel Admin
    SUPPORT_EMAIL = 'pp364598@gmail.com' # Email support (vous pouvez aussi le mettre dans .env si vous préférez)
    # Lit le lien Telegram depuis .env, avec fallback
    SUPPORT_TELEGRAM_LINK = os.environ.get('SUPPORT_TELEGRAM_LINK') or 'TELEGRAM_LINK_A_DEFINIR'
    # Montant minimum pour demander un retrait (en $)
    MINIMUM_WITHDRAWAL_AMOUNT = 25.00

    # --- Pagination ---
    COMPLETIONS_PER_PAGE = 25 # Pour historique admin et user

    # --- Configuration Uploads ---
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads') # Dossier pour preuves image
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'} # Extensions autorisées

    # --- Textes Statiques (Exemples) ---
    APP_DESCRIPTION = "Work and Win: Votre plateforme pour trouver et accomplir des tâches rémunérées, adaptées à votre profil et à votre localisation."
    FRAUD_WARNING = "Toute tentative de soumission frauduleuse entraînera la suspension immédiate du compte et l'annulation des gains. Nous comptons sur l'honnêteté de notre communauté."