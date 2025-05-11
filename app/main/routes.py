# app/main/routes.py (VERSION COMPLÈTE v27 - Passage Modèle Comment Renommé)

from flask import render_template, redirect, url_for, flash, request, abort, current_app, send_from_directory
from flask_login import login_required, current_user
from flask_babel import _
from app import db
from app.models import (Task, UserTaskCompletion, User, Notification,
                        ExternalTaskCompletion, ReferralCommission, Withdrawal, Post, Comment)
from app.main import bp
from app.forms import EditProfileForm, ChangePasswordForm, CommentForm
from datetime import datetime, timezone, timedelta, date
from sqlalchemy.orm import joinedload
from sqlalchemy import select, func, and_
from decimal import Decimal, InvalidOperation
import json
import os
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from app.mailer import send_verification_email

def allowed_file(filename):
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS_GENERIC', {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'})
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

@bp.route('/')
@bp.route('/index')
def index():
    warning_message = _("Nous appliquons une politique de tolérance zéro envers la triche, l'utilisation de VPN/proxys, ou la création de comptes multiples. Toute violation entraînera un bannissement permanent et la perte des gains.")
    latest_posts = []
    try:
        latest_posts = db.session.scalars(
            select(Post)
            .where(Post.is_published == True)
            .order_by(Post.timestamp.desc())
            .limit(3)
        ).all()
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la récupération des articles pour l'accueil: {e}")
    return render_template('index.html', title=_('Accueil'), warning_message=warning_message, latest_posts=latest_posts)

@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin: return redirect(url_for('admin.index'))
    warning_message = _("Nous appliquons une politique de tolérance zéro envers la triche, l'utilisation de VPN/proxys, ou la création de comptes multiples. Toute violation entraînera un bannissement permanent et la perte des gains.")
    return render_template('dashboard.html', title=_('Tableau de Bord'), warning_message=warning_message)

@bp.route('/tasks/available')
@login_required
def available_tasks():
    user_completions = db.session.scalars(
        db.select(UserTaskCompletion)
        .where(UserTaskCompletion.user_id == current_user.id)
    ).all()
    completions_dict = {}
    for comp in user_completions:
        if comp.task_id not in completions_dict:
            completions_dict[comp.task_id] = []
        completions_dict[comp.task_id].append(comp.completion_timestamp)
    all_active_tasks = db.session.scalars(db.select(Task).where(Task.is_active == True)).all()
    user_country = current_user.country
    user_device = current_user.device
    tasks_for_user = []
    today_utc = date.today()
    for task in all_active_tasks:
        target_countries = task.get_target_countries_list()
        country_match = 'ALL' in target_countries or user_country in target_countries
        target_devices = task.get_target_devices_list()
        device_match = 'ALL' in target_devices or user_device in target_devices
        if country_match and device_match:
            task_id = task.id
            is_completed_ever = task_id in completions_dict
            if task.is_daily:
                completed_today = False
                if is_completed_ever:
                    for timestamp in completions_dict[task_id]:
                        if timestamp.astimezone(timezone.utc).date() == today_utc:
                            completed_today = True; break
                if not completed_today: tasks_for_user.append(task)
            else:
                if not is_completed_ever: tasks_for_user.append(task)
    return render_template('available_tasks.html', title=_('Tâches Disponibles'), tasks=tasks_for_user)

