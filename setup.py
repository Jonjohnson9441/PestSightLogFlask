# setup.py
# Run this ONCE before starting the app for the first time.
# It creates the database tables and a default admin account.
#
# Usage:
#   python setup.py

from app import app, db, User

with app.app_context():
    # Create all database tables defined in app.py
    db.create_all()
    print('Database tables created.')

    # Create the default admin account if it doesn't already exist
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', is_admin=True)
        admin.set_password('changeme123')
        db.session.add(admin)
        db.session.commit()
        print()
        print('  Default admin account created:')
        print('  Username : admin')
        print('  Password : changeme123')
        print()
        print('  IMPORTANT: Log in and change this password immediately.')
    else:
        print('Admin account already exists — no changes made.')

    print('Setup complete. You can now run: python app.py')
