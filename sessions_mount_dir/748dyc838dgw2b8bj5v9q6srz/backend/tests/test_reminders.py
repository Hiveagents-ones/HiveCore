import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import Session
from app.services.reminder_service import ReminderService
from app.models.member import Member
from app.models.payment import Payment


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def reminder_service(mock_db):
    """Create a ReminderService instance with mocked dependencies."""
    return ReminderService(db=mock_db)


@pytest.fixture
def sample_member():
    """Create a sample member for testing."""
    return Member(
        id=1,
        email="test@example.com",
        membership_end=datetime.utcnow() + timedelta(days=15),
        is_active=True
    )


@pytest.mark.asyncio
async def test_check_membership_expiry_success(reminder_service, mock_db, sample_member):
    """Test successful membership expiry check and reminder sending."""
    # Mock database query
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = [sample_member]

    # Mock Redis and email sending
    with patch('app.services.reminder_service.redis_client') as mock_redis, \
         patch('app.services.reminder_service.send_email') as mock_email:
        
        mock_redis.get.return_value = None  # Reminder not sent yet
        mock_email.return_value = None

        await reminder_service.check_membership_expiry()

        # Verify database query was called with correct filters
        mock_db.query.assert_called_once_with(Member)
        mock_query.filter.assert_called()
        
        # Verify Redis check
        mock_redis.get.assert_called_once()
        
        # Verify email was sent
        mock_email.assert_called_once()
        
        # Verify Redis setex was called to mark reminder as sent
        mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_check_membership_expiry_already_sent(reminder_service, mock_db, sample_member):
    """Test that reminders are not sent if already sent (cached in Redis)."""
    # Mock database query
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = [sample_member]

    # Mock Redis to indicate reminder already sent
    with patch('app.services.reminder_service.redis_client') as mock_redis, \
         patch('app.services.reminder_service.send_email') as mock_email:
        
        mock_redis.get.return_value = "sent"  # Reminder already sent

        await reminder_service.check_membership_expiry()

        # Verify email was not sent
        mock_email.assert_not_called()
        
        # Verify Redis setex was not called
        mock_redis.setex.assert_not_called()


@pytest.mark.asyncio
async def test_check_membership_expiry_retry_mechanism(reminder_service, mock_db, sample_member):
    """Test retry mechanism when sending reminder fails."""
    # Mock database query
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = [sample_member]

    # Mock Redis and email sending with failure
    with patch('app.services.reminder_service.redis_client') as mock_redis, \
         patch('app.services.reminder_service.send_email') as mock_email, \
         patch('asyncio.sleep') as mock_sleep:
        
        mock_redis.get.return_value = None
        mock_email.side_effect = [Exception("SMTP error"), None]  # Fail first, succeed second

        await reminder_service.check_membership_expiry()

        # Verify retry attempt
        assert mock_email.call_count == 2
        mock_sleep.assert_called_once_with(5)  # retry_delay
        
        # Verify Redis setex was called after success
        mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_check_membership_expiry_max_retries(reminder_service, mock_db, sample_member):
    """Test that max retries are respected and error is logged."""
    # Mock database query
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = [sample_member]

    # Mock Redis and email sending with persistent failure
    with patch('app.services.reminder_service.redis_client') as mock_redis, \
         patch('app.services.reminder_service.send_email') as mock_email, \
         patch('asyncio.sleep') as mock_sleep, \
         patch('app.services.reminder_service.logger') as mock_logger:
        
        mock_redis.get.return_value = None
        mock_email.side_effect = Exception("Persistent SMTP error")

        await reminder_service.check_membership_expiry()

        # Verify max retries attempted
        assert mock_email.call_count == 3  # retry_limit
        assert mock_sleep.call_count == 2  # retry_limit - 1
        
        # Verify error was logged
        mock_logger.error.assert_called()
        
        # Verify Redis setex was not called after failure
        mock_redis.setex.assert_not_called()


@pytest.mark.asyncio
async def test_check_membership_expiry_database_error(reminder_service, mock_db):
    """Test handling of database errors."""
    # Mock database query to raise SQLAlchemyError
    mock_db.query.side_effect = Exception("Database connection failed")

    with patch('app.services.reminder_service.logger') as mock_logger:
        with pytest.raises(Exception):
            await reminder_service.check_membership_expiry()
        
        # Verify error was logged
        mock_logger.error.assert_called()


@pytest.mark.asyncio
async def test_check_membership_expiry_no_expiring_members(reminder_service, mock_db):
    """Test behavior when no members have expiring memberships."""
    # Mock database query to return empty list
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = []

    with patch('app.services.reminder_service.redis_client') as mock_redis, \
         patch('app.services.reminder_service.send_email') as mock_email:
        
        await reminder_service.check_membership_expiry()

        # Verify no reminders were sent
        mock_email.assert_not_called()
        mock_redis.get.assert_not_called()
        mock_redis.setex.assert_not_called()


@pytest.mark.asyncio
async def test_send_reminder_with_retry_inactive_member(reminder_service, mock_db):
    """Test that inactive members are not processed."""
    # Create inactive member
    inactive_member = Member(
        id=2,
        email="inactive@example.com",
        membership_end=datetime.utcnow() + timedelta(days=15),
        is_active=False
    )

    # Mock database query to return only inactive member
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = [inactive_member]

    with patch('app.services.reminder_service.redis_client') as mock_redis, \
         patch('app.services.reminder_service.send_email') as mock_email:
        
        await reminder_service.check_membership_expiry()

        # Verify no reminders were sent for inactive member
        mock_email.assert_not_called()
        mock_redis.get.assert_not_called()
        mock_redis.setex.assert_not_called()
