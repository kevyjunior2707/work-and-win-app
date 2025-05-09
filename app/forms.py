# app/forms.py (VERSION COMPLÈTE v13 - Ajout BannerForm)
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SubmitField, SelectField,
                     BooleanField, TextAreaField, DecimalField, SelectMultipleField,
                     ValidationError, URLField) # URLField ajouté
from wtforms import widgets
from wtforms.validators import (DataRequired, Email, EqualTo, Length, ValidationError,
                              NumberRange, Optional, URL, Regexp)
from flask_wtf.file import FileField, FileAllowed
from app.models import User # User est déjà importé
from app import db
from flask_babel import lazy_gettext as _l
from flask_login import current_user

# --- Listes de Choix (Pays/Appareils/Indicatifs) ---
try:
    import pycountry
    countries_raw = sorted([(c.alpha_2, c.name) for c in pycountry.countries], key=lambda x: x[1])
    countries_choices_multi = [('ALL', _l('Tous les pays'))] + countries_raw
    countries_choices_single = [('', _l('--- Sélectionnez votre pays ---'))] + countries_raw
except Exception as e:
    print(f"ERREUR: pycountry: {e}. Utilisation liste réduite."); countries_choices_multi = [('ALL', _l('Tous les pays')), ('BJ', 'Bénin'), ('FR', 'France')]; countries_choices_single = [('', _l('--- Sélectionnez votre pays ---')), ('BJ', 'Bénin'), ('FR', 'France')]

