# app.py
# Main application file — contains all backend code for PestSightLog.
# Run setup.py first to create the database and default admin account.

from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# ── App Configuration ──────────────────────────────────────────────────────────
app = Flask(__name__)

# Secret key used to sign session cookies — change this in production
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-secret-key-before-deploying')

# SQLite database stored in the same folder as this file
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sightings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ── Extensions Setup ───────────────────────────────────────────────────────────
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'           # Redirect here if not logged in
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'error'


# ── Database Models ────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    """A user account. is_admin=True gives access to all sightings."""
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin      = db.Column(db.Boolean, default=False, nullable=False)
    sightings     = db.relationship('Sighting', backref='user', lazy=True)

    def set_password(self, password):
        """Hash and store a password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check a plain-text password against the stored hash."""
        return check_password_hash(self.password_hash, password)


class Sighting(db.Model):
    """A single pest sighting report submitted by a user."""
    id                = db.Column(db.Integer, primary_key=True)
    date              = db.Column(db.String(20), nullable=False)
    location          = db.Column(db.String(200), nullable=False)
    pest_type         = db.Column(db.String(100), nullable=False)
    description       = db.Column(db.Text, nullable=True)
    reported_by_name  = db.Column(db.String(100), nullable=False)
    user_id           = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# ── Flask-Login: how to load a user from their session ────────────────────────
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Root URL — send logged-in users to sightings, others to login."""
    if current_user.is_authenticated:
        return redirect(url_for('sightings'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Show the login form (GET) or process login credentials (POST)."""
    if current_user.is_authenticated:
        return redirect(url_for('sightings'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('sightings'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Log the current user out and return to login page."""
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    """Show the report form (GET) or save a new sighting (POST)."""
    if request.method == 'POST':
        date             = request.form.get('date', '').strip()
        location         = request.form.get('location', '').strip()
        pest_type        = request.form.get('pest_type', '').strip()
        description      = request.form.get('description', '').strip()
        reported_by_name = request.form.get('reported_by', '').strip() or current_user.username

        # Validate required fields
        if not date or not location or not pest_type:
            flash('Date, location, and pest type are all required.', 'error')
        else:
            sighting = Sighting(
                date=date,
                location=location,
                pest_type=pest_type,
                description=description,
                reported_by_name=reported_by_name,
                user_id=current_user.id
            )
            db.session.add(sighting)
            db.session.commit()
            flash('Sighting reported successfully!', 'success')
            return redirect(url_for('sightings'))

    # Pre-fill today's date
    today = datetime.today().strftime('%Y-%m-%d')
    return render_template('report.html', today=today)


@app.route('/sightings')
@login_required
def sightings():
    """
    View sightings in a table with optional search filter.
    Admins see all sightings. Regular users see only their own.
    """
    search = request.args.get('search', '').strip()

    # Admins see everything; regular users see only their own reports
    if current_user.is_admin:
        query = Sighting.query
    else:
        query = Sighting.query.filter_by(user_id=current_user.id)

    # Apply search across location, pest type, description, and reporter name
    if search:
        like = f'%{search}%'
        query = query.filter(
            db.or_(
                Sighting.location.ilike(like),
                Sighting.pest_type.ilike(like),
                Sighting.description.ilike(like),
                Sighting.reported_by_name.ilike(like)
            )
        )

    results = query.order_by(Sighting.created_at.desc()).all()
    return render_template('sightings.html', sightings=results, search=search)


@app.route('/admin/users')
@login_required
def manage_users():
    """Admin-only page to view all user accounts."""
    if not current_user.is_admin:
        flash('Admin access required.', 'error')
        return redirect(url_for('sightings'))
    users = User.query.order_by(User.username).all()
    return render_template('users.html', users=users)


@app.route('/admin/users/add', methods=['POST'])
@login_required
def add_user():
    """Admin-only: add a new user account."""
    if not current_user.is_admin:
        flash('Admin access required.', 'error')
        return redirect(url_for('sightings'))

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    is_admin = request.form.get('is_admin') == 'on'

    if not username or not password:
        flash('Username and password are required.', 'error')
    elif User.query.filter_by(username=username).first():
        flash('That username is already taken.', 'error')
    elif len(password) < 6:
        flash('Password must be at least 6 characters.', 'error')
    else:
        user = User(username=username, is_admin=is_admin)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f'User "{username}" created.', 'success')

    return redirect(url_for('manage_users'))


@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """Admin-only: delete a user account."""
    if not current_user.is_admin:
        flash('Admin access required.', 'error')
        return redirect(url_for('sightings'))

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'error')
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f'User "{user.username}" deleted.', 'success')

    return redirect(url_for('manage_users'))


# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=False)
