# app/auth/routes.py (VERSION COMPLÈTE v13 - Ajout import func)
from flask import render_template, redirect, url_for, flash, request, current_app
from urllib.parse import urlparse
from app import db
from app.auth import bp
from app.forms import RegistrationForm, LoginForm
from app.models import User
from flask_login import login_user, logout_user, current_user, login_required
from flask_babel import _
from datetime import datetime, timezone
from sqlalchemy import select, func # <<< func ajouté ici >>>
from app.mailer import send_verification_email

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    ref_code = request.args.get('ref'); referrer = None
    if ref_code: referrer = db.session.scalar(select(User).where(User.referral_code == ref_code))
    form = RegistrationForm()
    if form.validate_on_submit():
        phone_number_full = form.phone_code.data + form.phone_local_number.data
        user = User(
            full_name=form.full_name.data,
            email=form.email.data.lower(),
            phone_number=phone_number_full,
            telegram_username=form.telegram_username.data or None,
            country=form.country.data,
            device=form.device.data,
            referred_by_id=(referrer.id if referrer else None),
            is_verified=False
        )
        user.set_password(form.password.data)
        try:
            db.session.add(user)
            db.session.commit()
            try:
                send_verification_email(user)
                flash(_('Inscription réussie ! Un email de vérification a été envoyé. Cliquez sur le lien pour activer votre compte.'), 'info')
            except Exception as e:
                current_app.logger.error(f"Erreur envoi email vérification pour {user.email}: {e}")
                flash(_('Inscription réussie, mais l\'email de vérification n\'a pas pu être envoyé. Contactez le support.'), 'warning')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erreur lors de l'inscription BDD pour {form.email.data}: {e}")
            flash(_("Erreur lors de l'inscription: %(error)s", error=str(e)), 'danger')
    return render_template('auth/register.html', title=_('Inscription'), form=form)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('admin.index') if current_user.is_admin else url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        # Utilise func.lower() pour comparaison insensible à la casse
        user = db.session.scalar(
            db.select(User).where(func.lower(User.email) == form.email.data.lower())
        )
        if user and user.is_banned: flash(_('Votre compte a été banni. Contactez le support.'), 'danger'); return redirect(url_for('auth.login'))
        if user is None or not user.check_password(form.password.data): flash(_('Email ou mot de passe invalide.'), 'danger'); return redirect(url_for('auth.login'))
        # Optionnel: Bloquer connexion si non vérifié
        # if not user.is_verified:
        #     flash(_('Compte non vérifié. Cliquez sur le lien dans votre email ou demandez un renvoi depuis le tableau de bord.'), 'warning')
        #     return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data); next_page = request.args.get('next'); is_safe_next = next_page and urlparse(next_page).netloc == ''
        if not is_safe_next: next_page = url_for('admin.index') if user.is_admin else url_for('main.dashboard')
        if hasattr(user, 'last_seen'): user.last_seen = datetime.now(timezone.utc); db.session.commit()
        flash(_('Connexion réussie !'), 'success'); return redirect(next_page)
    return render_template('auth/login.html', title=_('Connexion'), form=form)

@bp.route('/logout')
def logout():
    logout_user(); flash(_('Vous avez été déconnecté.'), 'info')
    return redirect(url_for('main.index'))

# Route pour infos mot de passe oublié
@bp.route('/forgot-password')
def forgot_password():
    return render_template('auth/forgot_password.html', title=_('Mot de Passe Oublié'))

# --- Route pour traiter le clic sur le lien de vérification ---
@bp.route('/verify/<token>')
def verify_email(token):
    user = User.verify_verification_token(token)
    if not user:
        flash(_('Le lien de vérification est invalide ou a expiré.'), 'danger')
        return redirect(url_for('main.index'))
    if user.is_verified:
         flash(_('Votre compte est déjà vérifié. Vous pouvez vous connecter.'), 'info')
         return redirect(url_for('auth.login'))
    user.is_verified = True
    try:
        db.session.commit()
        flash(_('Votre compte a été vérifié avec succès ! Vous pouvez maintenant vous connecter.'), 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur lors de la vérification BDD pour user {user.id}: {e}")
        flash(_('Une erreur est survenue lors de la vérification. Veuillez réessayer ou contacter le support.'), 'danger')
    return redirect(url_for('auth.login'))

# --- Route pour renvoyer l'Email de Vérification ---
@bp.route('/resend-verification', methods=['POST'])
@login_required
def resend_verification_email():
    if current_user.is_verified:
        flash(_('Votre compte est déjà vérifié.'), 'info')
        return redirect(url_for('main.dashboard'))
    try:
        send_verification_email(current_user)
        flash(_('Un nouvel email de vérification a été envoyé à votre adresse.'), 'success')
    except Exception as e:
        current_app.logger.error(f"Erreur renvoi email vérification pour {current_user.email}: {e}")
        flash(_('Erreur lors de l\'envoi de l\'email. Veuillez réessayer ou contacter le support.'), 'danger')
    return redirect(url_for('main.dashboard'))