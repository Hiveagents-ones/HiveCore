import sys
import os
from sqlalchemy.orm import Session

# Add the parent directory to the path so we can import from the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine
from app.models.rbac import User, Role, Permission, role_permissions, user_roles, init_default_roles
from app.core.security import get_password_hash

def init_rbac():
    """
    Initialize RBAC roles and permissions data
    """
    # Create all tables
    from app.models.rbac import Base
    Base.metadata.create_all(bind=engine)
    
    # Create a new session
    db = SessionLocal()
    
    try:
        # Initialize default roles and permissions
        init_default_roles(db)
        
        # Create default admin user if not exists
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123"),
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            
            # Assign admin role to admin user
            admin_role = db.query(Role).filter(Role.name == "admin").first()
            if admin_role:
                admin_user.roles.append(admin_role)
                db.commit()
        
        print("RBAC initialization completed successfully")
    except Exception as e:
        print(f"Error initializing RBAC: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_rbac()
