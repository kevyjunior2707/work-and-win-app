# migrations/versions/123949fe00c3_set_initial_super_admin_account.py
"""Set initial super admin account

Revision ID: 123949fe00c3
Revises: 96ab9fccb07e # Pointeur vers la migration 'Rebuild initial schema'
Create Date: 2025-05-13 15:27:45.862327
"""
from alembic import op
import sqlalchemy as sa
# Import pour l'update direct
from sqlalchemy.sql import table, column
from sqlalchemy import Boolean, String


# revision identifiers, used by Alembic.
revision = '123949fe00c3'
down_revision = '96ab9fccb07e' # Doit pointer vers la migration initiale reconstruite
branch_labels = None
depends_on = None


def upgrade():
    # Crée une "table" temporaire pour l'opération de mise à jour
    user_table = table('user',
        column('email', String), # Nécessaire pour la clause where
        column('is_admin', Boolean),
        column('is_super_admin', Boolean)
    )

    # Met à jour l'utilisateur spécifique par email
    # Assurez-vous que l'email ici est EXACTEMENT celui que vous utiliserez pour vous inscrire.
    op.execute(
        user_table.update().
        where(user_table.c.email == op.inline_literal('pp364598@gmail.com')).
        values(is_admin=op.inline_literal(True), is_super_admin=op.inline_literal(True))
    )
    print("INFO: Attempted to set pp364598@gmail.com as super admin via migration 123949fe00c3.")


def downgrade():
    # Optionnel: On pourrait retirer les droits ici.
    user_table = table('user',
        column('email', String),
        column('is_admin', Boolean),
        column('is_super_admin', Boolean)
    )
    op.execute(
        user_table.update().
        where(user_table.c.email == op.inline_literal('pp364598@gmail.com')).
        values(is_admin=op.inline_literal(False), is_super_admin=op.inline_literal(False)) # Remet à False
    )
    print("INFO: Attempted to remove super admin rights from pp364598@gmail.com during downgrade of 123949fe00c3.")

