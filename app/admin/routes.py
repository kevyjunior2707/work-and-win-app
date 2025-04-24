# app/admin/routes.py (VERSION COMPLÈTE v38 - Avec Historique Retraits Admin)

from flask import render_template, redirect, url_for, flash, request, abort, current_app, send_from_directory
from flask_login import login_required, current_user
from flask_babel import _
from app import db
from app.admin import bp
# Ajout AdminResetPasswordForm et AddAdminForm
from app.forms import TaskForm, countries_choices_multi, devices_choices_multi, countries_choices_single, devices_choices_single, AdminResetPasswordForm, AddAdminForm
# Ajout ReferralCommission et Withdrawal
from app.models import Task, UserTaskCompletion, ExternalTaskCompletion, User, Withdrawal, Notification, ReferralCommission
# Ajout super_admin_required
from app.decorators import admin_required, super_admin_required
from sqlalchemy import select, or_, func
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone, timedelta # Ajout timedelta
from decimal import Decimal, InvalidOperation
import json
import os
from werkzeug.utils import secure_filename
# Import pour générer le token CSRF
from flask_wtf.csrf import generate_csrf

# --- Route pour l'accueil Admin (Avec Graphiques) ---
@bp.route('/')
@login_required
@admin_required
def index():
    # Calculs pour les Graphiques (par mois, 12 derniers mois)
    twelve_months_ago = datetime.now(timezone.utc) - timedelta(days=365)
    date_format_string = 'YYYY-MM' # Format pour PostgreSQL

    # Inscriptions
    registrations_by_month_query = db.select(
            func.to_char(User.registration_date, date_format_string).label('month'),
            func.count(User.id).label('count')
        ).where(User.is_admin == False, User.registration_date >= twelve_months_ago)\
        .group_by(func.to_char(User.registration_date, date_format_string))\
        .order_by(func.to_char(User.registration_date, date_format_string))
    registrations_data = db.session.execute(registrations_by_month_query).all()
    # Accomplissements
    completions_by_month_query = db.select(
            func.to_char(UserTaskCompletion.completion_timestamp, date_format_string).label('month'),
            func.count(UserTaskCompletion.id).label('count')
        ).where(UserTaskCompletion.completion_timestamp >= twelve_months_ago)\
        .group_by(func.to_char(UserTaskCompletion.completion_timestamp, date_format_string))\
        .order_by(func.to_char(UserTaskCompletion.completion_timestamp, date_format_string))
    completions_data = db.session.execute(completions_by_month_query).all()
    # Gains
    earnings_by_month_query = db.select(
            func.to_char(UserTaskCompletion.completion_timestamp, date_format_string).label('month'),
            func.sum(Task.reward_amount).label('total_reward')
        ).join(Task, UserTaskCompletion.task_id == Task.id)\
        .where(UserTaskCompletion.completion_timestamp >= twelve_months_ago)\
        .group_by(func.to_char(UserTaskCompletion.completion_timestamp, date_format_string))\
        .order_by(func.to_char(UserTaskCompletion.completion_timestamp, date_format_string))
    earnings_data = db.session.execute(earnings_by_month_query).all()
    # Préparation données Chart.js
    reg_dict = {row.month: row.count for row in registrations_data}
    comp_dict = {row.month: row.count for row in completions_data}
    earn_dict = {row.month: float(row.total_reward or 0.0) for row in earnings_data}
    chart_labels = []
    current_month = datetime.now(timezone.utc)
    for i in range(12):
        month_label = (current_month - timedelta(days=i*30)).strftime('%Y-%m')
        chart_labels.append(month_label)
    chart_labels.reverse()
    registrations_chart_data = [reg_dict.get(month, 0) for month in chart_labels]
    completions_chart_data = [comp_dict.get(month, 0) for month in chart_labels]
    earnings_chart_data = [earn_dict.get(month, 0) for month in chart_labels]
    chart_data = {
        'labels': chart_labels,
        'registrations': registrations_chart_data,
        'completions': completions_chart_data,
        'earnings': earnings_chart_data
    }
    return render_template('admin_home.html',
                           title=_('Panneau Administrateur'),
                           chart_data=chart_data)

