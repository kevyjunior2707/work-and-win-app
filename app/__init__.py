# app/__init__.py (COMPLET avec tentative init_app pour locale - v11)
from flask import Flask, request, current_app
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
# from flask_mail import Mail # Commenté/Supprimé
from flask_babel import Babel, lazy_gettext as _l, get_locale as babel_get_locale
import logging
from logging.handlers import RotatingFileHandler
import os
import json
from datetime import datetime, timezone

# --- Définition de la fonction de sélection de langue (globale) AVEC DEBUG ---
# (Cette fonction sera passée à init_app)
def get_locale_selector():
    lang = request.args.get('lang')
    print(f"DEBUG flask-babel: Lang from URL = {lang}") # DEBUG
    if lang and lang in current_app.config['LANGUAGES']:
        print(f"DEBUG flask-babel: Using locale from URL: {lang}") # DEBUG
        return lang
    accept_lang = request.accept_languages.best_match(current_app.config['LANGUAGES'])
    print(f"DEBUG flask-babel: Lang from Accept-Language = {accept_lang}") # DEBUG
    if accept_lang:
         print(f"DEBUG flask-babel: Using locale from browser: {accept_lang}") # DEBUG
         return accept_lang
    default_lang = current_app.config.get('BABEL_DEFAULT_LOCALE', 'en')
    print(f"DEBUG flask-babel: Using default locale: {default_lang}") # DEBUG
    return default_lang

# --- Initialisation des extensions ---
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = _l('Veuillez vous connecter pour accéder à cette page.')
# mail = Mail() # Commenté/Supprimé
# <<< MODIFICATION ICI : Initialise Babel SANS le sélecteur ici >>>
babel = Babel()

# --- Factory de l'Application ---
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Filtre Jinja pour JSON
    app.jinja_env.filters['fromjson'] = json.loads

    # Initialisation des extensions AVEC application
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    # mail.init_app(app) # Commenté/Supprimé
    # <<< MODIFICATION ICI : Passe le sélecteur LORS de l'appel à init_app >>>
    babel.init_app(app, locale_selector=get_locale_selector)

    # --- Processeur de Contexte (Injecte dans les Templates) ---
    @app.context_processor
    def inject_template_globals():
        return dict(
            get_locale=babel_get_locale, # Fonction pour obtenir la langue choisie
            current_year=datetime.now(timezone.utc).year
        )

    # Enregistrement des Blueprints
    from app.errors import bp as errors_bp; app.register_blueprint(errors_bp)
    from app.auth import bp as auth_bp; app.register_blueprint(auth_bp, url_prefix='/auth')
    from app.main import bp as main_bp; app.register_blueprint(main_bp)
    from app.admin import bp as admin_bp; app.register_blueprint(admin_bp, url_prefix='/admin')

    # Configuration du Logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'): os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/work_and_win.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO); app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO); app.logger.info('Work and Win startup')

    return app

# Import des modèles à la fin
from app import models