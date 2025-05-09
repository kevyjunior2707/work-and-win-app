# app/__init__.py (VERSION COMPLÈTE v14 - Ajout Context Processor Bannières)

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
# <<< Import du modèle Banner >>>
from .models import Notification, Banner # Ajout de Banner ici

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
    os.makedirs(os.path.join(upload_folder, 'banners'), exist_ok=True) # Crée dossier banners

    @app.before_request
    def before_request():
        selected_locale = get_locale()
        g.locale = str(selected_locale)
        g.locale_display_name = app.config['LANGUAGES'].get(g.locale, g.locale)
        g.current_year = datetime.now(timezone.utc).year

    @app.context_processor
    def inject_notifications():
        unread_count = 0
        # from .models import Notification # Déjà importé en haut du fichier
        if current_user.is_authenticated and not current_user.is_admin:
            try:
                with app.app_context(): # Assure d'être dans le contexte de l'app
                    unread_count = db.session.scalar(
                        db.select(func.count(Notification.id))
                        .where(Notification.user_id == current_user.id, Notification.is_read == False)
                    ) or 0
            except Exception as e:
                print(f"Erreur lors du comptage des notifications: {e}")
                unread_count = 0
        return dict(unread_notification_count=unread_count)

    # <<< NOUVEAU CONTEXT PROCESSOR POUR LES BANNIÈRES >>>
    @app.context_processor
    def inject_banners():
        # from .models import Banner # Déjà importé en haut du fichier
        active_top_banner = None
        active_bottom_banner = None
        try:
            with app.app_context(): # Assure d'être dans le contexte de l'app
                # Cherche une bannière active pour le haut (ou haut et bas)
                active_top_banner = db.session.scalars(
                    select(Banner).where(
                        Banner.is_active == True,
                        Banner.display_location.in_(['top', 'top_bottom'])
                    ).order_by(Banner.uploaded_at.desc()) # Prend la plus récente si plusieurs
                ).first()

                # Cherche une bannière active pour le bas (ou haut et bas)
                active_bottom_banner = db.session.scalars(
                    select(Banner).where(
                        Banner.is_active == True,
                        Banner.display_location.in_(['bottom', 'top_bottom'])
                    ).order_by(Banner.uploaded_at.desc()) # Prend la plus récente si plusieurs
                ).first()
        except Exception as e:
            print(f"Erreur lors de la récupération des bannières: {e}")
            # Ne pas planter l'application si la base n'est pas prête (ex: pendant les migrations initiales)

        return dict(
            active_top_banner=active_top_banner,
            active_bottom_banner=active_bottom_banner
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

from app import models # Garder cet import à la fin