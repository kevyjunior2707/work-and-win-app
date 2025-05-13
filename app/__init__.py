# app/__init__.py (VERSION COMPLÈTE v18 - Correction Finale Import Circulaire)

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
# Ces objets seront liés à l'application dans create_app
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
    # Crée les dossiers s'ils n'existent pas
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'tasks'), exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'banners'), exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'blog_posts'), exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'proofs'), exist_ok=True)


    # --- Fonctions exécutées avant chaque requête ---
    @app.before_request
    def before_request():
        selected_locale = get_locale()
        g.locale = str(selected_locale)
        g.locale_display_name = app.config['LANGUAGES'].get(g.locale, g.locale)
        g.current_year = datetime.now(timezone.utc).year


    # --- Processeurs de Contexte (variables globales pour templates) ---
    # L'import des modèles se fera à la fin de ce fichier pour éviter les imports circulaires
    # avec les context processors qui pourraient les utiliser.

    @app.context_processor
    def inject_notifications():
        unread_count = 0
        if current_user.is_authenticated and not current_user.is_admin and hasattr(app, 'models'): # Vérifie si app.models est chargé
            try:
                unread_count = db.session.scalar(
                    db.select(func.count(app.models.Notification.id)) # Utilise app.models.Notification
                    .where(app.models.Notification.user_id == current_user.id, app.models.Notification.is_read == False)
                ) or 0
            except Exception as e:
                app.logger.error(f"Erreur lors du comptage des notifications: {e}")
                unread_count = 0
        return dict(unread_notification_count=unread_count)

    @app.context_processor
    def inject_banners():
        active_top_banner = None
        active_bottom_banner = None
        if hasattr(app, 'models'): # Vérifie si app.models est chargé
            try:
                active_top_banner = db.session.scalars(
                    select(app.models.Banner).where( # Utilise app.models.Banner
                        app.models.Banner.is_active == True,
                        app.models.Banner.display_location.in_(['top', 'top_bottom'])
                    ).order_by(app.models.Banner.uploaded_at.desc())
                ).first()
                active_bottom_banner = db.session.scalars(
                    select(app.models.Banner).where(
                        app.models.Banner.is_active == True,
                        app.models.Banner.display_location.in_(['bottom', 'top_bottom'])
                    ).order_by(app.models.Banner.uploaded_at.desc())
                ).first()
            except Exception as e:
                app.logger.error(f"Erreur lors de la récupération des bannières: {e}")
        return dict(
            active_top_banner=active_top_banner,
            active_bottom_banner=active_bottom_banner
        )

    @app.context_processor
    def inject_custom_scripts():
        head_scripts_list = []
        footer_scripts_list = []
        if hasattr(app, 'models'): # Vérifie si app.models est chargé
            try:
                active_scripts = db.session.scalars(
                    select(app.models.CustomScript).where(app.models.CustomScript.is_active == True) # Utilise app.models.CustomScript
                ).all()

                for script in active_scripts:
                    excluded = script.get_excluded_endpoints_list()
                    if request.endpoint not in excluded:
                        if script.location == 'head':
                            head_scripts_list.append(script.script_code)
                        elif script.location == 'footer':
                            footer_scripts_list.append(script.script_code)
            except Exception as e:
                app.logger.warning(f"Erreur lors de la récupération des CustomScripts: {e}")
        
        return dict(
            global_custom_head_scripts=head_scripts_list,
            global_custom_footer_scripts=footer_scripts_list
        )
    # --- Fin Processeurs de Contexte ---

    # --- Enregistrement des Blueprints ---
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    # Ne pas oublier d'importer et enregistrer d'autres blueprints si vous en créez

    # --- Log de démarrage ---
    if not app.debug and not app.testing:
        pass
    app.logger.info('Work and Win startup')

    return app

# <<< L'IMPORT DES MODÈLES EST CRUCIALEMENT À LA FIN DU FICHIER >>>
# Cela permet à 'db', 'login', etc., d'être définis avant que models.py ne les importe.
from app import models
# Ajoute les modèles à l'objet app pour que les context processors puissent y accéder sans import circulaire direct
# app.models = models # Cette ligne n'est pas standard et peut causer des problèmes. On utilise directement les modèles dans les context processors après l'import.
