# app/__init__.py (VERSION COMPLÈTE v10 - Utilisation Session pour Locale)

import os
from flask import Flask, request, g, current_app, session # <<< session ajouté >>>
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_babel import Babel, lazy_gettext as _l
from sqlalchemy import select, func
from datetime import datetime, timezone
import json

# Initialisation des extensions
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = _l('Veuillez vous connecter pour accéder à cette page.')
login.login_message_category = 'info'
babel = Babel()

# Fonction de sélection de la langue (MODIFIÉE pour utiliser la session)
def get_locale():
    # 1. Vérifier si une langue est stockée dans la session
    if 'locale' in session and session['locale'] in current_app.config['LANGUAGES']:
        # print(f"DEBUG get_locale: Using locale from session: {session['locale']}") # Débogage session
        return session['locale']

    # 2. (Optionnel) Essayer l'URL (si on veut toujours pouvoir forcer via URL)
    # lang_from_url = request.args.get('lang')
    # if lang_from_url and lang_from_url in current_app.config['LANGUAGES']:
    #     session['locale'] = lang_from_url # Stocke dans la session pour les prochaines requêtes
    #     print(f"DEBUG get_locale: Using locale from URL (and storing in session): {lang_from_url}")
    #     return lang_from_url

    # 3. Essayer l'en-tête Accept-Language du navigateur
    best_match = request.accept_languages.best_match(current_app.config['LANGUAGES'].keys())
    # print(f"DEBUG get_locale: best_match from browser = {best_match}")
    if best_match:
        # print(f"DEBUG get_locale: Using locale from browser: {best_match}")
        return best_match

    # 4. Utiliser la langue par défaut
    default_locale = current_app.config.get('BABEL_DEFAULT_LOCALE', 'fr') # Mis fr comme défaut
    # print(f"DEBUG get_locale: Using default locale: {default_locale}")
    return default_locale

# --- Fonction Factory pour créer l'application ---
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    babel.init_app(app)

    # Enregistre la fonction localeselector APRÈS init_app
    babel.localeselector_func = get_locale

    upload_folder = app.config.get('UPLOAD_FOLDER', os.path.join(app.root_path, 'static/uploads'))
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'tasks'), exist_ok=True)

    # Met la locale choisie et l'année actuelle à disposition des templates via 'g'
    @app.before_request
    def before_request():
        # <<< MODIFIÉ : Stocke la langue de l'URL dans la session SI présente >>>
        lang_code = request.args.get('lang')
        if lang_code and lang_code in app.config['LANGUAGES']:
            session['locale'] = lang_code
            # print(f"DEBUG before_request: Stored locale '{lang_code}' in session") # Debug session set

        # Utilise get_locale (qui lira la session en priorité maintenant)
        selected_locale = get_locale()
        # print(f"DEBUG before_request: Effective locale for g = {selected_locale}") # Debug final locale
        g.locale = str(selected_locale)
        g.locale_display_name = app.config['LANGUAGES'].get(g.locale, g.locale)
        g.current_year = datetime.now(timezone.utc).year

    # Context Processor pour Notifications Non Lues (inchangé)
    @app.context_processor
    def inject_notifications():
        unread_count = 0
        from .models import Notification
        if current_user.is_authenticated and not current_user.is_admin:
            try:
                with app.app_context():
                    unread_count = db.session.scalar(
                        db.select(func.count(Notification.id))
                        .where(Notification.user_id == current_user.id, Notification.is_read == False)
                    ) or 0
            except Exception as e:
                print(f"Erreur lors du comptage des notifications: {e}")
                unread_count = 0
        return dict(unread_notification_count=unread_count)

    # Enregistrement des Blueprints (inchangé)
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Log de démarrage (inchangé)
    if not app.debug and not app.testing:
        pass
    app.logger.info('Work and Win startup')

    return app

# Importe les modèles à la fin
from app import models