country_codes = [ ('', _l('-- Indicatif --')), ('+93', 'Afghanistan (+93)'), ('+355', 'Albanie (+355)'), ('+213', 'Algérie (+213)'), ('+1684', 'Samoa américaines (+1684)'), ('+376', 'Andorre (+376)'), ('+244', 'Angola (+244)'), ('+1264', 'Anguilla (+1264)'), ('+1268', 'Antigua-et-Barbuda (+1268)'), ('+54', 'Argentine (+54)'), ('+374', 'Arménie (+374)'), ('+297', 'Aruba (+297)'), ('+61', 'Australie (+61)'), ('+43', 'Autriche (+43)'), ('+994', 'Azerbaïdjan (+994)'), ('+1242', 'Bahamas (+1242)'), ('+973', 'Bahreïn (+973)'), ('+880', 'Bangladesh (+880)'), ('+1246', 'Barbade (+1246)'), ('+375', 'Biélorussie (+375)'), ('+32', 'Belgique (+32)'), ('+501', 'Belize (+501)'), ('+229', 'Bénin (+229)'), ('+1441', 'Bermudes (+1441)'), ('+975', 'Bhoutan (+975)'), ('+591', 'Bolivie (+591)'), ('+387', 'Bosnie-Herzégovine (+387)'), ('+267', 'Botswana (+267)'), ('+55', 'Brésil (+55)'), ('+246', 'Territoire britannique de l\'océan Indien (+246)'), ('+1284', 'Îles Vierges britanniques (+1284)'), ('+673', 'Brunéi Darussalam (+673)'), ('+359', 'Bulgarie (+359)'), ('+226', 'Burkina Faso (+226)'), ('+257', 'Burundi (+257)'), ('+855', 'Cambodge (+855)'), ('+237', 'Cameroun (+237)'), ('+1', 'Canada (+1)'), ('+238', 'Cap-Vert (+238)'), ('+1345', 'Îles Caïmans (+1345)'), ('+236', 'République centrafricaine (+236)'), ('+235', 'Tchad (+235)'), ('+56', 'Chili (+56)'), ('+86', 'Chine (+86)'), ('+61', 'Île Christmas (+61)'), ('+61', 'Îles Cocos (Keeling) (+61)'), ('+57', 'Colombie (+57)'), ('+269', 'Comores (+269)'), ('+243', 'Congo (RDC) (+243)'), ('+242', 'Congo (République) (+242)'), ('+682', 'Îles Cook (+682)'), ('+506', 'Costa Rica (+506)'), ('+225', 'Côte d\'Ivoire (+225)'), ('+385', 'Croatie (+385)'), ('+53', 'Cuba (+53)'), ('+599', 'Curaçao (+599)'), ('+357', 'Chypre (+357)'), ('+420', 'République tchèque (+420)'), ('+45', 'Danemark (+45)'), ('+253', 'Djibouti (+253)'), ('+1767', 'Dominique (+1767)'), ('+1809', 'République dominicaine (+1809)'), ('+593', 'Équateur (+593)'), ('+20', 'Égypte (+20)'), ('+503', 'El Salvador (+503)'), ('+240', 'Guinée équatoriale (+240)'), ('+291', 'Érythrée (+291)'), ('+372', 'Estonie (+372)'), ('+268', 'Eswatini (+268)'), ('+251', 'Éthiopie (+251)'), ('+500', 'Îles Malouines (+500)'), ('+298', 'Îles Féroé (+298)'), ('+679', 'Fidji (+679)'), ('+358', 'Finlande (+358)'), ('+33', 'France (+33)'), ('+594', 'Guyane française (+594)'), ('+689', 'Polynésie française (+689)'), ('+241', 'Gabon (+241)'), ('+220', 'Gambie (+220)'), ('+995', 'Géorgie (+995)'), ('+49', 'Allemagne (+49)'), ('+233', 'Ghana (+233)'), ('+350', 'Gibraltar (+350)'), ('+30', 'Grèce (+30)'), ('+299', 'Groenland (+299)'), ('+1473', 'Grenade (+1473)'), ('+590', 'Guadeloupe (+590)'), ('+1671', 'Guam (+1671)'), ('+502', 'Guatemala (+502)'), ('+44', 'Guernesey (+44)'), ('+224', 'Guinée (+224)'), ('+245', 'Guinée-Bissau (+245)'), ('+592', 'Guyana (+592)'), ('+509', 'Haïti (+509)'), ('+504', 'Honduras (+504)'), ('+852', 'Hong Kong (+852)'), ('+36', 'Hongrie (+36)'), ('+354', 'Islande (+354)'), ('+91', 'Inde (+91)'), ('+62', 'Indonésie (+62)'), ('+98', 'Iran (+98)'), ('+964', 'Irak (+964)'), ('+353', 'Irlande (+353)'), ('+44', 'Île de Man (+44)'), ('+972', 'Israël (+972)'), ('+39', 'Italie (+39)'), ('+1876', 'Jamaïque (+1876)'), ('+81', 'Japon (+81)'), ('+44', 'Jersey (+44)'), ('+962', 'Jordanie (+962)'), ('+7', 'Kazakhstan (+7)'), ('+254', 'Kenya (+254)'), ('+686', 'Kiribati (+686)'), ('+850', 'Corée du Nord (+850)'), ('+82', 'Corée du Sud (+82)'), ('+383', 'Kosovo (+383)'), ('+965', 'Koweït (+965)'), ('+996', 'Kirghizistan (+996)'), ('+856', 'Laos (+856)'), ('+371', 'Lettonie (+371)'), ('+961', 'Liban (+961)'), ('+266', 'Lesotho (+266)'), ('+231', 'Libéria (+231)'), ('+218', 'Libye (+218)'), ('+423', 'Liechtenstein (+423)'), ('+370', 'Lituanie (+370)'), ('+352', 'Luxembourg (+352)'), ('+853', 'Macao (+853)'), ('+261', 'Madagascar (+261)'), ('+265', 'Malawi (+265)'), ('+60', 'Malaisie (+60)'), ('+960', 'Maldives (+960)'), ('+223', 'Mali (+223)'), ('+356', 'Malte (+356)'), ('+692', 'Îles Marshall (+692)'), ('+596', 'Martinique (+596)'), ('+222', 'Mauritanie (+222)'), ('+230', 'Maurice (+230)'), ('+262', 'Mayotte (+262)'), ('+52', 'Mexique (+52)'), ('+691', 'Micronésie (+691)'), ('+373', 'Moldavie (+373)'), ('+377', 'Monaco (+377)'), ('+976', 'Mongolie (+976)'), ('+382', 'Monténégro (+382)'), ('+1664', 'Montserrat (+1664)'), ('+212', 'Maroc (+212)'), ('+258', 'Mozambique (+258)'), ('+95', 'Myanmar (Birmanie) (+95)'), ('+264', 'Namibie (+264)'), ('+674', 'Nauru (+674)'), ('+977', 'Népal (+977)'), ('+31', 'Pays-Bas (+31)'), ('+687', 'Nouvelle-Calédonie (+687)'), ('+64', 'Nouvelle-Zélande (+64)'), ('+505', 'Nicaragua (+505)'), ('+227', 'Niger (+227)'), ('+234', 'Nigéria (+234)'), ('+683', 'Niue (+683)'), ('+672', 'Île Norfolk (+672)'), ('+389', 'Macédoine du Nord (+389)'), ('+1670', 'Îles Mariannes du Nord (+1670)'), ('+47', 'Norvège (+47)'), ('+968', 'Oman (+968)'), ('+92', 'Pakistan (+92)'), ('+680', 'Palaos (+680)'), ('+970', 'Palestine (+970)'), ('+507', 'Panama (+507)'), ('+675', 'Papouasie-Nouvelle-Guinée (+675)'), ('+595', 'Paraguay (+595)'), ('+51', 'Pérou (+51)'), ('+63', 'Philippines (+63)'), ('+48', 'Pologne (+48)'), ('+351', 'Portugal (+351)'), ('+1', 'Porto Rico (+1)'), ('+974', 'Qatar (+974)'), ('+262', 'Réunion (+262)'), ('+40', 'Roumanie (+40)'), ('+7', 'Russie (+7)'), ('+250', 'Rwanda (+250)'), ('+590', 'Saint-Barthélemy (+590)'), ('+290', 'Sainte-Hélène (+290)'), ('+1869', 'Saint-Kitts-et-Nevis (+1869)'), ('+1758', 'Sainte-Lucie (+1758)'), ('+590', 'Saint-Martin (+590)'), ('+508', 'Saint-Pierre-et-Miquelon (+508)'), ('+1784', 'Saint-Vincent-et-les Grenadines (+1784)'), ('+685', 'Samoa (+685)'), ('+378', 'Saint-Marin (+378)'), ('+239', 'Sao Tomé-et-Principe (+239)'), ('+966', 'Arabie Saoudite (+966)'), ('+221', 'Sénégal (+221)'), ('+381', 'Serbie (+381)'), ('+248', 'Seychelles (+248)'), ('+232', 'Sierra Leone (+232)'), ('+65', 'Singapour (+65)'), ('+1721', 'Sint Maarten (+1721)'), ('+421', 'Slovaquie (+421)'), ('+386', 'Slovénie (+386)'), ('+677', 'Îles Salomon (+677)'), ('+252', 'Somalie (+252)'), ('+27', 'Afrique du Sud (+27)'), ('+211', 'Soudan du Sud (+211)'), ('+34', 'Espagne (+34)'), ('+94', 'Sri Lanka (+94)'), ('+249', 'Soudan (+249)'), ('+597', 'Suriname (+597)'), ('+46', 'Suède (+46)'), ('+41', 'Suisse (+41)'), ('+963', 'Syrie (+963)'), ('+886', 'Taïwan (+886)'), ('+992', 'Tadjikistan (+992)'), ('+255', 'Tanzanie (+255)'), ('+66', 'Thaïlande (+66)'), ('+670', 'Timor oriental (+670)'), ('+228', 'Togo (+228)'), ('+690', 'Tokelau (+690)'), ('+676', 'Tonga (+676)'), ('+1868', 'Trinité-et-Tobago (+1868)'), ('+216', 'Tunisie (+216)'), ('+90', 'Turquie (+90)'), ('+993', 'Turkménistan (+993)'), ('+1649', 'Îles Turques-et-Caïques (+1649)'), ('+688', 'Tuvalu (+688)'), ('+1340', 'Îles Vierges américaines (+1340)'), ('+256', 'Ouganda (+256)'), ('+380', 'Ukraine (+380)'), ('+971', 'Émirats arabes unis (+971)'), ('+44', 'Royaume-Uni (+44)'), ('+598', 'Uruguay (+598)'), ('+998', 'Ouzbékistan (+998)'), ('+678', 'Vanuatu (+678)'), ('+379', 'Vatican (+379)'), ('+58', 'Venezuela (+58)'), ('+84', 'Viêt Nam (+84)'), ('+681', 'Wallis-et-Futuna (+681)'), ('+212', 'Sahara occidental (+212)'), ('+967', 'Yémen (+967)'), ('+260', 'Zambie (+260)'), ('+263', 'Zimbabwe (+263)')
]
devices_choices_single = [('', _l('--- Sélectionnez votre appareil ---')), ('Android', 'Android'), ('iOS', 'iPhone (iOS)'), ('PC', 'PC (Windows/Mac/Linux)')]
devices_choices_multi = [('ALL', _l('Tous les appareils')), ('Android', 'Android'), ('iOS', 'iOS'), ('PC', 'PC')]

