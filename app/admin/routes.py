# app/admin/routes.py (VERSION COMPLÈTE v46 - Modération Commentaires + Toutes Fonctions)

from flask import render_template, redirect, url_for, flash, request, abort, current_app, send_from_directory
from flask_login import login_required, current_user
from flask_babel import _
from app import db
from app.admin import bp
# Ajout de BannerForm et PostForm
from app.forms import (TaskForm, countries_choices_multi, devices_choices_multi,
                       countries_choices_single, devices_choices_single,
                       AdminResetPasswordForm, AddAdminForm, BannerForm, PostForm,
                       CustomScriptForm)
# Ajout des modèles Banner, Post, Comment et de la fonction slugify
from app.models import (Task, UserTaskCompletion, ExternalTaskCompletion, User,
                        Withdrawal, Notification, ReferralCommission, Banner, Post, Comment, 
                        CustomScript)
from app.decorators import admin_required, super_admin_required
from sqlalchemy import select, or_, func
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
import json
import os
import secrets
from werkzeug.utils import secure_filename
from flask_wtf.csrf import generate_csrf
# Assurez-vous que cette fonction est bien définie
from app.main.routes import allowed_file

# À ajouter quelque part dans app/admin/routes.py, par exemple après les imports

def get_available_endpoints():
    """
    Récupère une liste de tous les endpoints de l'application avec des noms conviviaux.
    Exclut les endpoints statiques et ceux du blueprint admin lui-même.
    """
    endpoints = []
    # Mappage manuel des endpoints vers des noms conviviaux
    # Étendez cette liste au fur et à mesure que vous ajoutez des pages importantes.
    endpoint_names = {
        'main.index': _l('Page d\'Accueil'),
        'main.dashboard': _l('Tableau de Bord Utilisateur'),
        'main.available_tasks': _l('Tâches Disponibles'),
        'main.completed_tasks': _l('Mes Tâches Accomplies'),
        'main.withdraw': _l('Page de Retrait'),
        'main.notifications': _l('Mes Notifications'),
        'main.profile': _l('Mon Profil'),
        'main.blog_index': _l('Blog - Page Principale'),
        'main.view_post': _l('Blog - Vue d\'un Article'),  # Nom générique car le slug change
        'auth.login': _l('Page de Connexion'),
        'auth.register': _l('Page d\'Inscription'),
        'auth.forgot_password_info': _l('Page Info Mot de Passe Oublié'),
        'auth.logout': _l('Action de Déconnexion (pas une page)'),
        'auth.verify_email': _l('Page de Vérification Email (via lien)'),
        'main.view_external_task': _l('Vue Publique Tâche (pour partage)'),
    }
    # Préfixes des endpoints à exclure systématiquement
    excluded_prefixes = ['static', '_debug_toolbar']
    
    if current_app:  # S'assurer que current_app est disponible
        try:
            for rule in current_app.url_map.iter_rules():
                if rule.endpoint and 'GET' in rule.methods and \
                   not any(rule.endpoint.startswith(prefix) for prefix in excluded_prefixes) and \
                   not rule.endpoint.startswith(bp.name + '.'):  # bp.name est 'admin' pour ce blueprint

                    friendly_name = endpoint_names.get(rule.endpoint, rule.endpoint)
                    current_endpoint_tuple = (rule.endpoint, friendly_name)
                    if current_endpoint_tuple not in endpoints:
                        endpoints.append(current_endpoint_tuple)
            endpoints.sort(key=lambda x: x[1])
            current_app.logger.debug(f"Endpoints générés pour le formulaire : {endpoints}")
        except Exception as e:
            current_app.logger.error(f"Erreur lors de la récupération des endpoints pour le formulaire: {e}")
    return endpoints

# --- Fonctions utilitaires pour images (tâches, bannières, articles) ---
def save_picture(form_picture, subfolder='tasks'):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    upload_folder_base = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, 'static/uploads'))
    picture_folder = os.path.join(upload_folder_base, subfolder)
    os.makedirs(picture_folder, exist_ok=True)
    picture_path = os.path.join(picture_folder, picture_fn)
    try:
        form_picture.save(picture_path)
        return picture_fn
    except Exception as e:
        print(f"Erreur sauvegarde image dans {subfolder}: {e}")
        flash(_('Erreur lors de la sauvegarde de l\'image.'), 'danger')
        return None

