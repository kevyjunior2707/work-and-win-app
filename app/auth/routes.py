# app/auth/routes.py (COMPLET avec forgot_password - v7)
from flask import render_template, redirect, url_for, flash, request
from urllib.parse import urlparse
from app import db
from app.auth import bp
from app.forms import RegistrationForm, LoginForm
from app.models import User # User est déjà importé
from flask_login import login_user, logout_user, current_user
from flask_babel import _
from datetime import datetime, timezone
from sqlalchemy import select # Ajout select pour chercher le parrain

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    ref_code = request.args.get('ref'); referrer = None
    if ref_code: referrer = db.session.scalar(select(User).where(User.referral_code == ref_code))
    # Ne met plus de flash si code invalide, ignore juste
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data, email=form.email.data,
            phone_number=form.phone_number.data, country=form.country.data,
            device=form.device.data,
            referred_by_id=(referrer.id if referrer else None)
        )
        user.set_password(form.password.data)
        db.session.add(user); db.session.commit()
        flash(_('Félicitations, inscription réussie ! Connectez-vous.'), 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title=_('Inscription'), form=form)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('admin.index') if current_user.is_admin else url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(User).where(User.email == form.email.data))
        if user and user.is_banned: flash(_('Votre compte a été banni. Contactez le support.'), 'danger'); return redirect(url_for('auth.login'))
        if user is None or not user.check_password(form.password.data): flash(_('Email ou mot de passe invalide.'), 'danger'); return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data); next_page = request.args.get('next'); is_safe_next = next_page and urlparse(next_page).netloc == ''
        if not is_safe_next: next_page = url_for('admin.index') if user.is_admin else url_for('main.dashboard')
        if hasattr(user, 'last_seen'): user.last_seen = datetime.now(timezone.utc); db.session.commit()
        flash(_('Connexion réussie !'), 'success'); return redirect(next_page)
    return render_template('auth/login.html', title=_('Connexion'), form=form)

@bp.route('/logout')
def logout():
    logout_user(); flash(_('Vous avez été déconnecté.'), 'info')
    return redirect(url_for('main.index'))

# <<< NOUVELLE ROUTE ICI >>>
@bp.route('/forgot-password')
def forgot_password():
    # Affiche simplement la page avec les instructions
    return render_template('auth/forgot_password.html', title=_('Mot de Passe Oublié'))
# <<< FIN NOUVELLE ROUTE >>>