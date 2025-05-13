# app/__init__.py (VERSION COMPLÈTE v17 - Correction Finale Import Circulaire)

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
login.login_view = 'auth.login'
login.login_message = _l('Veuillez vous connecter pour accéder à cette page.')
login.login_message_category = 'info'
babel = Babel()
mail = Mail()

# Fonction de sélection de la langue (doit utiliser current_app pour la config)
def get_locale():
    lang = request.args.get('lang')
    if lang and lang in current_app.config['LANGUAGES']:
         return lang
    # Si on veut utiliser la session (décommenter si besoin)
    # if 'locale' in session and session['locale'] in current_app.config['LANGUAGES']:
    #     return session['locale']
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
        # Si on utilise la session pour la locale:
        # lang_code_url = request.args.get('lang')
        # if lang_code_url and lang_code_url in app.config['LANGUAGES']:
        #     session['locale'] = lang_code_url


    # --- Processeurs de Contexte (variables globales pour templates) ---
    @app.context_processor
    def inject_notifications():
        unread_count = 0
        # Import local pour éviter dépendance circulaire au démarrage,
        # mais .models sera importé à la fin du fichier __init__.py de toute façon.
        from .models import Notification
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
        from .models import Banner # Import local
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

    @app.context_processor
    def inject_site_settings():
        from .models import SiteSetting # Import local
        settings = None
        custom_head = ''
        custom_footer = ''
        try:
            settings = db.session.scalars(select(SiteSetting).filter_by(id=1).limit(1)).first()
            if settings:
                custom_head = settings.custom_head_scripts or ''
                custom_footer = settings.custom_footer_scripts or ''
        except Exception as e:
            app.logger.warning(f"Erreur lors de la récupération des SiteSettings: {e}")
        
        return dict(
            custom_head_scripts=custom_head,
            custom_footer_scripts=custom_footer
        )
    # --- Fin Processeurs de Contexte ---

    # --- Enregistrement des Blueprints ---
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    # Ne pas oublier d'importer et enregistrer d'autres blueprints si vous en créez (ex: blog)

    # --- Log de démarrage ---
    if not app.debug and not app.testing:
        # Configuration de logs plus avancés pour la production ici si nécessaire
        pass
    app.logger.info('Work and Win startup')

    return app

# <<< L'IMPORT DES MODÈLES EST CRUCIALEMENT À LA FIN DU FICHIER >>>
from app import models