def delete_picture(filename, subfolder='tasks'):
    if not filename: return
    try:
        upload_folder_base = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, 'static/uploads'))
        picture_folder = os.path.join(upload_folder_base, subfolder)
        file_path = os.path.join(picture_folder, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Image supprimée de {subfolder}: {filename}")
    except Exception as e:
        print(f"Erreur suppression image {filename} de {subfolder}: {e}")

# --- Route pour l'accueil Admin ---
@bp.route('/')
@login_required
@admin_required
def index():
    twelve_months_ago = datetime.now(timezone.utc) - timedelta(days=365)
    date_format_string = 'YYYY-MM'
    registrations_by_month_query = db.select(func.to_char(User.registration_date, date_format_string).label('month'), func.count(User.id).label('count')).where(User.is_admin == False, User.registration_date >= twelve_months_ago).group_by(func.to_char(User.registration_date, date_format_string)).order_by(func.to_char(User.registration_date, date_format_string))
    registrations_data = db.session.execute(registrations_by_month_query).all()
    completions_by_month_query = db.select(func.to_char(UserTaskCompletion.completion_timestamp, date_format_string).label('month'), func.count(UserTaskCompletion.id).label('count')).where(UserTaskCompletion.completion_timestamp >= twelve_months_ago).group_by(func.to_char(UserTaskCompletion.completion_timestamp, date_format_string)).order_by(func.to_char(UserTaskCompletion.completion_timestamp, date_format_string))
    completions_data = db.session.execute(completions_by_month_query).all()
    earnings_by_month_query = db.select(func.to_char(UserTaskCompletion.completion_timestamp, date_format_string).label('month'), func.sum(Task.reward_amount).label('total_reward')).join(Task, UserTaskCompletion.task_id == Task.id).where(UserTaskCompletion.completion_timestamp >= twelve_months_ago).group_by(func.to_char(UserTaskCompletion.completion_timestamp, date_format_string)).order_by(func.to_char(UserTaskCompletion.completion_timestamp, date_format_string))
    earnings_data = db.session.execute(earnings_by_month_query).all()
    reg_dict = {row.month: row.count for row in registrations_data}
    comp_dict = {row.month: row.count for row in completions_data}
    earn_dict = {row.month: float(row.total_reward or 0.0) for row in earnings_data}
    chart_labels = []
    current_month_date = datetime.now(timezone.utc)
    for i in range(12):
        month_label = (current_month_date - timedelta(days=i*30)).strftime('%Y-%m')
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
    return render_template('admin_home.html', title=_('Panneau Administrateur'), chart_data=chart_data)

# --- Routes pour la gestion des Tâches ---
@bp.route('/tasks/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_task():
    form = TaskForm()
    if form.validate_on_submit():
        image_file = None
        if form.task_image.data:
            image_file = save_picture(form.task_image.data, subfolder='tasks')
            if not image_file: return redirect(url_for('admin.create_task'))
        selected_countries = form.target_countries.data; countries_to_save = 'ALL' if 'ALL' in selected_countries or not selected_countries else ','.join(selected_countries)
        selected_devices = form.target_devices.data; devices_to_save = 'ALL' if 'ALL' in selected_devices or not selected_devices else ','.join(selected_devices)
        new_task = Task(
            title=form.title.data, description=form.description.data,
            instructions=form.instructions.data, task_link=form.task_link.data,
            reward_amount=form.reward_amount.data, target_countries=countries_to_save,
            target_devices=devices_to_save, is_active=form.is_active.data,
            image_filename=image_file,
            is_daily=form.is_daily.data
        )
        try:
            db.session.add(new_task)
            db.session.commit()
            flash(_('La nouvelle tâche "%(title)s" a été créée avec succès !', title=new_task.title), 'success')
            if new_task.is_active:
                target_country_list = countries_to_save.split(',') if countries_to_save != 'ALL' else []
                target_device_list = devices_to_save.split(',') if devices_to_save != 'ALL' else []
                user_query = select(User.id).where(User.is_admin == False, User.is_banned == False)
                if countries_to_save != 'ALL' and target_country_list: user_query = user_query.where(User.country.in_(target_country_list))
                if devices_to_save != 'ALL' and target_device_list: user_query = user_query.where(User.device.in_(target_device_list))
                eligible_user_ids = db.session.scalars(user_query).all()
                if eligible_user_ids:
                    notifications_to_add = []
                    for user_id_notif in eligible_user_ids:
                        notif = Notification(user_id=user_id_notif, name='new_task_available', payload_json=json.dumps({'task_id': new_task.id, 'task_title': new_task.title}))
                        notifications_to_add.append(notif)
                    if notifications_to_add:
                        db.session.add_all(notifications_to_add)
                        db.session.commit()
                        print(f"INFO: Sent 'new_task_available' notification to {len(notifications_to_add)} users for task {new_task.id}")
            return redirect(url_for('admin.list_tasks'))
        except Exception as e:
            db.session.rollback()
            if image_file: delete_picture(image_file, subfolder='tasks')
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
    task = db.session.get(Task, task_id) or abort(404)
    form = TaskForm(obj=task if request.method == 'GET' else None)
    old_image_filename = task.image_filename
    if request.method == 'GET':
        form.target_countries.data = task.target_countries.split(',') if task.target_countries and task.target_countries != 'ALL' else (['ALL'] if task.target_countries == 'ALL' else [])
        form.target_devices.data = task.target_devices.split(',') if task.target_devices and task.target_devices != 'ALL' else (['ALL'] if task.target_devices == 'ALL' else [])
        form.is_daily.data = task.is_daily
    if form.validate_on_submit():
        new_image_filename = None
        if form.task_image.data:
            new_image_filename = save_picture(form.task_image.data, subfolder='tasks')
            if not new_image_filename:
                 return render_template('create_task.html', title=_('Modifier la Tâche'), form=form, is_edit=True, task_id=task_id, current_image=old_image_filename)
            else:
                if old_image_filename: delete_picture(old_image_filename, subfolder='tasks')
                task.image_filename = new_image_filename
        
        old_status = task.is_active
        selected_countries = form.target_countries.data; countries_to_save = 'ALL' if 'ALL' in selected_countries or not selected_countries else ','.join(selected_countries)
        selected_devices = form.target_devices.data; devices_to_save = 'ALL' if 'ALL' in selected_devices or not selected_devices else ','.join(selected_devices)
        task.title=form.title.data; task.description=form.description.data; task.instructions=form.instructions.data; task.task_link=form.task_link.data; task.reward_amount=form.reward_amount.data; task.target_countries=countries_to_save; task.target_devices=devices_to_save; task.is_active=form.is_active.data
        task.is_daily=form.is_daily.data
        try:
            db.session.commit()
            flash(_('Tâche "%(title)s" mise à jour avec succès !', title=task.title), 'success')
            if not old_status and task.is_active:
                target_country_list = countries_to_save.split(',') if countries_to_save != 'ALL' else []
                target_device_list = devices_to_save.split(',') if devices_to_save != 'ALL' else []
                user_query = select(User.id).where(User.is_admin == False, User.is_banned == False)
                if countries_to_save != 'ALL' and target_country_list: user_query = user_query.where(User.country.in_(target_country_list))
                if devices_to_save != 'ALL' and target_device_list: user_query = user_query.where(User.device.in_(target_device_list))
                eligible_user_ids = db.session.scalars(user_query).all()
                if eligible_user_ids:
                    notifications_to_add = [];
                    for user_id_notif in eligible_user_ids:
                        already_done = db.session.scalar(select(UserTaskCompletion.id).where(UserTaskCompletion.user_id==user_id_notif, UserTaskCompletion.task_id==task.id))
                        if not already_done:
                            notifications_to_add.append(Notification(user_id=user_id_notif, name='new_task_available', payload_json=json.dumps({'task_id': task.id, 'task_title': task.title})))
                    if notifications_to_add:
                        db.session.add_all(notifications_to_add)
                        db.session.commit()
                        print(f"INFO: Sent 'new_task_available' notification to {len(notifications_to_add)} users for task {task.id} upon activation.")
            return redirect(url_for('admin.list_tasks'))
        except Exception as e:
            db.session.rollback()
            if new_image_filename: delete_picture(new_image_filename, subfolder='tasks')
            flash(_("Erreur lors de la mise à jour de la tâche : %(error)s", error=str(e)), 'danger')
    return render_template('create_task.html', title=_('Modifier la Tâche'), form=form, is_edit=True, task_id=task_id, current_image=old_image_filename)

@bp.route('/task/<int:task_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_task(task_id):
    task_to_delete = db.session.get(Task, task_id) or abort(404)
    title_copy = task_to_delete.title
    image_to_delete = task_to_delete.image_filename
    try:
        uc_stmt = db.delete(UserTaskCompletion).where(UserTaskCompletion.task_id == task_id); db.session.execute(uc_stmt)
        ec_stmt = db.delete(ExternalTaskCompletion).where(ExternalTaskCompletion.task_id == task_id); db.session.execute(ec_stmt)
        db.session.delete(task_to_delete)
        db.session.commit()
        if image_to_delete: delete_picture(image_to_delete, subfolder='tasks')
        flash(_('Tâche "%(title)s" supprimée avec succès.', title=title_copy), 'success')
    except Exception as e: db.session.rollback(); flash(_('Erreur lors de la suppression : %(error)s', error=str(e)), 'danger')
    return redirect(url_for('admin.list_tasks'))

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

@bp.route('/withdrawals')
@login_required
@admin_required
def list_withdrawals():
    page_users = request.args.get('page_users', 1, type=int)
    page_history = request.args.get('page_history', 1, type=int)
    search_name = request.args.get('name', '')
    search_email = request.args.get('email', '')
    users_query = db.select(User).where(User.is_admin == False)
    if search_name: users_query = users_query.where(User.full_name.ilike(f'%{search_name}%'))
    if search_email: users_query = users_query.where(User.email.ilike(f'%{search_email}%'))
    users_query = users_query.order_by(User.full_name)
    users_pagination = db.paginate(users_query, page=page_users, per_page=current_app.config.get('USERS_PER_PAGE', 15), error_out=False)
    users = users_pagination.items
    history_query = db.select(Withdrawal)\
        .options(joinedload(Withdrawal.requester), joinedload(Withdrawal.processed_by_admin))\
        .where(Withdrawal.status == 'Completed')\
        .order_by(Withdrawal.processed_timestamp.desc())
    history_pagination = db.paginate(history_query, page=page_history, per_page=current_app.config.get('HISTORY_PER_PAGE', 20), error_out=False)
    withdrawal_history = history_pagination.items
    return render_template('withdrawal_list.html',
                           title=_('Gestion Retraits / Soldes Utilisateurs'),
                           users=users,
                           users_pagination=users_pagination,
                           withdrawal_history=withdrawal_history,
                           history_pagination=history_pagination,
                           search_name=search_name,
                           search_email=search_email)

@bp.route('/withdrawal/record/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def record_withdrawal(user_id):
    user = db.session.get(User, user_id) or abort(404); amount_str = request.form.get('amount')
    page_users = request.args.get('page_users', 1, type=int)
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
    return redirect(url_for('admin.list_withdrawals', page_users=page_users))

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
    csrf_token_value = generate_csrf()
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
                           csrf_token=csrf_token_value)

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
                for user_id_notif in target_user_ids:
                    notifications_to_add.append(Notification(user_id=user_id_notif, name='admin_message', payload_json=json.dumps({'subject': subject.strip(), 'message': body.strip()})))
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
        bonus_amount = Decimal(str(task.reward_amount or 0.0)) * Decimal('0.85');
        referrer_balance_decimal = Decimal(str(referrer.balance or 0.0))
        submission.status = 'Approved'; submission.processed_timestamp = datetime.now(timezone.utc); submission.processed_by_admin_id = current_user.id; referrer.balance = float(referrer_balance_decimal + bonus_amount)
        notif = Notification(user_id=referrer.id, name='referral_bonus', payload_json=json.dumps({'message': _('Votre parrainage pour la tâche "%(task_title)s" a été approuvé !', task_title=task.title), 'amount': str(bonus_amount.quantize(Decimal("0.01")))}))
        db.session.add(notif); db.session.commit()
        flash(_('Soumission approuvée. Bonus de %(bonus)s $ (85%%) crédité à %(user)s.', bonus=bonus_amount.quantize(Decimal("0.01")), user=referrer.full_name), 'success')
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

@bp.route('/statistics')
@login_required
@admin_required
def statistics():
    search_country = request.args.get('country', ''); search_device = request.args.get('device', '')
    total_users = db.session.scalar(select(func.count(User.id)).where(User.is_admin == False, User.is_banned == False)) or 0
    total_active_tasks = db.session.scalar(select(func.count(Task.id)).where(Task.is_active == True)) or 0
    total_completions = db.session.scalar(select(func.count(UserTaskCompletion.id))) or 0
    total_earnings_generated = db.session.scalar(select(func.sum(Task.reward_amount)).join(UserTaskCompletion, UserTaskCompletion.task_id == Task.id)) or 0.0
    total_withdrawn = db.session.scalar(select(func.sum(Withdrawal.amount)).where(Withdrawal.status == 'Completed')) or 0.0
    pending_external_bonus_sum = db.session.scalar(select(func.sum(Task.reward_amount * 0.85)).join(ExternalTaskCompletion, ExternalTaskCompletion.task_id == Task.id).where(ExternalTaskCompletion.status == 'Pending')) or 0.0
    pending_commission_sum = db.session.scalar(select(func.sum(ReferralCommission.commission_amount)).where(ReferralCommission.status == 'Pending')) or 0.0
    stats_summary = {'total_users': total_users, 'total_active_tasks': total_active_tasks, 'total_completions': total_completions, 'total_earnings_generated': total_earnings_generated, 'total_withdrawn': total_withdrawn, 'pending_external_bonus': pending_external_bonus_sum, 'pending_commission': pending_commission_sum}
    query_table = db.select(User.country, User.device, func.count(UserTaskCompletion.id).label('completion_count')).join(UserTaskCompletion.user).group_by(User.country, User.device)
    if search_country: query_table = query_table.where(User.country == search_country)
    if search_device: query_table = query_table.where(User.device == search_device)
    query_table = query_table.order_by(User.country, User.device); results_table = db.session.execute(query_table).all()
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

@bp.route('/user/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def admin_reset_user_password(user_id):
    user_to_reset = db.session.get(User, user_id) or abort(404)
    if user_to_reset.is_admin:
        flash(_('Vous ne pouvez pas réinitialiser le mot de passe d\'un administrateur via cette interface.'), 'danger')
        return redirect(url_for('admin.list_users'))
    form = AdminResetPasswordForm()
    if form.validate_on_submit():
        try:
            user_to_reset.set_password(form.new_password.data)
            db.session.commit()
            flash(_('Le mot de passe pour %(user)s a été réinitialisé avec succès. N\'oubliez pas de communiquer le nouveau mot de passe temporaire à l\'utilisateur.', user=user_to_reset.full_name), 'success')
        except Exception as e:
            db.session.rollback()
            flash(_('Erreur lors de la réinitialisation du mot de passe : %(error)s', error=str(e)), 'danger')
    else:
        error_msg = _('Erreur de validation. Vérifiez que les mots de passe correspondent et font au moins 8 caractères.')
        for field, errors in form.errors.items():
            for error in errors: error_msg = error; break
            break
        flash(error_msg, 'danger')
    return redirect(url_for('admin.list_users'))

@bp.route('/manage-admins', methods=['GET', 'POST'])
@login_required
@super_admin_required
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

# --- Routes pour la Gestion des Bannières ---
@bp.route('/banners', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_banners():
    form = BannerForm()
    if form.validate_on_submit():
        image_file = None
        if form.banner_image.data:
            image_file = save_picture(form.banner_image.data, subfolder='banners')
            if not image_file:
                return redirect(url_for('admin.manage_banners'))
        new_banner = Banner(
            image_filename=image_file,
            destination_url=form.destination_url.data or None,
            display_location=form.display_location.data,
            is_active=form.is_active.data
        )
        try:
            db.session.add(new_banner)
            db.session.commit()
            flash(_('Nouvelle bannière ajoutée avec succès !'), 'success')
            return redirect(url_for('admin.manage_banners'))
        except Exception as e:
            db.session.rollback()
            if image_file: delete_picture(image_file, subfolder='banners')
            flash(_("Erreur lors de l'ajout de la bannière : %(error)s", error=str(e)), 'danger')
    banners = db.session.scalars(select(Banner).order_by(Banner.uploaded_at.desc())).all()
    return render_template('manage_banners.html', title=_('Gérer les Bannières Publicitaires'), form=form, banners=banners)

@bp.route('/banner/<int:banner_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_banner(banner_id):
    banner = db.session.get(Banner, banner_id) or abort(404)
    form = BannerForm(obj=banner if request.method == 'GET' else None)
    old_image_filename = banner.image_filename
    if form.validate_on_submit():
        new_image_filename = None
        if form.banner_image.data: # Si une nouvelle image est uploadée
            new_image_filename = save_picture(form.banner_image.data, subfolder='banners')
            if not new_image_filename:
                return render_template('create_banner.html', title=_('Modifier la Bannière'), form=form, banner=banner, is_edit=True, current_image=old_image_filename)
            else:
                if old_image_filename:
                    delete_picture(old_image_filename, subfolder='banners')
                banner.image_filename = new_image_filename
        # Si pas de nouvelle image, banner.image_filename reste inchangé
        banner.destination_url = form.destination_url.data or None
        banner.display_location = form.display_location.data
        banner.is_active = form.is_active.data
        try:
            db.session.commit()
            flash(_('Bannière mise à jour avec succès !'), 'success')
            return redirect(url_for('admin.manage_banners'))
        except Exception as e:
            db.session.rollback()
            if new_image_filename and new_image_filename != old_image_filename: # Si une nouvelle image avait été sauvée
                delete_picture(new_image_filename, subfolder='banners')
            flash(_("Erreur lors de la mise à jour de la bannière : %(error)s", error=str(e)), 'danger')
    return render_template('create_banner.html', title=_('Modifier la Bannière'), form=form, banner=banner, is_edit=True, current_image=old_image_filename)

@bp.route('/banner/<int:banner_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_banner(banner_id):
    banner_to_delete = db.session.get(Banner, banner_id) or abort(404)
    image_to_delete = banner_to_delete.image_filename
    try:
        db.session.delete(banner_to_delete)
        db.session.commit()
        if image_to_delete:
            delete_picture(image_to_delete, subfolder='banners')
        flash(_('Bannière supprimée avec succès.'), 'success')
    except Exception as e:
        db.session.rollback()
        flash(_('Erreur lors de la suppression de la bannière : %(error)s', error=str(e)), 'danger')
    return redirect(url_for('admin.manage_banners'))

@bp.route('/banner/<int:banner_id>/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_banner_active(banner_id):
    banner = db.session.get(Banner, banner_id) or abort(404)
    try:
        banner.is_active = not banner.is_active
        db.session.commit()
        status_msg = _('activée') if banner.is_active else _('désactivée')
        flash(_('Bannière %(id)s %(status)s.', id=banner.id, status=status_msg), 'success')
    except Exception as e:
        db.session.rollback()
        flash(_('Erreur lors du changement de statut de la bannière: %(error)s', error=str(e)), 'danger')
    return redirect(url_for('admin.manage_banners'))

# --- Routes pour la Gestion des Articles de Blog ---
@bp.route('/blog/posts', methods=['GET'])
@login_required
@admin_required
def manage_posts():
    posts = db.session.scalars(select(Post).order_by(Post.timestamp.desc())).all()
    csrf_token_value = generate_csrf()
    return render_template('manage_posts.html', title=_('Gérer les Articles de Blog'), posts=posts, csrf_token=csrf_token_value)

@bp.route('/blog/post/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        image_file = None
        if form.post_image.data:
            image_file = save_picture(form.post_image.data, subfolder='blog_posts')
            if not image_file:
                return render_template('create_post.html', title=_('Créer un Nouvel Article'), form=form, is_edit=False)
        unique_slug = Post.generate_unique_slug(form.title.data)
        new_post = Post(
            title=form.title.data,
            slug=unique_slug,
            content=form.content.data,
            user_id=current_user.id,
            image_filename=image_file,
            allow_comments=form.allow_comments.data,
            is_published=form.is_published.data
        )
        try:
            db.session.add(new_post)
            db.session.commit()
            flash(_('Nouvel article de blog créé avec succès !'), 'success')
            return redirect(url_for('admin.manage_posts'))
        except Exception as e:
            db.session.rollback()
            if image_file: delete_picture(image_file, subfolder='blog_posts')
            flash(_("Erreur lors de la création de l'article : %(error)s", error=str(e)), 'danger')
    return render_template('create_post.html', title=_('Créer un Nouvel Article'), form=form, is_edit=False)

@bp.route('/blog/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_post(post_id):
    post_to_edit = db.session.get(Post, post_id) or abort(404)
    form = PostForm(obj=post_to_edit if request.method == 'GET' else None)
    old_image_filename = post_to_edit.image_filename
    old_title = post_to_edit.title
    if form.validate_on_submit():
        new_image_filename = None
        if form.post_image.data:
            new_image_filename = save_picture(form.post_image.data, subfolder='blog_posts')
            if not new_image_filename:
                return render_template('create_post.html', title=_('Modifier l\'Article'), form=form, post=post_to_edit, is_edit=True, current_image=old_image_filename)
            else:
                if old_image_filename:
                    delete_picture(old_image_filename, subfolder='blog_posts')
                post_to_edit.image_filename = new_image_filename
        post_to_edit.title = form.title.data
        if post_to_edit.title != old_title:
            post_to_edit.slug = Post.generate_unique_slug(form.title.data, post_id=post_to_edit.id)
        post_to_edit.content = form.content.data
        post_to_edit.allow_comments = form.allow_comments.data
        post_to_edit.is_published = form.is_published.data
        try:
            db.session.commit()
            flash(_('Article "%(title)s" mis à jour avec succès !', title=post_to_edit.title), 'success')
            return redirect(url_for('admin.manage_posts'))
        except Exception as e:
            db.session.rollback()
            if new_image_filename and new_image_filename != old_image_filename:
                delete_picture(new_image_filename, subfolder='blog_posts')
            flash(_("Erreur lors de la mise à jour de l'article : %(error)s", error=str(e)), 'danger')
    if request.method == 'GET':
        form.title.data = post_to_edit.title
        form.content.data = post_to_edit.content
        form.allow_comments.data = post_to_edit.allow_comments
        form.is_published.data = post_to_edit.is_published
    return render_template('create_post.html', title=_('Modifier l\'Article'), form=form, post=post_to_edit, is_edit=True, current_image=old_image_filename)

@bp.route('/blog/post/<int:post_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_post(post_id):
    post_to_delete = db.session.get(Post, post_id) or abort(404)
    title_copy = post_to_delete.title
    image_to_delete = post_to_delete.image_filename
    try:
        db.session.delete(post_to_delete)
        db.session.commit()
        if image_to_delete:
            delete_picture(image_to_delete, subfolder='blog_posts')
        flash(_('Article "%(title)s" et ses commentaires supprimés avec succès.', title=title_copy), 'success')
    except Exception as e:
        db.session.rollback()
        flash(_('Erreur lors de la suppression de l\'article : %(error)s', error=str(e)), 'danger')
    return redirect(url_for('admin.manage_posts'))

@bp.route('/blog/post/<int:post_id>/toggle_published', methods=['POST'])
@login_required
@admin_required
def toggle_post_published(post_id):
    post = db.session.get(Post, post_id) or abort(404)
    try:
        post.is_published = not post.is_published
        db.session.commit()
        status_msg = _('publié') if post.is_published else _('dépublié (brouillon)')
        flash(_('Article "%(title)s" maintenant %(status)s.', title=post.title, status=status_msg), 'success')
    except Exception as e:
        db.session.rollback()
        flash(_('Erreur lors du changement de statut de publication: %(error)s', error=str(e)), 'danger')
    return redirect(url_for('admin.manage_posts'))

@bp.route('/blog/post/<int:post_id>/toggle_comments', methods=['POST'])
@login_required
@admin_required
def toggle_post_comments(post_id):
    post = db.session.get(Post, post_id) or abort(404)
    try:
        post.allow_comments = not post.allow_comments
        db.session.commit()
        status_msg = _('autorisés') if post.allow_comments else _('désactivés')
        flash(_('Commentaires pour l\'article "%(title)s" maintenant %(status)s.', title=post.title, status=status_msg), 'success')
    except Exception as e:
        db.session.rollback()
        flash(_('Erreur lors du changement de statut des commentaires: %(error)s', error=str(e)), 'danger')
    return redirect(url_for('admin.manage_posts'))

# --- Routes pour la Modération des Commentaires du Blog ---
# (Assurez-vous d'avoir cet import en haut de votre fichier app/admin/routes.py)
# from flask_wtf.csrf import generate_csrf

@bp.route('/blog/comments', methods=['GET'])
@login_required
@admin_required
def manage_comments():
    page = request.args.get('page', 1, type=int)
    search_author = request.args.get('author', '')
    search_post_title = request.args.get('post_title', '')
    search_content = request.args.get('content', '')

    comments_query = select(Comment).options(
        joinedload(Comment.author),
        joinedload(Comment.post)
    )
    if search_author:
        comments_query = comments_query.join(Comment.author).where(User.full_name.ilike(f'%{search_author}%'))
    if search_post_title:
        comments_query = comments_query.join(Comment.post).where(Post.title.ilike(f'%{search_post_title}%'))
    if search_content:
        comments_query = comments_query.where(Comment.body.ilike(f'%{search_content}%'))

    comments_query = comments_query.order_by(Comment.timestamp.desc())
    # Utilise COMMENTS_PER_PAGE depuis config, avec un fallback
    pagination = db.paginate(comments_query, page=page, per_page=current_app.config.get('COMMENTS_PER_PAGE', 20), error_out=False)
    comments = pagination.items
    
    # <<< AJOUT ICI : Générer le token CSRF >>>
    csrf_token_value = generate_csrf()

    return render_template('manage_comments.html',
                           title=_('Modérer les Commentaires du Blog'),
                           comments=comments,
                           pagination=pagination,
                           search_author=search_author,
                           search_post_title=search_post_title,
                           search_content=search_content,
                           csrf_token=csrf_token_value) # <<< Passer le token ici >>>

@bp.route('/blog/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_comment(comment_id):
    comment_to_delete = db.session.get(Comment, comment_id) or abort(404)
    # Récupère le slug avant la suppression pour une redirection potentielle
    post_slug_redirect = comment_to_delete.post.slug if comment_to_delete.post else None
    try:
        # La suppression en cascade (configurée dans le modèle Comment pour les réponses)
        # devrait s'occuper des réponses à ce commentaire.
        db.session.delete(comment_to_delete)
        db.session.commit()
        flash(_('Commentaire supprimé avec succès.'), 'success')
    except Exception as e:
        db.session.rollback()
        flash(_('Erreur lors de la suppression du commentaire : %(error)s', error=str(e)), 'danger')
    
    # Tente de rediriger vers la page précédente (manage_comments) si possible,
    # sinon vers la page de l'article, ou en dernier recours vers la liste des articles.
    if request.referrer and url_for('admin.manage_comments') in request.referrer:
        return redirect(request.referrer) # Retourne à la page de modération avec les filtres/pagination
    elif post_slug_redirect:
        return redirect(url_for('main.view_post', slug=post_slug_redirect))
    return redirect(url_for('admin.manage_posts')) # Fallback général

@bp.route('/blog/comment/<int:comment_id>/toggle_approved', methods=['POST'])
@login_required
@admin_required
def toggle_comment_approved(comment_id):
    comment = db.session.get(Comment, comment_id) or abort(404)
    try:
        comment.is_approved = not comment.is_approved
        db.session.commit()
        status_msg = _('approuvé') if comment.is_approved else _('désapprouvé')
        flash(_('Commentaire %(id)s %(status)s.', id=comment.id, status=status_msg), 'success')
    except Exception as e:
        db.session.rollback()
        flash(_('Erreur lors du changement de statut du commentaire: %(error)s', error=str(e)), 'danger')
    # Redirige vers la page précédente (manage_comments) en conservant la page de pagination
    return redirect(request.referrer or url_for('admin.manage_comments'))
# À ajouter à la fin de app/admin/routes.py

# <<< NOUVELLES ROUTES POUR LA GESTION DES SCRIPTS PERSONNALISÉS >>>
@bp.route('/custom-scripts', methods=['GET', 'POST'])
@login_required
@super_admin_required # Ou @admin_required si tous les admins peuvent gérer
def manage_custom_scripts():
    form = CustomScriptForm()
    if form.validate_on_submit():
        new_script = CustomScript(
            name=form.name.data,
            script_code=form.script_code.data,
            location=form.location.data,
            excluded_endpoints=form.excluded_endpoints.data,
            is_active=form.is_active.data,
            description=form.description.data
        )
        try:
            db.session.add(new_script)
            db.session.commit()
            flash(_('Nouveau script personnalisé "%(name)s" ajouté avec succès !', name=new_script.name), 'success')
            return redirect(url_for('admin.manage_custom_scripts'))
        except Exception as e:
            db.session.rollback()
            flash(_("Erreur lors de l'ajout du script personnalisé : %(error)s", error=str(e)), 'danger')
            current_app.logger.error(f"Erreur ajout CustomScript: {e}")

    scripts = db.session.scalars(select(CustomScript).order_by(CustomScript.name)).all()
    return render_template('manage_custom_scripts.html', title=_('Gérer les Scripts Personnalisés'), form=form, scripts=scripts)

@bp.route('/custom-script/<int:script_id>/edit', methods=['GET', 'POST'])
@login_required
@super_admin_required # Ou @admin_required
def edit_custom_script(script_id):
    script_to_edit = db.session.get(CustomScript, script_id) or abort(404)
    form = CustomScriptForm(obj=script_to_edit) # Pré-remplit avec les données existantes

    if form.validate_on_submit():
        script_to_edit.name = form.name.data
        script_to_edit.script_code = form.script_code.data
        script_to_edit.location = form.location.data
        script_to_edit.excluded_endpoints = form.excluded_endpoints.data
        script_to_edit.is_active = form.is_active.data
        script_to_edit.description = form.description.data
        try:
            db.session.commit()
            flash(_('Script personnalisé "%(name)s" mis à jour avec succès !', name=script_to_edit.name), 'success')
            return redirect(url_for('admin.manage_custom_scripts'))
        except Exception as e:
            db.session.rollback()
            flash(_("Erreur lors de la mise à jour du script : %(error)s", error=str(e)), 'danger')
            current_app.logger.error(f"Erreur MAJ CustomScript {script_id}: {e}")

    # Pour GET, le formulaire est déjà pré-rempli par obj=script_to_edit
    # Mais on peut s'assurer que les champs Textarea sont bien remplis
    if request.method == 'GET':
        form.script_code.data = script_to_edit.script_code
        form.excluded_endpoints.data = script_to_edit.excluded_endpoints
        form.description.data = script_to_edit.description

    return render_template('create_custom_script.html', title=_('Modifier le Script Personnalisé'), form=form, script=script_to_edit, is_edit=True)

@bp.route('/custom-script/<int:script_id>/delete', methods=['POST'])
@login_required
@super_admin_required # Ou @admin_required
def delete_custom_script(script_id):
    script_to_delete = db.session.get(CustomScript, script_id) or abort(404)
    try:
        db.session.delete(script_to_delete)
        db.session.commit()
        flash(_('Script personnalisé "%(name)s" supprimé avec succès.', name=script_to_delete.name), 'success')
    except Exception as e:
        db.session.rollback()
        flash(_('Erreur lors de la suppression du script : %(error)s', error=str(e)), 'danger')
        current_app.logger.error(f"Erreur suppression CustomScript {script_id}: {e}")
    return redirect(url_for('admin.manage_custom_scripts'))

@bp.route('/custom-script/<int:script_id>/toggle_active', methods=['POST'])
@login_required
@super_admin_required # Ou @admin_required
def toggle_custom_script_active(script_id):
    script = db.session.get(CustomScript, script_id) or abort(404)
    try:
        script.is_active = not script.is_active
        db.session.commit()
        status_msg = _('activé') if script.is_active else _('désactivé')
        flash(_('Script "%(name)s" maintenant %(status)s.', name=script.name, status=status_msg), 'success')
    except Exception as e:
        db.session.rollback()
        flash(_('Erreur lors du changement de statut du script: %(error)s', error=str(e)), 'danger')
        current_app.logger.error(f"Erreur toggle CustomScript {script_id}: {e}")
    return redirect(url_for('admin.manage_custom_scripts'))
# <<< FIN NOUVELLES ROUTES POUR SCRIPTS PERSONNALISÉS >>>