# --- Formulaire d'Inscription ---
class RegistrationForm(FlaskForm):
    full_name = StringField(_l('Nom complet'), validators=[DataRequired(_l('Le nom complet est requis.'))])
    email = StringField(_l('Adresse Email'), validators=[DataRequired(_l('L\'adresse email est requise.')), Email(_l('Adresse email invalide.'))])
    phone_code = SelectField(_l('Indicatif Pays'), choices=country_codes, validators=[DataRequired(_l('Indicatif requis'))])
    phone_local_number = StringField(_l('Numéro de téléphone (sans indicatif)'), validators=[DataRequired(_l('Numéro requis')), Regexp(r'^\d+$', message=_l('Entrez uniquement des chiffres.'))])
    telegram_username = StringField(_l('Nom d\'utilisateur Telegram (Optionnel, ex: @pseudo)'))
    country = SelectField(_l('Pays de Résidence'), choices=countries_choices_single, validators=[DataRequired(_l('Veuillez sélectionner votre pays.'))])
    device = SelectField(_l('Appareil Principal'), choices=devices_choices_single, validators=[DataRequired(_l('Veuillez sélectionner votre appareil.'))])
    password = PasswordField(_l('Mot de passe'), validators=[DataRequired(_l('Le mot de passe est requis.')),Length(min=8, message=_l('Le mot de passe doit contenir au moins 8 caractères.'))])
    password2 = PasswordField(_l('Confirmer le mot de passe'), validators=[DataRequired(_l('Veuillez confirmer le mot de passe.')), EqualTo('password', message=_l('Les mots de passe doivent correspondre.'))])
    submit = SubmitField(_l('S\'inscrire'))

    def validate_email(self, email):
        if email.data:
            email_lower = email.data.lower()
            user = db.session.scalar(db.select(User).where(User.email == email_lower))
            if user is not None: raise ValidationError(_l('Cette adresse email est déjà utilisée.'))

    def validate_telegram_username(self, telegram_username):
        if telegram_username.data and not telegram_username.data.startswith('@'):
            telegram_username.data = '@' + telegram_username.data

