# app/admin/__init__.py
from flask import Blueprint

# Crée un blueprint nommé 'admin'
# 'admin' sera utilisé dans url_for (ex: 'admin.create_task')
# __name__ aide Flask
# template_folder='templates' indique de chercher les templates dans un sous-dossier admin/templates/
bp = Blueprint('admin', __name__, template_folder='templates')

# Importe les routes spécifiques à l'admin (le fichier qu'on va créer ensuite)
# Cet import est à la fin pour éviter les imports circulaires
from app.admin import routes