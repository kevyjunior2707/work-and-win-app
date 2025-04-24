# app/__init__.py (VERSION COMPLÈTE v8 - Correction NameError current_app)

import os
from flask import Flask, request, g, current_app # <<< current_app ajouté à l'import flask >>>
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_babel import Babel, lazy_gettext as _l
from sqlalchemy import select, func
from datetime import datetime, timezone # Import datetime déplacé ici pour être sûr

# Initialisation des extensions
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = _l('Veuillez vous connecter pour accéder à cette page.')
login.login_message_category = 'info'
babel = Babel()

# Fonction de sélection de la langue
def get_locale():
    # 1. Essayer d'obtenir la langue depuis l'URL (?lang=en)
    lang = request.args.get('lang')
    # Utilise current_app importé
    if lang and lang in current_app.config['LANGUAGES']:
         return lang
    # 2. Essayer d'obtenir la langue depuis l'en-tête Accept-Language du navigateur
    return request.accept_languages.best_match(current_app.config['LANGUAGES'].keys())
    # 3. Utiliser la langue par défaut si aucune correspondance
    # return current_app.config['BABEL_DEFAULT_LOCALE']

# --- Fonction Factory pour créer l'application ---
def create_app(config_class=Config):
    """Crée et configure une instance de l'application Flask."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Lie les extensions à l'instance de l'application créée
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    babel.init_app(app)

    # Enregistre la fonction localeselector APRÈS init_app
    babel.localeselector_func = get_locale

    # --- Configuration du dossier d'upload ---
    upload_folder = app.config.get('UPLOAD_FOLDER', os.path.join(app.root_path, 'static/uploads'))
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'tasks'), exist_ok=True)

    # Met la locale choisie et l'année actuelle à disposition des templates via 'g'
    @app.before_request
    def before_request():
        g.locale = str(get_locale())
        g.locale_display_name = app.config['LANGUAGES'].get(g.locale, g.locale)
        g.current_year = datetime.now(timezone.utc).year

    # --- Context Processor pour Notifications Non Lues ---
    @app.context_processor
    def inject_notifications():
        unread_count = 0
        from .models import Notification # Import local
        if current_user.is_authenticated and not current_user.is_admin:
            try:
                # Utilise le contexte de l'application pour être sûr d'avoir accès à db
                with app.app_context():
                    unread_count = db.session.scalar(
                        db.select(func.count(Notification.id))
                        .where(Notification.user_id == current_user.id, Notification.is_read == False)
                    ) or 0
            except Exception as e:
                print(f"Erreur lors du comptage des notifications: {e}")
                unread_count = 0
        return dict(unread_notification_count=unread_count)
    # --- Fin Context Processor ---

    # --- Enregistrement des Blueprints ---
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # --- Log de démarrage ---
    if not app.debug and not app.testing:
        pass
    app.logger.info('Work and Win startup')

    return app

# Importe les modèles à la fin
from app import models