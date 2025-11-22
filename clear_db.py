from app import app, db

def clear_db():
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables...")
        db.create_all()
        print("Database cleared and re-initialized successfully.")

if __name__ == "__main__":
    confirmation = input("This will DELETE ALL DATA. Are you sure? (y/N): ")
    if confirmation.lower() == 'y':
        clear_db()
    else:
        print("Operation cancelled.")
