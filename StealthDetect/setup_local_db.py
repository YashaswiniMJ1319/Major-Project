
#!/usr/bin/env python3
"""
Database setup script for local MySQL (XAMPP) development
Run this script to create the database and tables locally
"""

import pymysql
import sys
from sqlalchemy import create_engine, text
from app import app, db

def create_database():
    """Create the stealth_captcha database if it doesn't exist"""
    try:
        # Connect to MySQL server without specifying database
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='',  # Default XAMPP password is empty
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Create database if it doesn't exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS stealth_captcha CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print("✓ Database 'stealth_captcha' created successfully")
        
        connection.commit()
        connection.close()
        return True
        
    except Exception as e:
        print(f"✗ Error creating database: {e}")
        return False

def setup_tables():
    """Create all tables using SQLAlchemy"""
    try:
        with app.app_context():
            # Import models to register them
            import models
            
            # Create all tables
            db.create_all()
            print("✓ All tables created successfully")
            
            # Create admin user
            from models import User
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@stealthcaptcha.com',
                    is_admin=True
                )
                admin_user.set_password('admin')
                db.session.add(admin_user)
                db.session.commit()
                print("✓ Admin user created (username: admin, password: admin)")
            else:
                print("✓ Admin user already exists")
        
        return True
        
    except Exception as e:
        print(f"✗ Error setting up tables: {e}")
        return False

def main():
    """Main setup function"""
    print("Setting up StealthCAPTCHA database for local development...")
    print("Make sure XAMPP MySQL is running before proceeding.\n")
    
    # Step 1: Create database
    print("Step 1: Creating database...")
    if not create_database():
        sys.exit(1)
    
    # Step 2: Set environment for local MySQL
    import os
    os.environ['DATABASE_URL'] = 'mysql+pymysql://root:@localhost/stealth_captcha'
    
    # Step 3: Create tables
    print("\nStep 2: Setting up tables...")
    if not setup_tables():
        sys.exit(1)
    
    # ==========================================================
    print("\nStep 3: Training initial ML model (This may take a moment)...")
    # You must import app here for app_context
    from app import app
    from ml_model import MLModel
    
    with app.app_context():
        # Initialize the model, which will then check if it needs to train
        ml_model_instance = MLModel()
        # Call the function where the comparison logic is implemented
        if ml_model_instance.is_trained:
            print("INFO: Model files exist. Forcing re-run of comparison metrics.")
            ml_model_instance.is_trained = False
        ml_model_instance.train_initial_model() 
    # ==========================================================
    
    print("\n🎉 Database setup completed successfully!")
    print("\nTo run the application locally:")
    print("1. Make sure XAMPP MySQL is running")
    print("2. Set DATABASE_URL environment variable:")
    print("   export DATABASE_URL='mysql+pymysql://root:@localhost/stealth_captcha'")
    print("3. Run: python main.py")

if __name__ == "__main__":
    main()
