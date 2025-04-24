# app/forms.py (VERSION COMPLÈTE v6 - Re-verified)
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SubmitField, SelectField,
                     BooleanField, TextAreaField, DecimalField, SelectMultipleField,
                     ValidationError)
from wtforms import widgets
from wtforms.validators import (DataRequired, Email, EqualTo, Length, ValidationError,
                              NumberRange, Optional, URL)
from app.models import User
from app import db
from flask_babel import lazy_gettext as _l
from flask_login import current_user # Import pour validation mot de passe

# --- Listes de Choix (Pays/Appareils) ---
try:
    import pycountry
    countries_raw = sorted([(c.alpha_2, c.name) for c in pycountry.countries], key=lambda x: x[1])
    countries_choices_multi = [('ALL', _l('Tous les pays'))] + countries_raw
    countries_choices_single = [('', _l('--- Sélectionnez votre pays ---'))] + countries_raw
except Exception as e:
    print(f"ERREUR: pycountry: {e}. Utilisation liste réduite."); countries_choices_multi = [('ALL', _l('Tous les pays')), ('BJ', 'Bénin'), ('FR', 'France')]; countries_choices_single = [('', _l('--- Sélectionnez votre pays ---')), ('BJ', 'Bénin'), ('FR', 'France')]
devices_choices_single = [('', _l('--- Sélectionnez votre appareil ---')), ('Android', 'Android'), ('iOS', 'iPhone (iOS)'), ('PC', 'PC (Windows/Mac/Linux)')]
devices_choices_multi = [('ALL', _l('Tous les appareils')), ('Android', 'Android'), ('iOS', 'iOS'), ('PC', 'PC')]

# --- Formulaire d'Inscription ---
class RegistrationForm(FlaskForm):
    full_name = StringField(_l('Nom complet'), validators=[DataRequired(_l('Le nom complet est requis.'))])
    email = StringField(_l('Adresse Email'), validators=[DataRequired(_l('L\'adresse email est requise.')), Email(_l('Adresse email invalide.'))])
    phone_number = StringField(_l('Numéro de téléphone (Optionnel)'))
    country = SelectField(_l('Pays'), choices=countries_choices_single, validators=[DataRequired(_l('Veuillez sélectionner votre pays.'))])
    device = SelectField(_l('Appareil Principal'), choices=devices_choices_single, validators=[DataRequired(_l('Veuillez sélectionner votre appareil.'))])
    password = PasswordField(_l('Mot de passe'), validators=[DataRequired(_l('Le mot de passe est requis.')),Length(min=8, message=_l('Le mot de passe doit contenir au moins 8 caractères.'))])
    password2 = PasswordField(_l('Confirmer le mot de passe'), validators=[DataRequired(_l('Veuillez confirmer le mot de passe.')), EqualTo('password', message=_l('Les mots de passe doivent correspondre.'))])
    submit = SubmitField(_l('S\'inscrire'))

    def validate_email(self, email):
        user = db.session.scalar(db.select(User).where(User.email == email.data))
        if user is not None:
            raise ValidationError(_l('Cette adresse email est déjà utilisée. Veuillez en choisir une autre.'))

# --- Formulaire de Connexion ---
class LoginForm(FlaskForm):
    email = StringField(_l('Adresse Email'), validators=[DataRequired(_l("L'adresse email est requise.")), Email(_l('Adresse email invalide.'))])
    password = PasswordField(_l('Mot de passe'), validators=[DataRequired(_l('Le mot de passe est requis.'))])
    remember_me = BooleanField(_l('Se souvenir de moi'))
    submit = SubmitField(_l('Connexion'))

# --- Formulaire de Tâche ---
class TaskForm(FlaskForm):
    title = StringField(_l('Titre de la tâche'), validators=[DataRequired(_l('Le titre est requis.'))])
    description = TextAreaField(_l('Description détaillée'), validators=[DataRequired(_l('La description est requise.'))], render_kw={'rows': 5})
    instructions = TextAreaField(_l('Instructions spécifiques (Optionnel)'), render_kw={'rows': 3})
    task_link = StringField(_l('Lien de la Tâche (URL directe, optionnel)'), validators=[Optional(), URL(message=_l('Veuillez entrer une URL valide (ex: http://... ou https://...)'))], render_kw={'placeholder': 'https://...'})
    reward_amount = DecimalField(_l('Montant de la récompense (en $)'), validators=[DataRequired(_l('La récompense est requise.')),NumberRange(min=0, message=_l('La récompense ne peut pas être négative.'))], places=2)
    target_countries = SelectMultipleField(_l('Pays Cibles'), choices=countries_choices_multi, widget=widgets.ListWidget(prefix_label=False), option_widget=widgets.CheckboxInput(), coerce=str)
    target_devices = SelectMultipleField(_l('Appareils Cibles'), choices=devices_choices_multi, widget=widgets.ListWidget(prefix_label=False), option_widget=widgets.CheckboxInput(), coerce=str)
    is_active = BooleanField(_l('Activer cette tâche maintenant ?'), default='checked')
    submit = SubmitField(_l('Enregistrer la Tâche'))

