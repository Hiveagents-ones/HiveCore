"""Create payment tables

Revision ID: xxxx
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'xxxx'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create payment_status enum
    payment_status = postgresql.ENUM(
        'pending', 'processing', 'completed', 'failed', 'refunded', 'cancelled', 'partially_refunded',
        name='paymentstatus'
    )
    payment_status.create(op.get_bind())
    
    # Create payment_method enum
    payment_method = postgresql.ENUM(
        'credit_card', 'debit_card', 'paypal', 'bank_transfer', 'alipay', 'wechat_pay', 'apple_pay', 'google_pay', 'crypto',
        name='paymentmethod'
    )
    payment_method.create(op.get_bind())
    
    # Create payment_orders table
    op.create_table(
        'payment_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('membership_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('status', payment_status, nullable=False, server_default='pending'),
        sa.Column('payment_method', payment_method, nullable=False),
        sa.Column('transaction_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.Column('is_recurring', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('next_billing_date', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['membership_id'], ['memberships.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_id')
    )
    
    # Create payment_transactions table
    op.create_table(
        'payment_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('gateway_transaction_id', sa.String(length=255), nullable=False),
        sa.Column('gateway', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('status', payment_status, nullable=False, server_default='pending'),
        sa.Column('gateway_response', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('refund_reason_code', sa.String(length=50), nullable=True),
        sa.Column('partial_refund_available', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['payment_order_id'], ['payment_orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create refunds table
    op.create_table(
        'refunds',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('status', payment_status, nullable=False, server_default='pending'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('gateway_refund_id', sa.String(length=255), nullable=True),
        sa.Column('gateway_response', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['payment_order_id'], ['payment_orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_payment_orders_user_id'), 'payment_orders', ['user_id'], unique=False)
    op.create_index(op.f('ix_payment_orders_membership_id'), 'payment_orders', ['membership_id'], unique=False)
    op.create_index(op.f('ix_payment_orders_status'), 'payment_orders', ['status'], unique=False)
    op.create_index(op.f('ix_payment_transactions_payment_order_id'), 'payment_transactions', ['payment_order_id'], unique=False)
    op.create_index(op.f('ix_refunds_payment_order_id'), 'refunds', ['payment_order_id'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_refunds_payment_order_id'), table_name='refunds')
    op.drop_index(op.f('ix_payment_transactions_payment_order_id'), table_name='payment_transactions')
    op.drop_index(op.f('ix_payment_orders_status'), table_name='payment_orders')
    op.drop_index(op.f('ix_payment_orders_membership_id'), table_name='payment_orders')
    op.drop_index(op.f('ix_payment_orders_user_id'), table_name='payment_orders')
    
    # Drop tables
    op.drop_table('refunds')
    op.drop_table('payment_transactions')
    op.drop_table('payment_orders')
    
    # Drop enums
    sa.Enum(name='paymentmethod').drop(op.get_bind())
    sa.Enum(name='paymentstatus').drop(op.get_bind())
