# setup.py
# Run this ONCE before starting the app for the first time.
# It creates the database tables and a default admin account.
#
# Usage:
#   python setup.py

from app import app, db, User
import sqlite3
import os

with app.app_context():
    # Create all database tables defined in app.py
    db.create_all()
    print('Database tables created.')

    # Migration: add new columns to existing databases if they are missing
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'sightings.db')
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        existing = [row[1] for row in cursor.execute('PRAGMA table_info(sighting)').fetchall()]
        if 'sighting_time' not in existing:
            cursor.execute('ALTER TABLE sighting ADD COLUMN sighting_time VARCHAR(10)')
            print('Added sighting_time column.')
        if 'photo_filename' not in existing:
            cursor.execute('ALTER TABLE sighting ADD COLUMN photo_filename VARCHAR(200)')
            print('Added photo_filename column.')
        if 'status' not in existing:
            cursor.execute("ALTER TABLE sighting ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'open'")
            print('Added status column.')
        if 'owner_id' not in existing:
            cursor.execute('ALTER TABLE sighting ADD COLUMN owner_id INTEGER REFERENCES user(id)')
            print('Added owner_id column.')
        if 'owner_taken_at' not in existing:
            cursor.execute('ALTER TABLE sighting ADD COLUMN owner_taken_at DATETIME')
            print('Added owner_taken_at column.')
        conn.commit()
        conn.close()

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