# --- Routes pour la gestion des Tâches ---
@bp.route('/tasks/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_task():
    form = TaskForm()
    if form.validate_on_submit():
        selected_countries = form.target_countries.data; countries_to_save = 'ALL' if 'ALL' in selected_countries or not selected_countries else ','.join(selected_countries)
        selected_devices = form.target_devices.data; devices_to_save = 'ALL' if 'ALL' in selected_devices or not selected_devices else ','.join(selected_devices)
        is_active_task = form.is_active.data
        new_task = Task(
            title=form.title.data, description=form.description.data,
            instructions=form.instructions.data, task_link=form.task_link.data,
            reward_amount=form.reward_amount.data, target_countries=countries_to_save,
            target_devices=devices_to_save, is_active=is_active_task
        )
        try:
            db.session.add(new_task)
            db.session.commit() # Commit la tâche d'abord
            flash(_('La nouvelle tâche "%(title)s" a été créée avec succès !', title=new_task.title), 'success')
            if is_active_task:
                target_country_list = countries_to_save.split(',') if countries_to_save != 'ALL' else []
                target_device_list = devices_to_save.split(',') if devices_to_save != 'ALL' else []
                query = select(User.id).where(User.is_admin == False, User.is_banned == False)
                if countries_to_save != 'ALL' and target_country_list: query = query.where(User.country.in_(target_country_list))
                if devices_to_save != 'ALL' and target_device_list: query = query.where(User.device.in_(target_device_list))
                eligible_user_ids = db.session.scalars(query).all()
                if eligible_user_ids:
                    notifications_to_add = []
                    for user_id in eligible_user_ids:
                        notif = Notification(user_id=user_id, name='new_task_available', payload_json=json.dumps({'task_id': new_task.id, 'task_title': new_task.title}))
                        notifications_to_add.append(notif)
                    if notifications_to_add:
                        db.session.add_all(notifications_to_add)
                        db.session.commit() # Commit les notifications
                        print(f"INFO: Sent 'new_task_available' notification to {len(notifications_to_add)} users for task {new_task.id}")
            return redirect(url_for('admin.list_tasks'))
        except Exception as e:
            db.session.rollback()
            flash(_("Erreur lors de la création de la tâche : %(error)s", error=str(e)), 'danger')
    return render_template('create_task.html', title=_('Créer une Nouvelle Tâche'), form=form, is_edit=False)

@bp.route('/tasks')
@login_required
@admin_required
def list_tasks():
    search_title = request.args.get('title', ''); search_country = request.args.get('country', ''); search_device = request.args.get('device', '')
    query = select(Task);
    if search_title: query = query.where(Task.title.ilike(f'%{search_title}%'))
    if search_country: query = query.where(Task.target_countries.ilike(f'%{search_country}%'))
    if search_device: query = query.where(Task.target_devices.ilike(f'%{search_device}%'))
    query = query.order_by(Task.creation_date.desc()); tasks = db.session.scalars(query).all()
    return render_template('task_list.html', title=_('Gestion des Tâches'), tasks=tasks, countries_list=countries_choices_multi, devices_list=devices_choices_multi, search_title=search_title, search_country=search_country, search_device=search_device)

@bp.route('/task/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_task(task_id):
    task = db.session.get(Task, task_id) or abort(404); form = TaskForm(obj=task if request.method == 'GET' else None)
    if request.method == 'GET':
        form.target_countries.data = task.target_countries.split(',') if task.target_countries and task.target_countries != 'ALL' else (['ALL'] if task.target_countries == 'ALL' else [])
        form.target_devices.data = task.target_devices.split(',') if task.target_devices and task.target_devices != 'ALL' else (['ALL'] if task.target_devices == 'ALL' else [])
    if form.validate_on_submit():
        old_status = task.is_active
        selected_countries = form.target_countries.data; countries_to_save = 'ALL' if 'ALL' in selected_countries or not selected_countries else ','.join(selected_countries)
        selected_devices = form.target_devices.data; devices_to_save = 'ALL' if 'ALL' in selected_devices or not selected_devices else ','.join(selected_devices)
        task.title=form.title.data; task.description=form.description.data; task.instructions=form.instructions.data; task.task_link=form.task_link.data; task.reward_amount=form.reward_amount.data; task.target_countries=countries_to_save; task.target_devices=devices_to_save; task.is_active=form.is_active.data
        try:
            db.session.commit()
            flash(_('Tâche "%(title)s" mise à jour avec succès !', title=task.title), 'success')
            if not old_status and task.is_active:
                target_country_list = countries_to_save.split(',') if countries_to_save != 'ALL' else []
                target_device_list = devices_to_save.split(',') if devices_to_save != 'ALL' else []
                query = select(User.id).where(User.is_admin == False, User.is_banned == False)
                if countries_to_save != 'ALL' and target_country_list: query = query.where(User.country.in_(target_country_list))
                if devices_to_save != 'ALL' and target_device_list: query = query.where(User.device.in_(target_device_list))
                eligible_user_ids = db.session.scalars(query).all()
                if eligible_user_ids:
                    notifications_to_add = [];
                    for user_id in eligible_user_ids:
                        already_done = db.session.scalar(select(UserTaskCompletion.id).where(UserTaskCompletion.user_id==user_id, UserTaskCompletion.task_id==task.id))
                        if not already_done:
                            notifications_to_add.append(Notification(user_id=user_id, name='new_task_available', payload_json=json.dumps({'task_id': task.id, 'task_title': task.title})))
                    if notifications_to_add:
                        db.session.add_all(notifications_to_add)
                        db.session.commit()
                        print(f"INFO: Sent 'new_task_available' notification to {len(notifications_to_add)} users for task {task.id} upon activation.")
            return redirect(url_for('admin.list_tasks'))
        except Exception as e:
            db.session.rollback()
            flash(_("Erreur lors de la mise à jour de la tâche : %(error)s", error=str(e)), 'danger')
    return render_template('create_task.html', title=_('Modifier la Tâche'), form=form, is_edit=True, task_id=task_id)

@bp.route('/task/<int:task_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_task(task_id):
    task_to_delete = db.session.get(Task, task_id) or abort(404); title_copy = task_to_delete.title
    try: uc_stmt = db.delete(UserTaskCompletion).where(UserTaskCompletion.task_id == task_id); db.session.execute(uc_stmt); ec_stmt = db.delete(ExternalTaskCompletion).where(ExternalTaskCompletion.task_id == task_id); db.session.execute(ec_stmt); db.session.delete(task_to_delete); db.session.commit(); flash(_('Tâche "%(title)s" supprimée avec succès.', title=title_copy), 'success')
    except Exception as e: db.session.rollback(); flash(_('Erreur lors de la suppression : %(error)s', error=str(e)), 'danger')
    return redirect(url_for('admin.list_tasks'))

# --- Route pour voir l'historique des accomplissements ---
@bp.route('/completions')
@login_required
@admin_required
def list_completions():
    page = request.args.get('page', 1, type=int); user_search = request.args.get('user_search', ''); task_search = request.args.get('task_search', '')
    query = db.select(UserTaskCompletion).options(joinedload(UserTaskCompletion.user), joinedload(UserTaskCompletion.task))
    if user_search: query = query.join(UserTaskCompletion.user).where(or_(User.full_name.ilike(f'%{user_search}%'), User.email.ilike(f'%{user_search}%')))
    if task_search: query = query.join(UserTaskCompletion.task).where(Task.title.ilike(f'%{task_search}%'))
    query = query.order_by(UserTaskCompletion.completion_timestamp.desc()); pagination = db.paginate(query, page=page, per_page=current_app.config['COMPLETIONS_PER_PAGE'], error_out=False); completions = pagination.items
    return render_template('completion_list.html', title=_('Historique des Accomplissements'), completions=completions, pagination=pagination, user_search=user_search, task_search=task_search)

# --- Route pour afficher les utilisateurs/soldes et enregistrer les retraits (MODIFIÉE) ---
@bp.route('/withdrawals')
@login_required
@admin_required
def list_withdrawals():
    page_users = request.args.get('page_users', 1, type=int)
    page_history = request.args.get('page_history', 1, type=int)
    search_name = request.args.get('name', '')
    search_email = request.args.get('email', '')

    # Requête pour la liste des utilisateurs (paginée)
    users_query = db.select(User).where(User.is_admin == False)
    if search_name: users_query = users_query.where(User.full_name.ilike(f'%{search_name}%'))
    if search_email: users_query = users_query.where(User.email.ilike(f'%{search_email}%'))
    users_query = users_query.order_by(User.full_name)
    users_pagination = db.paginate(users_query, page=page_users, per_page=current_app.config.get('USERS_PER_PAGE', 15), error_out=False)
    users = users_pagination.items

    # <<< AJOUT : Requête pour l'historique global des retraits (paginée) >>>
    history_query = db.select(Withdrawal)\
        .options(joinedload(Withdrawal.requester), joinedload(Withdrawal.processed_by_admin))\
        .where(Withdrawal.status == 'Completed')\
        .order_by(Withdrawal.processed_timestamp.desc())
    history_pagination = db.paginate(history_query, page=page_history, per_page=current_app.config.get('HISTORY_PER_PAGE', 20), error_out=False)
    withdrawal_history = history_pagination.items
    # <<< FIN AJOUT >>>

    return render_template('withdrawal_list.html',
                           title=_('Gestion Retraits / Soldes Utilisateurs'),
                           users=users,
                           users_pagination=users_pagination, # Passe l'objet pagination des users
                           withdrawal_history=withdrawal_history,
                           history_pagination=history_pagination, # Passe l'objet pagination de l'historique
                           search_name=search_name,
                           search_email=search_email)

# --- Route pour ENREGISTRER un retrait manuel ---
@bp.route('/withdrawal/record/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def record_withdrawal(user_id):
    user = db.session.get(User, user_id) or abort(404); amount_str = request.form.get('amount')
    try:
        amount_withdrawn = Decimal(amount_str);
        if amount_withdrawn <= 0: raise ValueError(_("Le montant doit être positif."))
        user_balance_decimal = Decimal(str(user.balance or 0.0))
        if amount_withdrawn > user_balance_decimal: raise ValueError(_("Le montant retiré dépasse le solde."))
        user.balance = float(user_balance_decimal - amount_withdrawn); user.last_withdrawal_date = datetime.now(timezone.utc)
        withdrawal_log = Withdrawal(user_id=user.id, amount=float(amount_withdrawn), status='Completed', processed_by_admin_id=current_user.id, processed_timestamp=datetime.now(timezone.utc))
        db.session.add(withdrawal_log); db.session.commit()
        flash(_('Paiement de %(amount)s $ enregistré pour %(user)s.', amount=amount_withdrawn, user=user.full_name), 'success')
    except (InvalidOperation, ValueError, TypeError, Exception) as e: db.session.rollback(); flash(_('Erreur lors de l\'enregistrement du retrait : %(error)s', error=str(e)), 'danger')
    # Redirige vers la page d'où venait la requête (ou la page 1 par défaut)
    page_users = request.args.get('page_users', 1, type=int)
    return redirect(url_for('admin.list_withdrawals', page_users=page_users))

# --- Routes Gestion Utilisateurs ---
@bp.route('/users')
@login_required
@admin_required
def list_users():
    page = request.args.get('page', 1, type=int); search_name = request.args.get('name', ''); search_email = request.args.get('email', ''); search_country = request.args.get('country', ''); search_device = request.args.get('device', '')
    query = select(User).where(User.is_admin == False);
    if search_name: query = query.where(User.full_name.ilike(f'%{search_name}%'))
    if search_email: query = query.where(User.email.ilike(f'%{search_email}%'))
    if search_country: query = query.where(User.country == search_country)
    if search_device: query = query.where(User.device == search_device)
    query = query.order_by(User.registration_date.desc()); pagination = db.paginate(query, page=page, per_page=current_app.config['COMPLETIONS_PER_PAGE'], error_out=False); users = pagination.items
    csrf_token_value = generate_csrf() # Génère le token pour la modale
    return render_template('user_list.html',
                           title=_('Gestion des Utilisateurs'),
                           users=users,
                           pagination=pagination,
                           search_name=search_name,
                           search_email=search_email,
                           search_country=search_country,
                           search_device=search_device,
                           countries_list=countries_choices_single,
                           devices_list=devices_choices_single,
                           csrf_token=csrf_token_value) # Passe le token

@bp.route('/user/<int:user_id>/ban', methods=['POST'])
@login_required
@admin_required
def ban_user(user_id):
    user_to_ban = db.session.get(User, user_id) or abort(404);
    if user_to_ban.is_admin or user_to_ban.id == current_user.id: flash(_('Action non autorisée.'), 'danger'); return redirect(url_for('admin.list_users'))
    if user_to_ban.is_banned: flash(_('Cet utilisateur est déjà banni.'), 'warning'); return redirect(url_for('admin.list_users'))
    user_to_ban.is_banned = True; db.session.commit(); flash(_('L\'utilisateur %(name)s a été banni.', name=user_to_ban.full_name), 'success'); return redirect(url_for('admin.list_users'))

@bp.route('/user/<int:user_id>/unban', methods=['POST'])
@login_required
@admin_required
def unban_user(user_id):
    user_to_unban = db.session.get(User, user_id) or abort(404);
    if not user_to_unban.is_banned: flash(_('Cet utilisateur n\'est pas banni.'), 'warning'); return redirect(url_for('admin.list_users'))
    user_to_unban.is_banned = False; db.session.commit(); flash(_('L\'utilisateur %(name)s a été débanni.', name=user_to_unban.full_name), 'success'); return redirect(url_for('admin.list_users'))

@bp.route('/user/<int:user_id>/reduce_balance', methods=['POST'])
@login_required
@admin_required
def reduce_balance(user_id):
    user_to_update = db.session.get(User, user_id) or abort(404);
    if user_to_update.is_admin: flash(_('Vous ne pouvez pas modifier le solde d\'un administrateur.'), 'danger'); return redirect(url_for('admin.list_users'))
    amount_str = request.form.get('reduction_amount'); message = request.form.get('warning_message')
    try:
        amount_to_reduce = Decimal(amount_str);
        if amount_to_reduce <= 0: raise ValueError(_("Le montant de réduction doit être positif."))
        if not message or not message.strip(): raise ValueError(_("Le message d'avertissement ne peut pas être vide."))
        user_balance_decimal = Decimal(str(user_to_update.balance or 0.0)); user_to_update.balance = float(user_balance_decimal - amount_to_reduce)
        notif = Notification(user_id=user_to_update.id, name='admin_warning', payload_json=json.dumps({'message': message.strip()}))
        db.session.add(notif); db.session.commit()
        flash(_('Le solde de %(user)s a été réduit de %(amount)s $ et un avertissement a été enregistré.', user=user_to_update.full_name, amount=amount_to_reduce), 'success')
    except (InvalidOperation, ValueError, TypeError, Exception) as e: db.session.rollback(); flash(_('Erreur : %(error)s', error=str(e)), 'danger')
    return redirect(url_for('admin.list_users'))

@bp.route('/user/<int:user_id>/add_balance', methods=['POST'])
@login_required
@admin_required
def add_balance(user_id):
    user_to_update = db.session.get(User, user_id) or abort(404);
    if user_to_update.is_admin: flash(_('Vous ne pouvez pas modifier le solde d\'un administrateur.'), 'danger'); return redirect(url_for('admin.list_users'))
    amount_str = request.form.get('amount_to_add'); reason = request.form.get('reason_message')
    try:
        amount_to_add = Decimal(amount_str);
        if amount_to_add <= 0: raise ValueError(_("Le montant ajouté doit être positif."))
        if not reason or not reason.strip(): raise ValueError(_("La raison/description ne peut pas être vide."))
        user_balance_decimal = Decimal(str(user_to_update.balance or 0.0)); user_to_update.balance = float(user_balance_decimal + amount_to_add)
        notif = Notification(user_id=user_to_update.id, name='admin_credit', payload_json=json.dumps({'message': reason.strip(), 'amount': str(amount_to_add)}))
        db.session.add(notif); db.session.commit()
        flash(_('Un montant de %(amount)s $ a été ajouté au solde de %(user)s. Raison : %(reason)s', user=user_to_update.full_name, amount=amount_to_add, reason=reason.strip()), 'success')
    except (InvalidOperation, ValueError, TypeError, Exception) as e: db.session.rollback(); flash(_('Erreur : %(error)s', error=str(e)), 'danger')
    return redirect(url_for('admin.list_users'))

# --- Route Messagerie Ciblée ---
@bp.route('/messaging', methods=['GET', 'POST'])
@login_required
@admin_required
def send_message():
    if request.method == 'POST':
        target_country = request.form.get('country'); target_device = request.form.get('device'); subject = request.form.get('subject', ''); body = request.form.get('body')
        if not body or not body.strip(): flash(_('Le corps du message ne peut pas être vide.'), 'danger'); return redirect(url_for('admin.send_message'))
        query = select(User.id).where(User.is_admin == False, User.is_banned == False);
        if target_country: query = query.where(User.country == target_country)
        if target_device: query = query.where(User.device == target_device)
        target_user_ids = db.session.scalars(query).all(); count = 0
        try:
            if target_user_ids:
                notifications_to_add = [];
                for user_id in target_user_ids:
                    notifications_to_add.append(Notification(user_id=user_id, name='admin_message', payload_json=json.dumps({'subject': subject.strip(), 'message': body.strip()})))
                if notifications_to_add:
                    db.session.add_all(notifications_to_add)
                    db.session.commit()
                    count = len(notifications_to_add)
                flash(_('%(count)s message(s) envoyé(s) avec succès !', count=count), 'success')
            else:
                 flash(_('Aucun utilisateur ne correspond aux critères sélectionnés.'), 'warning')
        except Exception as e:
             db.session.rollback()
             flash(_('Erreur lors de l\'envoi des messages : %(error)s', error=str(e)), 'danger')
        return redirect(url_for('admin.send_message'))
    return render_template('send_message.html', title=_('Envoyer un Message Ciblé'), countries_list=countries_choices_single, devices_list=devices_choices_single)

# --- Routes Approbation Parrainage (Lien Externe) ---
@bp.route('/referrals/pending')
@login_required
@admin_required
def list_pending_referrals():
    page = request.args.get('page', 1, type=int); query = db.select(ExternalTaskCompletion).where(ExternalTaskCompletion.status == 'Pending').options(joinedload(ExternalTaskCompletion.referrer_user), joinedload(ExternalTaskCompletion.task)).order_by(ExternalTaskCompletion.submission_timestamp.asc()); pagination = db.paginate(query, page=page, per_page=current_app.config['COMPLETIONS_PER_PAGE'], error_out=False); submissions = pagination.items
    return render_template('pending_referrals.html', title=_('Approuver les Soumissions Externes'), submissions=submissions, pagination=pagination)

@bp.route('/referral/<int:completion_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_referral(completion_id):
    submission = db.session.get(ExternalTaskCompletion, completion_id) or abort(404);
    if submission.status != 'Pending': flash(_('Cette soumission a déjà été traitée.'), 'warning'); return redirect(url_for('admin.list_pending_referrals'))
    referrer = submission.referrer_user; task = submission.task
    if not referrer or not task: flash(_('Erreur : Utilisateur parrain ou tâche associée introuvable.'), 'danger'); return redirect(url_for('admin.list_pending_referrals'))
    try:
        bonus_amount = Decimal(str(task.reward_amount or 0.0)) * Decimal('0.40'); referrer_balance_decimal = Decimal(str(referrer.balance or 0.0))
        submission.status = 'Approved'; submission.processed_timestamp = datetime.now(timezone.utc); submission.processed_by_admin_id = current_user.id; referrer.balance = float(referrer_balance_decimal + bonus_amount)
        notif = Notification(user_id=referrer.id, name='referral_bonus', payload_json=json.dumps({'message': _('Votre parrainage pour la tâche "%(task_title)s" a été approuvé !', task_title=task.title), 'amount': str(bonus_amount.quantize(Decimal("0.01")))}))
        db.session.add(notif); db.session.commit()
        flash(_('Soumission approuvée. Bonus de %(bonus)s $ crédité à %(user)s.', bonus=bonus_amount.quantize(Decimal("0.01")), user=referrer.full_name), 'success')
    except Exception as e: db.session.rollback(); flash(_('Erreur lors de l\'approbation : %(error)s', error=str(e)), 'danger')
    return redirect(url_for('admin.list_pending_referrals'))

@bp.route('/referral/<int:completion_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_referral(completion_id):
    submission = db.session.get(ExternalTaskCompletion, completion_id) or abort(404);
    if submission.status != 'Pending': flash(_('Cette soumission a déjà été traitée.'), 'warning'); return redirect(url_for('admin.list_pending_referrals'))
    try:
        submission.status = 'Rejected'; submission.processed_timestamp = datetime.now(timezone.utc); submission.processed_by_admin_id = current_user.id;
        db.session.commit()
        flash(_('Soumission rejetée.'), 'info')
    except Exception as e: db.session.rollback(); flash(_('Erreur lors du rejet : %(error)s', error=str(e)), 'danger')
    return redirect(url_for('admin.list_pending_referrals'))

# --- Routes Approbation Commissions (Parrainage Inscription) ---
@bp.route('/commissions/pending')
@login_required
@admin_required
def list_pending_commissions():
    page = request.args.get('page', 1, type=int)
    query = db.select(ReferralCommission).where(ReferralCommission.status == 'Pending').options(joinedload(ReferralCommission.referrer), joinedload(ReferralCommission.referred_user), joinedload(ReferralCommission.originating_completion).joinedload(UserTaskCompletion.task)).order_by(ReferralCommission.creation_timestamp.asc())
    pagination = db.paginate(query, page=page, per_page=current_app.config['COMPLETIONS_PER_PAGE'], error_out=False); commissions = pagination.items
    return render_template('pending_commissions.html', title=_('Approuver les Commissions de Parrainage (3%)'), commissions=commissions, pagination=pagination)

@bp.route('/commission/<int:commission_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_commission(commission_id):
    commission = db.session.get(ReferralCommission, commission_id) or abort(404)
    if commission.status != 'Pending': flash(_('Cette commission a déjà été traitée.'), 'warning'); return redirect(url_for('admin.list_pending_commissions'))
    referrer = commission.referrer
    if not referrer: flash(_('Erreur : Utilisateur parrain associé introuvable.'), 'danger'); return redirect(url_for('admin.list_pending_commissions'))
    try:
        commission.status = 'Approved'; commission.processed_timestamp = datetime.now(timezone.utc); commission.processed_by_admin_id = current_user.id
        commission_amount_decimal = Decimal(str(commission.commission_amount or 0.0)); referrer_balance_decimal = Decimal(str(referrer.balance or 0.0))
        referrer.balance = float(referrer_balance_decimal + commission_amount_decimal)
        notif = Notification(user_id=referrer.id, name='referral_commission_approved', payload_json=json.dumps({'message': _('Une commission de parrainage de $%(amount)s (pour l\'activité de %(referred_user)s) a été ajoutée à votre solde.', amount=commission_amount_decimal.quantize(Decimal("0.01")), referred_user=commission.referred_user.full_name if commission.referred_user else 'un filleul'), 'amount': str(commission_amount_decimal.quantize(Decimal("0.01")))}))
        db.session.add(notif); db.session.commit()
        flash(_('Commission de %(amount)s $ approuvée et créditée à %(user)s.', amount=commission_amount_decimal.quantize(Decimal("0.01")), user=referrer.full_name), 'success')
    except Exception as e: db.session.rollback(); flash(_('Erreur lors de l\'approbation de la commission : %(error)s', error=str(e)), 'danger')
    return redirect(url_for('admin.list_pending_commissions'))

@bp.route('/commission/<int:commission_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_commission(commission_id):
    commission = db.session.get(ReferralCommission, commission_id) or abort(404)
    if commission.status != 'Pending': flash(_('Cette commission a déjà été traitée.'), 'warning'); return redirect(url_for('admin.list_pending_commissions'))
    try:
        commission.status = 'Rejected'; commission.processed_timestamp = datetime.now(timezone.utc); commission.processed_by_admin_id = current_user.id;
        db.session.commit()
        flash(_('Commission rejetée.'), 'info')
    except Exception as e: db.session.rollback(); flash(_('Erreur lors du rejet de la commission : %(error)s', error=str(e)), 'danger')
    return redirect(url_for('admin.list_pending_commissions'))

# --- Route Statistiques ---
@bp.route('/statistics')
@login_required
@admin_required
def statistics():
    search_country = request.args.get('country', ''); search_device = request.args.get('device', '')
    # Calculs des stats clés
    total_users = db.session.scalar(select(func.count(User.id)).where(User.is_admin == False, User.is_banned == False)) or 0
    total_active_tasks = db.session.scalar(select(func.count(Task.id)).where(Task.is_active == True)) or 0
    total_completions = db.session.scalar(select(func.count(UserTaskCompletion.id))) or 0
    total_earnings_generated = db.session.scalar(select(func.sum(Task.reward_amount)).join(UserTaskCompletion, UserTaskCompletion.task_id == Task.id)) or 0.0
    total_withdrawn = db.session.scalar(select(func.sum(Withdrawal.amount)).where(Withdrawal.status == 'Completed')) or 0.0
    pending_external_bonus_sum = db.session.scalar(select(func.sum(Task.reward_amount * 0.40)).join(ExternalTaskCompletion, ExternalTaskCompletion.task_id == Task.id).where(ExternalTaskCompletion.status == 'Pending')) or 0.0
    pending_commission_sum = db.session.scalar(select(func.sum(ReferralCommission.commission_amount)).where(ReferralCommission.status == 'Pending')) or 0.0
    stats_summary = {'total_users': total_users, 'total_active_tasks': total_active_tasks, 'total_completions': total_completions, 'total_earnings_generated': total_earnings_generated, 'total_withdrawn': total_withdrawn, 'pending_external_bonus': pending_external_bonus_sum, 'pending_commission': pending_commission_sum}
    # Requête pour le tableau
    query_table = db.select(User.country, User.device, func.count(UserTaskCompletion.id).label('completion_count')).join(UserTaskCompletion.user).group_by(User.country, User.device)
    if search_country: query_table = query_table.where(User.country == search_country)
    if search_device: query_table = query_table.where(User.device == search_device)
    query_table = query_table.order_by(User.country, User.device); results_table = db.session.execute(query_table).all()
    # Prépare les données pour Chart.js (Utilise to_char pour PG)
    date_format_string = 'YYYY-MM'
    registrations_by_month_query = db.select(func.to_char(User.registration_date, date_format_string).label('month'), func.count(User.id).label('count')).where(User.is_admin == False).group_by(func.to_char(User.registration_date, date_format_string)).order_by(func.to_char(User.registration_date, date_format_string))
    registrations_data = db.session.execute(registrations_by_month_query).all()
    completions_by_month_query = db.select(func.to_char(UserTaskCompletion.completion_timestamp, date_format_string).label('month'), func.count(UserTaskCompletion.id).label('count')).group_by(func.to_char(UserTaskCompletion.completion_timestamp, date_format_string)).order_by(func.to_char(UserTaskCompletion.completion_timestamp, date_format_string))
    completions_data = db.session.execute(completions_by_month_query).all()
    earnings_by_month_query = db.select(func.to_char(UserTaskCompletion.completion_timestamp, date_format_string).label('month'), func.sum(Task.reward_amount).label('total_reward')).join(Task, UserTaskCompletion.task_id == Task.id).group_by(func.to_char(UserTaskCompletion.completion_timestamp, date_format_string)).order_by(func.to_char(UserTaskCompletion.completion_timestamp, date_format_string))
    earnings_data = db.session.execute(earnings_by_month_query).all()
    reg_dict = {row.month: row.count for row in registrations_data}; comp_dict = {row.month: row.count for row in completions_data}; earn_dict = {row.month: float(row.total_reward or 0.0) for row in earnings_data}
    all_months = sorted(list(set(reg_dict.keys()) | set(comp_dict.keys()) | set(earn_dict.keys())))
    chart_labels = all_months; registrations_chart_data = [reg_dict.get(month, 0) for month in all_months]; completions_chart_data = [comp_dict.get(month, 0) for month in all_months]; earnings_chart_data = [earn_dict.get(month, 0) for month in all_months]
    chart_data = {'labels': chart_labels, 'registrations': registrations_chart_data, 'completions': completions_chart_data, 'earnings': earnings_chart_data}
    return render_template('statistics.html', title=_('Statistiques Détaillées'), stats=stats_summary, results=results_table, countries_list=countries_choices_single, devices_list=devices_choices_single, search_country=search_country, search_device=search_device, chart_data=chart_data)

# --- Route pour que l'Admin réinitialise le MDP d'un utilisateur ---
@bp.route('/user/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def admin_reset_user_password(user_id):
    user_to_reset = db.session.get(User, user_id) or abort(404)
    if user_to_reset.is_admin:
        flash(_('Vous ne pouvez pas réinitialiser le mot de passe d\'un administrateur via cette interface.'), 'danger')
        return redirect(url_for('admin.list_users'))

    form = AdminResetPasswordForm() # Utilise le formulaire pour la validation

    if form.validate_on_submit(): # Valide les données POST (incluant CSRF)
        try:
            user_to_reset.set_password(form.new_password.data)
            db.session.commit()
            flash(_('Le mot de passe pour %(user)s a été réinitialisé avec succès. N\'oubliez pas de communiquer le nouveau mot de passe temporaire à l\'utilisateur.', user=user_to_reset.full_name), 'success')
        except Exception as e:
            db.session.rollback()
            flash(_('Erreur lors de la réinitialisation du mot de passe : %(error)s', error=str(e)), 'danger')
    else:
        # Gère les erreurs de validation du formulaire
        error_msg = _('Erreur de validation. Vérifiez que les mots de passe correspondent et font au moins 8 caractères.')
        for field, errors in form.errors.items():
            for error in errors: error_msg = error; break
            break
        flash(error_msg, 'danger')

    return redirect(url_for('admin.list_users')) # Redirige après POST

# --- Routes pour la Gestion des Admins (Super Admin Uniquement) ---
@bp.route('/manage-admins', methods=['GET', 'POST'])
@login_required
@super_admin_required # Seul un super admin peut accéder
def manage_admins():
    form = AddAdminForm()
    if form.validate_on_submit():
        user_to_promote = db.session.scalar(db.select(User).where(User.email == form.email.data))
        if user_to_promote:
            try:
                user_to_promote.is_admin = True
                user_to_promote.is_super_admin = form.is_super.data
                if user_to_promote.id == current_user.id and not current_user.is_super_admin:
                     user_to_promote.is_super_admin = False
                db.session.commit()
                flash(_('Utilisateur %(email)s promu administrateur %(super)s.',
                        email=user_to_promote.email,
                        super=(_(' (Super Admin)') if user_to_promote.is_super_admin else '')), 'success')
                return redirect(url_for('admin.manage_admins'))
            except Exception as e:
                db.session.rollback()
                flash(_('Erreur lors de la promotion de l\'administrateur: %(error)s', error=str(e)), 'danger')
        else:
             flash(_('Utilisateur non trouvé.'), 'danger')

    admins = db.session.scalars(select(User).where(User.is_admin == True).order_by(User.full_name)).all()
    return render_template('manage_admins.html',
                           title=_('Gérer les Administrateurs'),
                           form=form,
                           admins=admins)

@bp.route('/remove-admin/<int:user_id>', methods=['POST'])
@login_required
@super_admin_required
def remove_admin(user_id):
    user_to_demote = db.session.get(User, user_id) or abort(404)
    if user_to_demote.id == current_user.id:
        flash(_('Vous ne pouvez pas retirer vos propres privilèges administrateur.'), 'danger')
        return redirect(url_for('admin.manage_admins'))
    if user_to_demote.email == current_app.config.get('ADMINS', [''])[0]:
         flash(_('Vous ne pouvez pas retirer les privilèges du compte administrateur principal.'), 'danger')
         return redirect(url_for('admin.manage_admins'))
    try:
        user_to_demote.is_admin = False
        user_to_demote.is_super_admin = False
        db.session.commit()
        flash(_('Les privilèges administrateur ont été retirés pour %(email)s.', email=user_to_demote.email), 'success')
    except Exception as e:
        db.session.rollback()
        flash(_('Erreur lors du retrait des privilèges: %(error)s', error=str(e)), 'danger')
    return redirect(url_for('admin.manage_admins'))

@bp.route('/promote-super-admin/<int:user_id>', methods=['POST'])
@login_required
@super_admin_required
def promote_super_admin(user_id):
    user_to_promote = db.session.get(User, user_id) or abort(404)
    if not user_to_promote.is_admin:
         flash(_('Cet utilisateur n\'est pas un administrateur.'), 'warning')
         return redirect(url_for('admin.manage_admins'))
    if user_to_promote.is_super_admin:
         flash(_('Cet utilisateur est déjà un Super Administrateur.'), 'info')
         return redirect(url_for('admin.manage_admins'))
    try:
        user_to_promote.is_super_admin = True
        db.session.commit()
        flash(_('%(email)s a été promu Super Administrateur.', email=user_to_promote.email), 'success')
    except Exception as e:
        db.session.rollback()
        flash(_('Erreur lors de la promotion: %(error)s', error=str(e)), 'danger')
    return redirect(url_for('admin.manage_admins'))

@bp.route('/demote-admin/<int:user_id>', methods=['POST'])
@login_required
@super_admin_required
def demote_admin(user_id):
    user_to_demote = db.session.get(User, user_id) or abort(404)
    if not user_to_demote.is_super_admin:
         flash(_('Cet utilisateur n\'est pas un Super Administrateur.'), 'warning')
         return redirect(url_for('admin.manage_admins'))
    if user_to_demote.id == current_user.id:
         flash(_('Vous ne pouvez pas retirer vos propres privilèges Super Admin.'), 'danger')
         return redirect(url_for('admin.manage_admins'))
    if user_to_demote.email == current_app.config.get('ADMINS', [''])[0]:
         flash(_('Vous ne pouvez pas rétrograder le compte administrateur principal.'), 'danger')
         return redirect(url_for('admin.manage_admins'))
    try:
        user_to_demote.is_super_admin = False
        db.session.commit()
        flash(_('%(email)s a été rétrogradé en Administrateur normal.', email=user_to_demote.email), 'success')
    except Exception as e:
        db.session.rollback()
        flash(_('Erreur lors de la rétrogradation: %(error)s', error=str(e)), 'danger')
    return redirect(url_for('admin.manage_admins'))