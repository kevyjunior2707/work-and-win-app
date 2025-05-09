# app/__init__.py (VERSION COMPLÈTE v15 - Correction Import Circulaire)

import os
from flask import Flask, request, g, current_app, session
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_babel import Babel, lazy_gettext as _l
from flask_mail import Mail
from sqlalchemy import select, func
from datetime import datetime, timezone
import json

# Initialisation des extensions (SANS app au niveau global)
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login' # Point d'entrée pour la page de connexion
login.login_message = _l('Veuillez vous connecter pour accéder à cette page.')
login.login_message_category = 'info' # Catégorie Bootstrap pour le message flash
babel = Babel()
mail = Mail()

# Fonction de sélection de la langue (doit utiliser current_app pour la config)
def get_locale():
    lang = request.args.get('lang')
    if lang and lang in current_app.config['LANGUAGES']:
         return lang
    best_match = request.accept_languages.best_match(current_app.config['LANGUAGES'].keys())
    if best_match:
        return best_match
    return current_app.config.get('BABEL_DEFAULT_LOCALE', 'fr')

# --- Fonction Factory pour créer l'application ---
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Lie les extensions à l'instance de l'application créée
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    mail.init_app(app)

    # --- Configuration du dossier d'upload ---
    upload_folder = app.config.get('UPLOAD_FOLDER', os.path.join(app.root_path, 'static/uploads'))
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'tasks'), exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'banners'), exist_ok=True)

    # --- Fonctions exécutées avant chaque requête ---
    @app.before_request
    def before_request():
        selected_locale = get_locale()
        g.locale = str(selected_locale)
        g.locale_display_name = app.config['LANGUAGES'].get(g.locale, g.locale)
        g.current_year = datetime.now(timezone.utc).year

    # --- Processeurs de Contexte (variables globales pour templates) ---
    @app.context_processor
    def inject_notifications():
        unread_count = 0
        # Import local pour éviter dépendance circulaire au démarrage
        # et pour que le modèle Notification soit déjà connu par SQLAlchemy via l'import final
        from .models import Notification
        if current_user.is_authenticated and not current_user.is_admin:
            try:
                # Utilise le contexte de l'application pour être sûr d'avoir accès à db
                # Cela est implicite si le context processor est appelé pendant une requête
                unread_count = db.session.scalar(
                    db.select(func.count(Notification.id))
                    .where(Notification.user_id == current_user.id, Notification.is_read == False)
                ) or 0
            except Exception as e:
                # En cas d'erreur (ex: BDD pas encore initialisée pendant les migrations),
                # évite de planter toute l'application.
                app.logger.error(f"Erreur lors du comptage des notifications: {e}")
                unread_count = 0
        return dict(unread_notification_count=unread_count)

    @app.context_processor
    def inject_banners():
        active_top_banner = None
        active_bottom_banner = None
        # Import local
        from .models import Banner
        try:
            # Pas besoin de app.app_context() ici car on est déjà dans un contexte de requête
            active_top_banner = db.session.scalars(
                select(Banner).where(
                    Banner.is_active == True,
                    Banner.display_location.in_(['top', 'top_bottom'])
                ).order_by(Banner.uploaded_at.desc())
            ).first()
            active_bottom_banner = db.session.scalars(
                select(Banner).where(
                    Banner.is_active == True,
                    Banner.display_location.in_(['bottom', 'top_bottom'])
                ).order_by(Banner.uploaded_at.desc())
            ).first()
        except Exception as e:
            app.logger.error(f"Erreur lors de la récupération des bannières: {e}")
        return dict(
            active_top_banner=active_top_banner,
            active_bottom_banner=active_bottom_banner
        )
    # --- Fin Processeurs de Contexte ---

    # --- Enregistrement des Blueprints ---
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # --- Log de démarrage ---
    if not app.debug and not app.testing:
        # Configuration de logs plus avancés pour la production ici si nécessaire
        pass
    app.logger.info('Work and Win startup')

    return app

# <<< L'IMPORT DES MODÈLES EST MAINTENANT À LA FIN >>>
from app import models