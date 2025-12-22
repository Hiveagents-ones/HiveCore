from app.db.session import engine
from app.models.member import Base

def init_db() -> None:
    """
    Initialize the database by creating all tables.
    """
    # Import all models here to ensure they are registered with Base.metadata
    # Currently, only the Member model is defined.
    # If more models are added, they should be imported here.
    # Example:
    # from app.models.booking import Booking
    # from app.models.payment import Payment

    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    # This allows the script to be run directly to initialize the DB.
    print("Initializing database...")
    init_db()
    print("Database initialized successfully.")
