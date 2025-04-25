# app/email.py

from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from app import mail # Importe l'instance mail depuis __init__.py
from flask_babel import _ # Pour traduire le sujet de l'email

# Fonction pour envoyer un email en arrière-plan
def send_async_email(app, msg):
    with app.app_context(): # Nécessaire car l'email est envoyé dans un thread séparé
        try:
            mail.send(msg)
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email en arrière-plan: {e}")
            # Ici, vous pourriez ajouter un log plus robuste
            # ou un mécanisme pour réessayer plus tard

# Fonction principale pour préparer et lancer l'envoi
def send_email(subject, sender, recipients, text_body, html_body):
    # Crée l'objet Message
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    # Crée une copie de l'application actuelle pour le thread
    app = current_app._get_current_object()
    # Lance l'envoi dans un thread séparé
    Thread(target=send_async_email, args=(app, msg)).start()

# Fonction spécifique pour l'email de vérification
def send_verification_email(user):
    # Génère le token unique et limité dans le temps pour cet utilisateur
    token = user.get_verification_token()
    # Prépare l'email
    send_email(
        _('Vérifiez votre adresse email - Work and Win'), # Sujet
        sender=current_app.config['MAIL_DEFAULT_SENDER'], # Expéditeur (configuré dans config.py)
        recipients=[user.email], # Destinataire
        # Corps de l'email en texte brut (pour clients mail simples)
        text_body=render_template('email/verify_email.txt', user=user, token=token),
        # Corps de l'email en HTML (pour la plupart des clients mail)
        html_body=render_template('email/verify_email.html', user=user, token=token)
    )