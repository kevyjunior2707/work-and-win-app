# app/__init__.py (VERSION COMPLÈTE v17 - Context Processor pour CustomScript)

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
# <<< Import des modèles Notification, Banner, et CustomScript >>>
from .models import Notification, Banner, CustomScript # SiteSetting a été remplacé par CustomScript

# Initialisation des extensions
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = _l('Veuillez vous connecter pour accéder à cette page.')
login.login_message_category = 'info'
babel = Babel()
mail = Mail()

# Fonction de sélection de la langue
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

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    mail.init_app(app)

    upload_folder = app.config.get('UPLOAD_FOLDER', os.path.join(app.root_path, 'static/uploads'))
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'tasks'), exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'banners'), exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'blog_posts'), exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'proofs'), exist_ok=True)

    @app.before_request
    def before_request():
        selected_locale = get_locale()
        g.locale = str(selected_locale)
        g.locale_display_name = app.config['LANGUAGES'].get(g.locale, g.locale)
        g.current_year = datetime.now(timezone.utc).year

    @app.context_processor
    def inject_notifications():
        unread_count = 0
        # Notification est déjà importé en haut du fichier
        if current_user.is_authenticated and not current_user.is_admin:
            try:
                unread_count = db.session.scalar(
                    db.select(func.count(Notification.id))
                    .where(Notification.user_id == current_user.id, Notification.is_read == False)
                ) or 0
            except Exception as e:
                app.logger.error(f"Erreur lors du comptage des notifications: {e}")
                unread_count = 0
        return dict(unread_notification_count=unread_count)

    @app.context_processor
    def inject_banners():
        active_top_banner = None
        active_bottom_banner = None
        # Banner est déjà importé en haut du fichier
        try:
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

    # <<< NOUVEAU CONTEXT PROCESSOR POUR LES SCRIPTS PERSONNALISÉS >>>
    @app.context_processor
    def inject_custom_scripts():
        # CustomScript est déjà importé en haut du fichier
        head_scripts_list = []
        footer_scripts_list = []
        try:
            # Récupère tous les scripts actifs
            active_scripts = db.session.scalars(
                select(CustomScript).where(CustomScript.is_active == True)
            ).all()

            for script in active_scripts:
                excluded = script.get_excluded_endpoints_list()
                # Vérifie si l'endpoint actuel n'est PAS dans la liste d'exclusion du script
                if request.endpoint not in excluded:
                    if script.location == 'head':
                        head_scripts_list.append(script.script_code)
                    elif script.location == 'footer':
                        footer_scripts_list.append(script.script_code)
        except Exception as e:
            app.logger.warning(f"Erreur lors de la récupération des CustomScripts: {e}")
            # Ne pas planter l'application
        
        return dict(
            global_custom_head_scripts=head_scripts_list,  # Renommé pour éviter conflit potentiel
            global_custom_footer_scripts=footer_scripts_list # Renommé pour éviter conflit potentiel
        )
    # <<< FIN NOUVEAU CONTEXT PROCESSOR >>>

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    if not app.debug and not app.testing:
        pass
    app.logger.info('Work and Win startup')

    return app

# L'import des modèles est crucial et doit rester à la fin
from app import models
