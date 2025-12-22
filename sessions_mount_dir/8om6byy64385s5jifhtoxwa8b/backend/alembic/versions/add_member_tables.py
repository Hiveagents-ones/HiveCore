"""add member tables

Revision ID: add_member_tables
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = 'add_member_tables'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create members table
    op.create_table(
        'members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=True),
        sa.Column('member_card_number', sa.String(length=50), nullable=False),
        sa.Column('member_level', sa.String(length=20), nullable=False),
        sa.Column('remaining_sessions', sa.Integer(), nullable=True),
        sa.Column('expiry_date', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=func.now(), nullable=True),
        sa.Column('encrypted_data', sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('member_card_number')
    )
    
    # Create indexes
    op.create_index('ix_members_id', 'members', ['id'], unique=False)
    op.create_index('ix_members_phone', 'members', ['phone'], unique=False)
    op.create_index('ix_members_email', 'members', ['email'], unique=False)
    op.create_index('ix_members_member_card_number', 'members', ['member_card_number'], unique=False)
    op.create_index('idx_member_level_active', 'members', ['member_level', 'is_active'], unique=False)
    op.create_index('idx_phone_active', 'members', ['phone', 'is_active'], unique=False)
    op.create_index('idx_card_number_level', 'members', ['member_card_number', 'member_level'], unique=False)

def downgrade():
    # Drop indexes
    op.drop_index('idx_card_number_level', table_name='members')
    op.drop_index('idx_phone_active', table_name='members')
    op.drop_index('idx_member_level_active', table_name='members')
    op.drop_index('ix_members_member_card_number', table_name='members')
    op.drop_index('ix_members_email', table_name='members')
    op.drop_index('ix_members_phone', table_name='members')
    op.drop_index('ix_members_id', table_name='members')
    
    # Drop table
    op.drop_table('members')
