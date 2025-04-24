# app/decorators.py (VERSION COMPLÈTE AVEC LES DEUX DÉCORATEURS - Indentation Vérifiée)

from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user
from flask_babel import _

# --- Décorateur pour Admin Normal (ou Super Admin) ---
# Vérifie si l'utilisateur est connecté ET a le flag 'is_admin'
def admin_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash(_('Accès non autorisé. Cette zone est réservée aux administrateurs.'), 'danger')
            # Redirige vers l'accueil principal si pas admin
            return redirect(url_for('main.index'))
        # Laisse passer si admin (normal ou super)
        return func(*args, **kwargs)
    return decorated_function

# --- Décorateur pour Super Admin Uniquement ---
# Vérifie si l'utilisateur est connecté ET a le flag 'is_admin' ET le flag 'is_super_admin'
def super_admin_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        # Utilise getattr pour vérifier 'is_super_admin' de manière sûre,
        # au cas où un vieil objet user n'aurait pas l'attribut
        is_super = getattr(current_user, 'is_super_admin', False)

        if (not current_user.is_authenticated or
                not current_user.is_admin or
                not is_super):
            flash(_('Accès non autorisé. Cette action requiert les privilèges Super Administrateur.'), 'danger')
            # Redirige vers le panel admin standard si pas super admin
            return redirect(url_for('admin.index'))
        # Laisse passer seulement si super admin
        return func(*args, **kwargs)
    return decorated_function