@bp.route('/task/complete/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    task = db.session.get(Task, task_id) or abort(404); user = current_user
    user_country = user.country; user_device = user.device; target_countries = task.get_target_countries_list(); target_devices = task.get_target_devices_list(); country_match = 'ALL' in target_countries or user_country in target_countries; device_match = 'ALL' in target_devices or user_device in target_devices
    if not (country_match and device_match and task.is_active): flash(_('Vous ne pouvez pas accomplir cette tâche ou elle n\'est plus active.'), 'danger'); return redirect(url_for('main.available_tasks'))
    if task.is_daily:
        today_utc = date.today()
        todays_completion = db.session.scalar(select(UserTaskCompletion.id).where(UserTaskCompletion.user_id == user.id, UserTaskCompletion.task_id == task.id, func.date(UserTaskCompletion.completion_timestamp) == today_utc))
        if todays_completion: flash(_('Vous avez déjà accompli cette tâche quotidienne aujourd\'hui.'), 'warning'); return redirect(url_for('main.available_tasks'))
    else:
        existing_completion = db.session.scalar(select(UserTaskCompletion.id).where(UserTaskCompletion.user_id == user.id, UserTaskCompletion.task_id == task.id))
        if existing_completion: flash(_('Vous avez déjà marqué cette tâche comme accomplie.'), 'warning'); return redirect(url_for('main.available_tasks'))
    try:
        completion = UserTaskCompletion(user_id=user.id, task_id=task.id); db.session.add(completion)
        reward = Decimal(str(task.reward_amount or 0.0)); current_balance = Decimal(str(user.balance or 0.0))
        user.balance = float(current_balance + reward); user.completed_task_count = (user.completed_task_count or 0) + 1
        if user.referred_by_id and user.completed_task_count >= 20:
            referrer = db.session.get(User, user.referred_by_id)
            if referrer:
                commission_amount = reward * Decimal('0.03');
                if commission_amount > 0:
                    new_commission = ReferralCommission(referrer_id=referrer.id, referred_user_id=user.id, originating_completion=completion, commission_amount=float(commission_amount), status='Pending');
                    db.session.add(new_commission)
        db.session.commit(); flash(_('Félicitations ! Tâche "%(title)s" marquée comme accomplie. Récompense de %(amount)s $ ajoutée à votre solde.', title=task.title, amount=reward), 'success')
    except Exception as e: db.session.rollback(); flash(_('Une erreur est survenue : %(error)s', error=str(e)), 'danger')
    return redirect(url_for('main.available_tasks'))

@bp.route('/tasks/completed')
@login_required
def completed_tasks():
    page = request.args.get('page', 1, type=int); query = db.select(UserTaskCompletion).where(UserTaskCompletion.user_id == current_user.id).options(joinedload(UserTaskCompletion.task)).order_by(UserTaskCompletion.completion_timestamp.desc()); pagination = db.paginate(query, page=page, per_page=current_app.config['COMPLETIONS_PER_PAGE'], error_out=False); completions = pagination.items
    return render_template('completed_tasks.html', title=_('Mes Tâches Accomplies'), completions=completions, pagination=pagination)

@bp.route('/withdraw')
@login_required
def withdraw():
    min_amount = current_app.config.get('MINIMUM_WITHDRAWAL_AMOUNT', 15.0)
    last_withdrawal = current_user.last_withdrawal_date
    is_eligible_time = False; next_eligible_date = None; days_limit = 30
    now_utc = datetime.now(timezone.utc)
    if last_withdrawal is None: is_eligible_time = True
    else:
        if last_withdrawal.tzinfo is None: last_withdrawal = last_withdrawal.replace(tzinfo=timezone.utc)
        time_since_last = now_utc - last_withdrawal
        if time_since_last >= timedelta(days=days_limit): is_eligible_time = True
        else: next_eligible_date = last_withdrawal + timedelta(days=days_limit)
    can_request_now = is_eligible_time and current_user.balance >= min_amount
    withdrawal_history = db.session.scalars(db.select(Withdrawal).where(Withdrawal.user_id == current_user.id, Withdrawal.status == 'Completed').order_by(Withdrawal.processed_timestamp.desc())).all()
    return render_template('withdraw.html', title=_('Mon Solde et Retrait'), minimum_amount=min_amount, is_eligible_time=is_eligible_time, can_request_now=can_request_now, next_eligible_date=next_eligible_date, withdrawal_history=withdrawal_history)

@bp.route('/notifications')
@login_required
def notifications():
    page = request.args.get('page', 1, type=int)
    query = db.select(Notification).where(Notification.user_id == current_user.id).order_by(Notification.timestamp.desc())
    pagination = db.paginate(query, page=page, per_page=current_app.config['COMPLETIONS_PER_PAGE'], error_out=False)
    user_notifications = pagination.items
    notifications_to_render = []; ids_to_mark_read = []
    for notification in user_notifications:
        payload_dict = {};
        if notification.payload_json:
            try: payload_dict = json.loads(notification.payload_json)
            except json.JSONDecodeError: print(f"Erreur décodage JSON pour notif ID {notification.id}: {notification.payload_json}")
        notification.payload_dict = payload_dict; notifications_to_render.append(notification)
        if not notification.is_read: ids_to_mark_read.append(notification.id)
    if ids_to_mark_read:
        try:
            stmt = db.update(Notification).where(Notification.id.in_(ids_to_mark_read)).values(is_read=True)
            db.session.execute(stmt); db.session.commit()
        except Exception as e: db.session.rollback(); print(f"Erreur marquage notifs lues: {e}"); flash(_("Erreur mise à jour statut notifications."),'danger')
    return render_template('notifications.html', title=_('Mes Notifications'), notifications=notifications_to_render, pagination=pagination)

@bp.route('/task/external/<int:task_id>')
def view_external_task(task_id):
    task = db.session.get(Task, task_id); ref_code = request.args.get('ref')
    if task is None or not task.is_active: flash(_('Cette tâche n\'est pas disponible ou n\'existe pas.'), 'warning'); return redirect(url_for('main.index'))
    return render_template('external_task_view.html', task=task, ref_code=ref_code)

@bp.route('/task/external/submit', methods=['POST'])
def submit_external_proof():
    task_id = request.form.get('task_id'); ref_code = request.form.get('ref_code'); proof_text = request.form.get('proof'); submitter_email = request.form.get('submitter_email'); screenshot_file = request.files.get('screenshot_proof'); filename = None
    task = db.session.get(Task, int(task_id)) if task_id else None; referrer = db.session.scalar(db.select(User).where(User.referral_code == ref_code)) if ref_code else None
    if not task or not referrer: flash(_('Erreur : Tâche ou Parrain invalide.'), 'danger'); return redirect(url_for('main.index'))
    if screenshot_file and screenshot_file.filename != '':
        if allowed_file(screenshot_file.filename):
            unique_prefix = str(int(datetime.now(timezone.utc).timestamp())) + '_'; filename = secure_filename(unique_prefix + screenshot_file.filename)
            upload_dir = current_app.config['UPLOAD_FOLDER']; os.makedirs(upload_dir, exist_ok=True)
            proof_folder = os.path.join(upload_dir, 'proofs'); os.makedirs(proof_folder, exist_ok=True)
            try: screenshot_file.save(os.path.join(proof_folder, filename))
            except Exception as e: flash(_('Erreur lors de la sauvegarde de l\'image: %(err)s', err=e), 'danger'); return redirect(url_for('main.view_external_task', task_id=task_id, ref=ref_code))
        else: flash(_('Type de fichier non autorisé. Permis: %(ext)s', ext=', '.join(current_app.config.get('ALLOWED_EXTENSIONS_GENERIC', {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}))), 'danger'); return redirect(url_for('main.view_external_task', task_id=task_id, ref=ref_code))
    try:
        new_submission = ExternalTaskCompletion(task_id=task.id, referrer_user_id=referrer.id, submitted_proof=(proof_text.strip() if proof_text else None), screenshot_filename=filename, submitter_identifier=submitter_email.strip() if submitter_email else None, status='Pending')
        db.session.add(new_submission); db.session.commit(); flash(_('Votre accomplissement a été soumis avec succès et est en attente de vérification.'), 'success'); return redirect(url_for('main.index'))
    except Exception as e:
        db.session.rollback();
        if filename and os.path.exists(os.path.join(current_app.config['UPLOAD_FOLDER'], 'proofs', filename)):
            try: os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], 'proofs', filename))
            except OSError: pass
        flash(_('Erreur lors de la soumission : %(error)s', error=str(e)), 'danger'); return redirect(url_for('main.view_external_task', task_id=task_id, ref=ref_code))

