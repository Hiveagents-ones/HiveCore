"""Add indexes

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add indexes for payment history queries
    op.create_index('idx_payment_user_id', 'payment', ['user_id'])
    op.create_index('idx_payment_created_at', 'payment', ['created_at'])
    op.create_index('idx_payment_status', 'payment', ['status'])
    
    # Add indexes for membership expiration queries
    op.create_index('idx_membership_user_id', 'membership', ['user_id'])
    op.create_index('idx_membership_expires_at', 'membership', ['expires_at'])
    op.create_index('idx_membership_status', 'membership', ['status'])
    
    # Add composite index for payment history filtering
    op.create_index('idx_payment_user_status', 'payment', ['user_id', 'status'])
    
    # Add composite index for expiration reminders
    op.create_index('idx_membership_expires_status', 'membership', ['expires_at', 'status'])


def downgrade() -> None:
    # Drop composite indexes first
    op.drop_index('idx_membership_expires_status', 'membership')
    op.drop_index('idx_payment_user_status', 'payment')
    
    # Drop single column indexes
    op.drop_index('idx_membership_status', 'membership')
    op.drop_index('idx_membership_expires_at', 'membership')
    op.drop_index('idx_membership_user_id', 'membership')
    op.drop_index('idx_payment_status', 'payment')
    op.drop_index('idx_payment_created_at', 'payment')
    op.drop_index('idx_payment_user_id', 'payment')