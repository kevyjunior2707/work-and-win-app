# app/__init__.py (VERSION COMPLÈTE v5 - Avec Context Processor Notif)

import os
from flask import Flask, request, g # g ajouté pour la langue
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_babel import Babel, lazy_gettext as _l # Babel ajouté
# Ajout pour le context processor
from flask_login import current_user
from sqlalchemy import select

# Initialisation des extensions (sans lier à une app spécifique pour l'instant)
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
# Point d'entrée pour la page de connexion (requis par Flask-Login)
login.login_view = 'auth.login'
# Message à afficher quand un utilisateur essaie d'accéder à une page protégée
login.login_message = _l('Veuillez vous connecter pour accéder à cette page.')
login.login_message_category = 'info' # Catégorie Bootstrap pour le message flash
babel = Babel() # Initialisation de Babel

# --- Fonction Factory pour créer l'application ---
def create_app(config_class=Config):
    """Crée et configure une instance de l'application Flask."""
    app = Flask(__name__)
    # Charge la configuration depuis la classe Config (ou une autre passée en argument)
    app.config.from_object(config_class)

    # Lie les extensions à l'instance de l'application créée
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    babel.init_app(app) # Lie Babel à l'app

    # --- Configuration du dossier d'upload ---
    # S'assure que le dossier UPLOAD_FOLDER existe
    # Note: Sur Render, ce dossier sera probablement effacé lors des redéploiements
    # si vous n'utilisez pas un "disque persistant" (option payante).
    # Pour les preuves, un stockage externe (comme S3) serait plus robuste à long terme.
    upload_folder = app.config.get('UPLOAD_FOLDER', os.path.join(app.root_path, 'static/uploads'))
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'tasks'), exist_ok=True) # Crée aussi le sous-dossier tasks

    # --- Sélection de la langue ---
    @babel.localeselector
    def get_locale():
        # 1. Essayer d'obtenir la langue depuis l'URL (?lang=en)
        lang = request.args.get('lang')
        if lang and lang in app.config['LANGUAGES']:
            return lang
        # 2. Essayer d'obtenir la langue depuis la session utilisateur (si stockée)
        # return session.get('locale', app.config['BABEL_DEFAULT_LOCALE'])
        # 3. Essayer d'obtenir la langue depuis l'en-tête Accept-Language du navigateur
        return request.accept_languages.best_match(app.config['LANGUAGES'].keys())
        # 4. Utiliser la langue par défaut
        # return app.config['BABEL_DEFAULT_LOCALE']

    # Met la locale choisie et l'année actuelle à disposition des templates via 'g'
    @app.before_request
    def before_request():
        g.locale = str(get_locale())
        g.locale_display_name = app.config['LANGUAGES'].get(g.locale, g.locale) # Nom lisible
        g.current_year = datetime.now(timezone.utc).year

    # --- Context Processor pour Notifications Non Lues ---
    @app.context_processor
    def inject_notifications():
        unread_count = 0
        # Import local pour éviter dépendance circulaire au démarrage
        from .models import Notification
        if current_user.is_authenticated and not current_user.is_admin:
            # Compte seulement si l'utilisateur est connecté et n'est pas admin
            try:
                unread_count = db.session.scalar(
                    db.select(db.func.count(Notification.id))
                    .where(Notification.user_id == current_user.id, Notification.is_read == False)
                ) or 0
            except Exception as e:
                # En cas d'erreur BDD pendant le démarrage ou avant la première requête,
                # évite de planter toute l'application.
                print(f"Erreur lors du comptage des notifications: {e}")
                unread_count = 0 # Retourne 0 par sécurité
        return dict(unread_notification_count=unread_count)
    # --- Fin Context Processor ---

    # --- Enregistrement des Blueprints ---
    # Blueprint pour les routes d'authentification (login, register, logout)
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Blueprint pour les routes principales (accueil, dashboard, tâches user)
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    # Blueprint pour les routes d'administration
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # --- Log de démarrage (optionnel) ---
    # Utilise app.logger pour une meilleure intégration
    if not app.debug and not app.testing:
        # Configurez ici des logs plus avancés pour la production si nécessaire
        # (ex: envoi par email, fichier rotatif, etc.)
        pass
    app.logger.info('Work and Win startup') # Message simple pour les logs Render

    return app

# Importe les modèles à la fin pour éviter les imports circulaires
# Flask-SQLAlchemy et Flask-Migrate peuvent maintenant trouver les modèles
from app import models