# --- Formulaire pour Modifier le Profil ---
class EditProfileForm(FlaskForm):
    full_name = StringField(_l('Nom complet'), validators=[DataRequired(_l('Le nom complet est requis.'))])
    email = StringField(_l('Adresse Email'), validators=[DataRequired(_l('L\'adresse email est requise.')), Email(_l('Adresse email invalide.'))])
    phone_number = StringField(_l('Numéro de téléphone (Optionnel)'))
    country = SelectField(_l('Pays'), choices=countries_choices_single, validators=[DataRequired(_l('Veuillez sélectionner votre pays.'))])
    device = SelectField(_l('Appareil Principal'), choices=devices_choices_single, validators=[DataRequired(_l('Veuillez sélectionner votre appareil.'))])
    submit_profile = SubmitField(_l('Enregistrer les Modifications du Profil')) # Nom différent pour le bouton submit

    def __init__(self, original_email, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, email):
        if email.data != self.original_email:
            user = db.session.scalar(db.select(User).where(User.email == email.data))
            if user is not None:
                raise ValidationError(_l('Cette adresse email est déjà utilisée par un autre compte.'))

# --- Formulaire pour Changer le Mot de Passe ---
class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(_l('Mot de Passe Actuel'), validators=[DataRequired(_l('Requis'))])
    new_password = PasswordField(_l('Nouveau Mot de Passe'), validators=[DataRequired(_l('Requis')), Length(min=8, message=_l('Doit contenir au moins 8 caractères.'))])
    new_password2 = PasswordField(_l('Confirmer Nouveau Mot de Passe'), validators=[DataRequired(_l('Requis')), EqualTo('new_password', message=_l('Les mots de passe doivent correspondre.'))])
    submit_password = SubmitField(_l('Changer le Mot de Passe')) # Nom différent pour le bouton submit

    def validate_current_password(self, current_password):
        if not current_user.check_password(current_password.data):
            raise ValidationError(_l('Mot de passe actuel incorrect.'))

# --- Formulaire pour l'Admin pour Réinitialiser le MDP d'un Utilisateur ---
class AdminResetPasswordForm(FlaskForm):
    new_password = PasswordField(_l('Nouveau Mot de Passe Temporaire'), validators=[
        DataRequired(_l('Requis')),
        Length(min=8, message=_l('Doit contenir au moins 8 caractères.'))
    ])
    confirm_password = PasswordField(
        _l('Confirmer le Nouveau Mot de Passe'), validators=[
            DataRequired(_l('Requis')),
            EqualTo('new_password', message=_l('Les mots de passe doivent correspondre.'))
    ])
    submit_reset = SubmitField(_l('Réinitialiser le Mot de Passe')) # Nom différent pour le bouton submit

# --- Formulaire pour Ajouter un Nouvel Admin (par Super Admin) ---
class AddAdminForm(FlaskForm):
    email = StringField(_l('Email de l\'utilisateur à promouvoir Admin'), validators=[
        DataRequired(_l('L\'adresse email est requise.')),
        Email(_l('Adresse email invalide.'))
    ])
    # Option pour créer directement un Super Admin
    is_super = BooleanField(_l('Promouvoir Super Administrateur ?'))
    submit_add = SubmitField(_l('Ajouter/Promouvoir Admin'))

    # Valide si l'email correspond à un utilisateur existant et non-admin
    def validate_email(self, email):
        user = db.session.scalar(db.select(User).where(User.email == email.data))
        if user is None:
            raise ValidationError(_l('Aucun utilisateur trouvé avec cette adresse email.'))
        if user.is_admin:
            raise ValidationError(_l('Cet utilisateur est déjà un administrateur.'))