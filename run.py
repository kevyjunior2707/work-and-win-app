from app import create_app, db # Importe la factory et l'objet BDD depuis app/__init__.py
from app.models import User, Task # Importe les modèles BDD (même si app/models.py est encore vide)
from flask_migrate import Migrate # Importe l'outil de migration BDD

# Crée l'instance de l'application en appelant la factory
# create_app() utilise la classe Config par défaut
app = create_app()

# Initialise Flask-Migrate en le liant à notre app et notre BDD
# Cela active les commandes comme `flask db migrate`
migrate = Migrate(app, db)

# Ceci est une fonction utilitaire pour la commande `flask shell`
# Elle permet d'avoir accès directement aux variables 'app', 'db', 'User', 'Task'
# sans avoir à les importer manuellement dans le shell. Très pratique pour tester.
@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Task': Task}

# Ce bloc ne s'exécute que si on lance le script directement (ex: python run.py)
if __name__ == '__main__':
    # Affiche un message dans la console (Exemple de texte pro)
    print("Lancement du serveur de développement WorkAndWin...")
    # Démarre le serveur web de développement Flask.
    # Il utilisera automatiquement FLASK_DEBUG=1 (depuis .env) pour le mode débogage.
    # ATTENTION: Ce serveur n'est PAS adapté pour la production sur Hostinger.
    # En production, on utilisera un serveur WSGI comme Gunicorn ou uWSGI.
    app.run()