# --- Formulaire de Connexion ---
class LoginForm(FlaskForm):
    email = StringField(_l('Adresse Email'), validators=[DataRequired(_l("L'adresse email est requise.")), Email(_l('Adresse email invalide.'))])
    password = PasswordField(_l('Mot de passe'), validators=[DataRequired(_l('Le mot de passe est requis.'))])
    remember_me = BooleanField(_l('Se souvenir de moi'))
    submit = SubmitField(_l('Connexion'))

    def validate_email(self, email):
        if email.data: email.data = email.data.lower()

# --- Formulaire de Tâche ---
class TaskForm(FlaskForm):
    title = StringField(_l('Titre de la tâche'), validators=[DataRequired(_l('Le titre est requis.'))])
    description = TextAreaField(_l('Description détaillée'), validators=[DataRequired(_l('La description est requise.'))], render_kw={'rows': 5})
    instructions = TextAreaField(_l('Instructions spécifiques (Optionnel)'), render_kw={'rows': 3})
    task_link = StringField(_l('Lien de la Tâche (URL directe, optionnel)'), validators=[Optional(), URL(message=_l('Veuillez entrer une URL valide (ex: http://... ou https://...)'))], render_kw={'placeholder': 'https://...'})
    reward_amount = DecimalField(_l('Montant de la récompense (en $)'), validators=[DataRequired(_l('La récompense est requise.')),NumberRange(min=0, message=_l('La récompense ne peut pas être négative.'))], places=2)
    task_image = FileField(_l('Image Mise en Avant (Optionnel, JPG/PNG/JPEG/GIF)'), validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif'], _l('Seules les images sont autorisées!'))])
    target_countries = SelectMultipleField(_l('Pays Cibles'), choices=countries_choices_multi, widget=widgets.ListWidget(prefix_label=False), option_widget=widgets.CheckboxInput(), coerce=str)
    target_devices = SelectMultipleField(_l('Appareils Cibles'), choices=devices_choices_multi, widget=widgets.ListWidget(prefix_label=False), option_widget=widgets.CheckboxInput(), coerce=str)
    is_active = BooleanField(_l('Activer cette tâche maintenant ?'), default='checked')
    is_daily = BooleanField(_l('Tâche Quotidienne (Répétable chaque jour) ?'), default=False)
    submit = SubmitField(_l('Enregistrer la Tâche'))

# --- Formulaire pour Modifier le Profil ---
class EditProfileForm(FlaskForm):
    full_name = StringField(_l('Nom complet'), validators=[DataRequired(_l('Le nom complet est requis.'))])
    email = StringField(_l('Adresse Email'), validators=[DataRequired(_l('L\'adresse email est requise.')), Email(_l('Adresse email invalide.'))])
    phone_code = SelectField(_l('Indicatif Pays'), choices=country_codes, validators=[DataRequired(_l('Indicatif requis'))])
    phone_local_number = StringField(_l('Numéro de téléphone (sans indicatif)'), validators=[DataRequired(_l('Numéro requis')), Regexp(r'^\d+$', message=_l('Entrez uniquement des chiffres.'))])
    telegram_username = StringField(_l('Nom d\'utilisateur Telegram (Optionnel, ex: @pseudo)'))
    country = SelectField(_l('Pays de Résidence'), choices=countries_choices_single, validators=[DataRequired(_l('Veuillez sélectionner votre pays.'))])
    device = SelectField(_l('Appareil Principal'), choices=devices_choices_single, validators=[DataRequired(_l('Veuillez sélectionner votre appareil.'))])
    submit_profile = SubmitField(_l('Enregistrer les Modifications du Profil'))

    def __init__(self, original_email, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, email):
        if email.data:
            email_lower = email.data.lower()
            if email_lower != self.original_email.lower():
                user = db.session.scalar(db.select(User).where(User.email == email_lower))
                if user is not None: raise ValidationError(_l('Cette adresse email est déjà utilisée par un autre compte.'))
            email.data = email_lower

    def validate_telegram_username(self, telegram_username):
        if telegram_username.data and not telegram_username.data.startswith('@'):
            telegram_username.data = '@' + telegram_username.data

# --- Formulaire pour Changer le Mot de Passe ---
class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(_l('Mot de Passe Actuel'), validators=[DataRequired(_l('Requis'))])
    new_password = PasswordField(_l('Nouveau Mot de Passe'), validators=[DataRequired(_l('Requis')), Length(min=8, message=_l('Doit contenir au moins 8 caractères.'))])
    new_password2 = PasswordField(_l('Confirmer Nouveau Mot de Passe'), validators=[DataRequired(_l('Requis')), EqualTo('new_password', message=_l('Les mots de passe doivent correspondre.'))])
    submit_password = SubmitField(_l('Changer le Mot de Passe'))

    def validate_current_password(self, current_password):
        if not current_user.check_password(current_password.data):
            raise ValidationError(_l('Mot de passe actuel incorrect.'))

# --- Formulaire pour l'Admin pour Réinitialiser le MDP d'un Utilisateur ---
class AdminResetPasswordForm(FlaskForm):
    new_password = PasswordField(_l('Nouveau Mot de Passe Temporaire'), validators=[DataRequired(_l('Requis')), Length(min=8, message=_l('Doit contenir au moins 8 caractères.'))])
    confirm_password = PasswordField(_l('Confirmer le Nouveau Mot de Passe'), validators=[DataRequired(_l('Requis')), EqualTo('new_password', message=_l('Les mots de passe doivent correspondre.'))])
    submit_reset = SubmitField(_l('Réinitialiser le Mot de Passe'))

# --- Formulaire pour Ajouter un Nouvel Admin (par Super Admin) ---
class AddAdminForm(FlaskForm):
    email = StringField(_l('Email de l\'utilisateur à promouvoir Admin'), validators=[DataRequired(_l('L\'adresse email est requise.')), Email(_l('Adresse email invalide.'))])
    is_super = BooleanField(_l('Promouvoir Super Administrateur ?'))
    submit_add = SubmitField(_l('Ajouter/Promouvoir Admin'))

    def validate_email(self, email):
        if email.data:
            email_lower = email.data.lower()
            user = db.session.scalar(db.select(User).where(User.email == email_lower))
            if user is None: raise ValidationError(_l('Aucun utilisateur trouvé avec cette adresse email.'))
            if user.is_admin: raise ValidationError(_l('Cet utilisateur est déjà un administrateur.'))
            email.data = email_lower

# <<< NOUVEAU FORMULAIRE POUR LES BANNIÈRES >>>
class BannerForm(FlaskForm):
    banner_image = FileField(_l('Image de la Bannière (JPG/PNG/GIF)'), validators=[
        DataRequired(_l('Une image est requise pour la bannière.')),
        FileAllowed(['jpg', 'png', 'jpeg', 'gif'], _l('Seules les images (jpg, png, jpeg, gif) sont autorisées!'))
    ])
    destination_url = URLField(_l('URL de Destination (Optionnel, ex: https://...)'), validators=[Optional(), URL(message=_l('Veuillez entrer une URL valide.'))])
    display_location = SelectField(_l('Afficher la bannière:'), choices=[
        ('top_bottom', _l('En Haut et En Bas')),
        ('top', _l('En Haut Seulement')),
        ('bottom', _l('En Bas Seulement'))
    ], validators=[DataRequired()])
    is_active = BooleanField(_l('Activer cette bannière maintenant ?'), default=False)
    submit = SubmitField(_l('Enregistrer la Bannière'))