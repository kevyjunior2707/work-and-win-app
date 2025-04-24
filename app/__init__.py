# app/__init__.py (VERSION COMPLÈTE v6 - Re-vérification Décorateur Babel)

import os
from flask import Flask, request, g # g ajouté pour la langue
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user # current_user ajouté pour context processor
from flask_babel import Babel, lazy_gettext as _l # Babel ajouté
# Ajout pour le context processor
from sqlalchemy import select, func # Ajout func pour count

# Initialisation des extensions (sans lier à une app spécifique pour l'instant)
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = _l('Veuillez vous connecter pour accéder à cette page.')
login.login_message_category = 'info'
babel = Babel() # Initialisation de Babel

# --- Fonction Factory pour créer l'application ---
def create_app(config_class=Config):
    """Crée et configure une instance de l'application Flask."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Lie les extensions à l'instance de l'application créée
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    babel.init_app(app) # Lie Babel à l'app

    # --- Configuration du dossier d'upload ---
    upload_folder = app.config.get('UPLOAD_FOLDER', os.path.join(app.root_path, 'static/uploads'))
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'tasks'), exist_ok=True)

    # --- Sélection de la langue ---
    @babel.localeselector
    def get_locale():
        # 1. Essayer d'obtenir la langue depuis l'URL (?lang=en)
        lang = request.args.get('lang')
        if lang and lang in app.config['LANGUAGES']:
            return lang
        # 2. Essayer d'obtenir la langue depuis l'en-tête Accept-Language du navigateur
        return request.accept_languages.best_match(app.config['LANGUAGES'].keys())
        # 3. Utiliser la langue par défaut si aucune correspondance
        # return app.config['BABEL_DEFAULT_LOCALE'] # Décommenter si nécessaire

    # Met la locale choisie et l'année actuelle à disposition des templates via 'g'
    @app.before_request
    def before_request():
        g.locale = str(get_locale())
        g.locale_display_name = app.config['LANGUAGES'].get(g.locale, g.locale)
        # Import datetime ici pour éviter import circulaire potentiel au démarrage
        from datetime import datetime, timezone
        g.current_year = datetime.now(timezone.utc).year

    # --- Context Processor pour Notifications Non Lues ---
    @app.context_processor
    def inject_notifications():
        unread_count = 0
        # Import local pour éviter dépendance circulaire au démarrage
        from .models import Notification
        if current_user.is_authenticated and not current_user.is_admin:
            try:
                unread_count = db.session.scalar(
                    db.select(func.count(Notification.id)) # Utilise func.count
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
        pass # Configuration logs production ici si besoin
    app.logger.info('Work and Win startup')

    return app

# Importe les modèles à la fin
from app import models