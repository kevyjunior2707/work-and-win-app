# app/models.py (VERSION COMPLÈTE v23 - Ajout Modèle SiteSetting)

import secrets
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy.orm import relationship
from sqlalchemy import select, ForeignKey
from app import db, login # Assurez-vous que db et login sont bien initialisés dans app/__init__.py
from flask import current_app # Pour SECRET_KEY dans les tokens
from itsdangerous import URLSafeTimedSerializer as Serializer
from itsdangerous import SignatureExpired, BadSignature
import re
import random
import string

# --- Fonction pour générer un slug de base ---
def slugify_base(text):
    if text is None:
        return ""
    # Remplace les caractères non alphanumériques par des tirets
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[-\s]+', '-', text)
    return text

# --- Modèle Utilisateur ---
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), index=True)
    email = db.Column(db.String(120), index=True, unique=True)
    phone_number = db.Column(db.String(30), nullable=True)
    country = db.Column(db.String(100))
    device = db.Column(db.String(50))
    password_hash = db.Column(db.String(256))
    registration_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    balance = db.Column(db.Float, default=0.0)
    referral_code = db.Column(db.String(16), unique=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_super_admin = db.Column(db.Boolean, default=False, nullable=False)
    last_withdrawal_date = db.Column(db.DateTime, nullable=True)
    is_banned = db.Column(db.Boolean, default=False, nullable=False)
    referred_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    completed_task_count = db.Column(db.Integer, default=0, nullable=False)
    telegram_username = db.Column(db.String(100), nullable=True, index=True)
    is_verified = db.Column(db.Boolean, default=False, nullable=False, index=True)

    # Relations
    referrer = relationship('User', remote_side=[id], back_populates='referred_users')
    referred_users = relationship('User', back_populates='referrer', foreign_keys=[referred_by_id])
    completed_tasks_rel = relationship('UserTaskCompletion', back_populates='user', lazy='dynamic', foreign_keys='UserTaskCompletion.user_id')
    referred_completions = relationship('ExternalTaskCompletion', back_populates='referrer_user', lazy='dynamic', foreign_keys='ExternalTaskCompletion.referrer_user_id')
    withdrawals = relationship('Withdrawal', back_populates='requester', lazy='dynamic', foreign_keys='Withdrawal.user_id')
    notifications = relationship('Notification', back_populates='user', lazy='dynamic', foreign_keys='Notification.user_id')
    processed_withdrawals = relationship('Withdrawal', back_populates='processed_by_admin', lazy='dynamic', foreign_keys='Withdrawal.processed_by_admin_id')
    processed_external_completions = relationship('ExternalTaskCompletion', back_populates='processed_by_ext_admin', lazy='dynamic', foreign_keys='ExternalTaskCompletion.processed_by_admin_id')
    processed_commissions = relationship('ReferralCommission', back_populates='processed_by_admin', lazy='dynamic', foreign_keys='ReferralCommission.processed_by_admin_id')
    commissions_earned = relationship('ReferralCommission', back_populates='referrer', lazy='dynamic', foreign_keys='ReferralCommission.referrer_id')
    commissions_generated = relationship('ReferralCommission', back_populates='referred_user', lazy='dynamic', foreign_keys='ReferralCommission.referred_user_id')
    posts = relationship('Post', back_populates='author', lazy='dynamic', foreign_keys='Post.user_id')
    comments = relationship('Comment', back_populates='author', lazy='dynamic', foreign_keys='Comment.user_id')

    def __init__(self, **kwargs): super().__init__(**kwargs); self._generate_referral_code()
    def _generate_referral_code(self):
        if not self.referral_code: self.referral_code = secrets.token_hex(8)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password) if self.password_hash else False
    def get_verification_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})
    @staticmethod
    def verify_verification_token(token, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        try: data = s.loads(token, max_age=expires_sec); user_id = data.get('user_id')
        except (SignatureExpired, BadSignature, Exception): return None
        return db.session.get(User, user_id)
    def __repr__(self): return f'<User {self.full_name} ({self.email})>'

@login.user_loader
def load_user(id): return db.session.get(User, int(id))

class Task(db.Model):
    __tablename__ = 'task'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=True)
    task_link = db.Column(db.String(500), nullable=True)
    reward_amount = db.Column(db.Float, nullable=False, default=0.0)
    target_countries = db.Column(db.Text, nullable=True)
    target_devices = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    creation_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    image_filename = db.Column(db.String(256), nullable=True)
    is_daily = db.Column(db.Boolean, default=False, nullable=False)
    completions = db.relationship('UserTaskCompletion', back_populates='task', lazy='dynamic', foreign_keys='UserTaskCompletion.task_id')
    external_completions = db.relationship('ExternalTaskCompletion', back_populates='task', lazy='dynamic', foreign_keys='ExternalTaskCompletion.task_id')
    def get_target_countries_list(self): return ['ALL'] if not self.target_countries or self.target_countries.upper() == 'ALL' else [c.strip().upper() for c in self.target_countries.split(',')]
    def get_target_devices_list(self): return ['ALL'] if not self.target_devices or self.target_devices.upper() == 'ALL' else [d.strip().capitalize() for d in self.target_devices.split(',')]
    def __repr__(self): return f'<Task {self.id}: {self.title}>'