@bp.route('/uploads/proofs/<path:filename>')
@login_required
def view_proof_upload(filename):
    upload_dir = current_app.config['UPLOAD_FOLDER']
    proof_folder = os.path.join(upload_dir, 'proofs')
    return send_from_directory(proof_folder, filename)

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    edit_form = EditProfileForm(current_user.email); password_form = ChangePasswordForm()
    if edit_form.submit_profile.data and edit_form.validate_on_submit():
        phone_number_full = edit_form.phone_code.data + edit_form.phone_local_number.data
        current_user.full_name = edit_form.full_name.data; current_user.email = edit_form.email.data; current_user.phone_number = phone_number_full; current_user.telegram_username = edit_form.telegram_username.data or None; current_user.country = edit_form.country.data; current_user.device = edit_form.device.data
        try: db.session.commit(); flash(_('Votre profil a été mis à jour.'), 'success'); return redirect(url_for('main.profile'))
        except Exception as e: db.session.rollback(); flash(_('Erreur lors de la mise à jour du profil: %(error)s', error=str(e)), 'danger')
    if password_form.submit_password.data and password_form.validate_on_submit():
        current_user.set_password(password_form.new_password.data)
        try: db.session.commit(); flash(_('Votre mot de passe a été changé avec succès.'), 'success'); return redirect(url_for('main.profile'))
        except Exception as e: db.session.rollback(); flash(_('Erreur lors du changement de mot de passe: %(error)s', error=str(e)), 'danger')
    if request.method == 'GET':
        edit_form.full_name.data = current_user.full_name; edit_form.email.data = current_user.email; edit_form.telegram_username.data = current_user.telegram_username; edit_form.country.data = current_user.country; edit_form.device.data = current_user.device
        current_phone = current_user.phone_number or ''
        found_code = ''; local_num = current_phone
        from app.forms import country_codes
        possible_codes = sorted([c[0] for c in country_codes if c[0]], key=len, reverse=True)
        for code in possible_codes:
            if current_phone.startswith(code): found_code = code; local_num = current_phone[len(code):]; break
        edit_form.phone_code.data = found_code; edit_form.phone_local_number.data = local_num
    return render_template('edit_profile.html', title=_('Modifier Mon Profil'), edit_form=edit_form, password_form=password_form)

