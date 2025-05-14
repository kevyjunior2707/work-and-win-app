# migrations/versions/NOUVEL_ID_POUR_ADMIN_set_initial_super_admin_pp364598.py
"""Set initial super admin pp364598

Revision ID: cf4f51782f42  # <<< REMPLACEZ PAR L'ID DE CE NOUVEAU FICHIER
Revises: 8753f09510d5           # <<< ID de la migration 'Rebuild initial schema'
Create Date: # Date de création
"""
from alembic import op
import sqlalchemy as sa
# Import pour l'update direct
from sqlalchemy.sql import table, column
from sqlalchemy import Boolean, String


# revision identifiers, used by Alembic.
revision = 'cf4f51782f42'  # <<< REMPLACEZ PAR L'ID DE CE NOUVEAU FICHIER
down_revision = '8753f09510d5'      # Pointeur vers la migration initiale reconstruite
branch_labels = None
depends_on = None


def upgrade():
    user_table = table('user',
        column('email', String),
        column('is_admin', Boolean),
        column('is_super_admin', Boolean)
    )

    op.execute(
        user_table.update().
        where(user_table.c.email == op.inline_literal('pp364598@gmail.com')).
        values(is_admin=op.inline_literal(True), is_super_admin=op.inline_literal(True))
    )
    print("INFO: Attempted to set pp364598@gmail.com as super admin.")


def downgrade():
    user_table = table('user',
        column('email', String),
        column('is_admin', Boolean),
        column('is_super_admin', Boolean)
    )
    op.execute(
        user_table.update().
        where(user_table.c.email == op.inline_literal('pp364598@gmail.com')).
        values(is_admin=op.inline_literal(False), is_super_admin=op.inline_literal(False))
    )
    print("INFO: Attempted to remove super admin rights from pp364598@gmail.com during downgrade.")