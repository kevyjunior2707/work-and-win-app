# run.py (VERSION COMPLÈTE FINALE - v3)

# Imports essentiels
from app import create_app, db # Importe la factory et l'objet BDD depuis app/__init__.py
from app.models import User, Task # Importe les modèles BDD
import click # Import click pour la commande CLI
from flask_migrate import Migrate # Importe l'outil de migration BDD

# Crée l'instance de l'application Flask en utilisant la factory
app = create_app()

# Initialise Flask-Migrate en le liant à notre app et notre BDD
# Cela active les commandes comme `flask db migrate`
migrate = Migrate(app, db)

# --- Commande CLI pour définir un super admin ---
# Cette fonction sera exécutable via "flask set-super-admin <email>"
@app.cli.command("set-super-admin")
@click.argument("email")
def set_super_admin(email):
    """Définit un utilisateur existant comme Super Admin."""
    # Utilise le contexte de l'application pour accéder à la BDD
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.email == email))
        if user:
            user.is_admin = True
            user.is_super_admin = True
            db.session.commit()
            print(f"Utilisateur {email} défini comme Super Admin.")
        else:
            print(f"ERREUR : Utilisateur {email} non trouvé.")
# --- Fin Commande CLI ---


# --- Fonction utilitaire pour la commande `flask shell` ---
# Permet d'avoir accès directement aux variables 'app', 'db', 'User', 'Task'
# sans avoir à les importer manuellement dans le shell.
@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Task': Task}

# --- Point d'entrée (si exécuté directement, non utilisé par Gunicorn) ---
if __name__ == '__main__':
    # Démarre le serveur de développement Flask (pour tests locaux si besoin)
    # Ne pas utiliser en production.
    app.run()