@bp.route('/forgot-password-info')
def forgot_password_info():
    return render_template('auth/forgot_password.html', title=_('Mot de Passe Oublié'))

# --- Routes pour le Blog (CÔTÉ UTILISATEUR) ---
@bp.route('/blog')
def blog_index():
    page = request.args.get('page', 1, type=int)
    posts_query = select(Post).where(Post.is_published == True).order_by(Post.timestamp.desc())
    pagination = db.paginate(posts_query, page=page, per_page=current_app.config.get('POSTS_PER_PAGE', 9), error_out=False)
    posts = pagination.items
    return render_template('blog_index.html', title=_('Blog Work and Win'), posts=posts, pagination=pagination)

@bp.route('/blog/post/<slug>', methods=['GET', 'POST'])
def view_post(slug):
    post = db.session.scalar(select(Post).where(Post.slug == slug, Post.is_published == True))
    if post is None:
        abort(404)

    form = None
    if post.allow_comments and current_user.is_authenticated:
        form = CommentForm()
        if form.validate_on_submit():
            if not current_user.is_verified:
                flash(_('Veuillez vérifier votre adresse email avant de commenter.'), 'warning')
                return redirect(url_for('main.view_post', slug=post.slug))
            parent_id_val = form.parent_id.data
            parent_comment = None
            if parent_id_val:
                try: parent_id_int = int(parent_id_val)
                except ValueError: flash(_("ID de commentaire parent invalide."), 'danger'); return redirect(url_for('main.view_post', slug=post.slug))
                parent_comment = db.session.get(Comment, parent_id_int)
                if not parent_comment or parent_comment.post_id != post.id:
                    flash(_('Commentaire parent invalide.'), 'danger')
                    return redirect(url_for('main.view_post', slug=post.slug))
            comment = Comment(
                body=form.body.data, post_id=post.id, user_id=current_user.id,
                parent_id=parent_comment.id if parent_comment else None
            )
            try:
                db.session.add(comment); db.session.commit()
                flash(_('Votre commentaire a été ajouté.'), 'success')
                return redirect(url_for('main.view_post', slug=post.slug) + '#comment-' + str(comment.id))
            except Exception as e:
                db.session.rollback(); flash(_('Erreur lors de l\'ajout du commentaire.'), 'danger')
                current_app.logger.error(f"Erreur ajout commentaire: {e}")
    
    comments_query = select(Comment).where(
        Comment.post_id == post.id,
        Comment.is_approved == True,
        Comment.parent_id == None
    ).order_by(Comment.timestamp.asc())
    comments = db.session.scalars(comments_query).all()

    return render_template('view_post.html', title=post.title, post=post, comments=comments, form=form, CommentModel=Comment) # CommentModel est passé ici
# --- FIN ROUTES BLOG ---

