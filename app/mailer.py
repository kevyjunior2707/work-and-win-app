# app/email.py
from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from app import mail
from flask_babel import _
import requests


# -------------------------
# ENVOI BREVO
# -------------------------
def send_email_brevo(subject, recipients, html_body, text_body=None):
    api_key = current_app.config.get("BREVO_API_KEY")

    url = "https://api.brevo.com/v3/smtp/email"

    payload = {
        "sender": {
            "name": "Work and Win",
            "email": current_app.config['MAIL_USERNAME']
        },
        "to": [{"email": recipients[0]}],
        "subject": subject,
        "htmlContent": html_body
    }

    if text_body:
        payload["textContent"] = text_body

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }

    requests.post(url, json=payload, headers=headers)


# -------------------------
# EMAIL ASYNC
# -------------------------
def send_async_email(app, msg):
    with app.app_context():
        try:
            if current_app.config.get("BREVO_API_KEY"):
                send_email_brevo(
                    msg.subject,
                    msg.recipients,
                    msg.html,
                    msg.body
                )
            else:
                mail.send(msg)

        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email en arrière-plan: {e}")
            current_app.logger.error(f"Erreur envoi email BG: {e}")


# -------------------------
# SEND EMAIL
# -------------------------
def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body

    app = current_app._get_current_object()

    Thread(target=send_async_email, args=(app, msg)).start()


# -------------------------
# VERIFICATION EMAIL
# -------------------------
def send_verification_email(user):
    token = user.get_verification_token()

    send_email(
        _('Vérifiez votre adresse email - Work and Win'),
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[user.email],
        text_body=render_template('email/verify_email.txt', user=user, token=token),
        html_body=render_template('email/verify_email.html', user=user, token=token)
    )