class UserTaskCompletion(db.Model):
    __tablename__ = 'user_task_completion'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'))
    completion_timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user = relationship('User', back_populates='completed_tasks_rel', foreign_keys=[user_id])
    task = relationship('Task', back_populates='completions', foreign_keys=[task_id])
    referral_commission_generated = relationship('ReferralCommission', back_populates='originating_completion', uselist=False, foreign_keys='ReferralCommission.originating_completion_id')
    def __repr__(self): return f'<User {self.user_id} completed Task {self.task_id}>'

class ExternalTaskCompletion(db.Model):
    __tablename__ = 'external_task_completion'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'))
    referrer_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    submitter_identifier = db.Column(db.String(120), nullable=True)
    submitted_proof = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Pending')
    submission_timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    processed_timestamp = db.Column(db.DateTime, nullable=True)
    processed_by_admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    screenshot_filename = db.Column(db.String(256), nullable=True)
    task = relationship('Task', back_populates='external_completions', foreign_keys=[task_id])
    referrer_user = relationship('User', back_populates='referred_completions', foreign_keys=[referrer_user_id])
    processed_by_ext_admin = relationship('User', back_populates='processed_external_completions', foreign_keys=[processed_by_admin_id])
    def __repr__(self): return f'<External Completion Task {self.task_id} via Referrer {self.referrer_user_id} - Status: {self.status}>'

class Withdrawal(db.Model):
    __tablename__ = 'withdrawal'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Float, nullable=False)
    request_timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    processed_timestamp = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='Pending')
    processed_by_admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    requester = relationship('User', back_populates='withdrawals', foreign_keys=[user_id])
    processed_by_admin = relationship('User', back_populates='processed_withdrawals', foreign_keys=[processed_by_admin_id])
    def __repr__(self): return f'<Withdrawal {self.id} - User {self.user_id} - Amount {self.amount} - Status: {self.status}>'

class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(128), index=True)
    payload_json = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    is_read = db.Column(db.Boolean, default=False)
    user = relationship('User', back_populates='notifications', foreign_keys=[user_id])
    def __repr__(self): return f'<Notification {self.name} for User {self.user_id}>'

class ReferralCommission(db.Model):
    __tablename__ = 'referral_commission'
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    referred_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    originating_completion_id = db.Column(db.Integer, db.ForeignKey('user_task_completion.id'), nullable=False, unique=True)
    commission_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Pending', nullable=False, index=True)
    creation_timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    processed_timestamp = db.Column(db.DateTime, nullable=True)
    processed_by_admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    referrer = relationship('User', back_populates='commissions_earned', foreign_keys=[referrer_id])
    referred_user = relationship('User', back_populates='commissions_generated', foreign_keys=[referred_user_id])
    originating_completion = relationship('UserTaskCompletion', back_populates='referral_commission_generated', foreign_keys=[originating_completion_id])
    processed_by_admin = relationship('User', back_populates='processed_commissions', foreign_keys=[processed_by_admin_id])
    def __repr__(self): return f'<ReferralCommission {self.id} - Referrer {self.referrer_id} from User {self.referred_user_id} - Amount {self.commission_amount} - Status {self.status}>'

class Banner(db.Model):
    __tablename__ = 'banner'
    id = db.Column(db.Integer, primary_key=True)
    image_filename = db.Column(db.String(256), nullable=False)
    destination_url = db.Column(db.String(500), nullable=True)
    display_location = db.Column(db.String(50), nullable=False, default='top_bottom')
    is_active = db.Column(db.Boolean, default=False, nullable=False, index=True)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    clicks = db.Column(db.Integer, default=0)
    def __repr__(self): return f'<Banner {self.id} - {self.image_filename} - Active: {self.is_active}>'

class Post(db.Model):
    __tablename__ = 'post'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    slug = db.Column(db.String(250), nullable=False, unique=True, index=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_filename = db.Column(db.String(256), nullable=True)
    allow_comments = db.Column(db.Boolean, default=True, nullable=False)
    is_published = db.Column(db.Boolean, default=False, nullable=False, index=True)
    author = relationship('User', back_populates='posts')
    comments = relationship('Comment', back_populates='post', lazy='dynamic', cascade="all, delete-orphan")

    @staticmethod
    def generate_unique_slug(title, post_id=None):
        base_slug = slugify_base(title)
        slug_candidate = base_slug
        while True:
            query = db.session.query(Post.id).filter(Post.slug == slug_candidate)
            if post_id: query = query.filter(Post.id != post_id)
            if not db.session.execute(query).first(): return slug_candidate
            suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
            slug_candidate = f"{base_slug}-{suffix}"
    def __repr__(self): return f'<Post {self.title}>'

class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    is_approved = db.Column(db.Boolean, default=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    parent = relationship('Comment', remote_side=[id], back_populates='replies')
    replies = relationship('Comment', back_populates='parent', lazy='dynamic', cascade="all, delete-orphan")
    author = relationship('User', back_populates='comments')
    post = relationship('Post', back_populates='comments')
    def __repr__(self): return f'<Comment {self.id} by User {self.user_id} on Post {self.post_id}>'

# <<< NOUVEAU MODÈLE SiteSetting >>>
class SiteSetting(db.Model):
    __tablename__ = 'site_setting'
    # Utilise un ID simple, on s'assurera qu'il n'y a qu'une seule ligne via la logique des routes
    id = db.Column(db.Integer, primary_key=True, default=1)
    custom_head_scripts = db.Column(db.Text, nullable=True)
    custom_footer_scripts = db.Column(db.Text, nullable=True)
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<SiteSetting {self.id}>'
# <<< FIN NOUVEAU MODÈLE SiteSetting >>>

