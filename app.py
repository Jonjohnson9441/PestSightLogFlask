# app.py
# Main application file — contains all backend code for PestSightLog.
# Run setup.py first to create the database and default admin account.

from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import uuid

# ── App Configuration ──────────────────────────────────────────────────────────
app = Flask(__name__)

# Secret key used to sign session cookies — change this in production
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-secret-key-before-deploying')

# SQLite database stored in the same folder as this file
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sightings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Photo upload settings
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB max
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    first_name    = db.Column(db.String(80), nullable=True)
    last_name     = db.Column(db.String(80), nullable=True)
    sightings     = db.relationship('Sighting', foreign_keys='Sighting.user_id', back_populates='reporter', lazy=True)

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f'{self.first_name} {self.last_name}'
        return self.username

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
    sighting_time     = db.Column(db.String(10), nullable=True)
    photo_filename    = db.Column(db.String(200), nullable=True)
    status            = db.Column(db.String(20), default='open', nullable=False)
    owner_id          = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    owner_taken_at    = db.Column(db.DateTime, nullable=True)
    user_id           = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    reporter          = db.relationship('User', foreign_keys=[user_id], back_populates='sightings')
    owner             = db.relationship('User', foreign_keys=[owner_id])
    capa_entries      = db.relationship('CAPAEntry', backref='sighting', lazy=True,
                                        order_by='CAPAEntry.created_at')


class CAPAEntry(db.Model):
    """A single entry in the CAPA trail for a pest sighting."""
    id             = db.Column(db.Integer, primary_key=True)
    sighting_id    = db.Column(db.Integer, db.ForeignKey('sighting.id'), nullable=False)
    user_id        = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    entry_type     = db.Column(db.String(50), nullable=False)
    description    = db.Column(db.Text, nullable=False)
    photo_filename = db.Column(db.String(200), nullable=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    author         = db.relationship('User', foreign_keys=[user_id])


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
        first_name    = request.form.get('first_name', '').strip()
        last_name     = request.form.get('last_name', '').strip()
        date          = request.form.get('date', '').strip()
        sighting_time = request.form.get('sighting_time', '').strip()
        location      = request.form.get('location', '').strip()
        pest_type     = request.form.get('pest_type', '').strip()
        description   = request.form.get('description', '').strip()

        reported_by_name = f'{first_name} {last_name}'.strip() or current_user.username

        if not date or not location or not pest_type or not first_name or not last_name:
            flash('First name, last name, date, location, and pest type are all required.', 'error')
        else:
            # Handle optional photo upload
            photo_filename = None
            photo_file = request.files.get('photo')
            if photo_file and photo_file.filename and allowed_file(photo_file.filename):
                ext = photo_file.filename.rsplit('.', 1)[1].lower()
                photo_filename = f'{uuid.uuid4().hex}.{ext}'
                photo_file.save(os.path.join(UPLOAD_FOLDER, photo_filename))

            sighting = Sighting(
                date=date,
                sighting_time=sighting_time or None,
                location=location,
                pest_type=pest_type,
                description=description,
                reported_by_name=reported_by_name,
                photo_filename=photo_filename,
                user_id=current_user.id
            )
            db.session.add(sighting)
            db.session.commit()
            flash('Sighting reported successfully!', 'success')
            return redirect(url_for('sightings'))

    today = datetime.today().strftime('%Y-%m-%d')
    now_time = datetime.now().strftime('%H:%M')
    return render_template('report.html', today=today, now_time=now_time)


@app.route('/sightings')
@login_required
def sightings():
    """View all sightings with status tabs and optional search filter."""
    search     = request.args.get('search', '').strip()
    status_tab = request.args.get('status', 'open')

    query = Sighting.query

    if status_tab in ('open', 'in_progress', 'completed'):
        query = query.filter_by(status=status_tab)

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

    counts = {
        'open':        Sighting.query.filter_by(status='open').count(),
        'in_progress': Sighting.query.filter_by(status='in_progress').count(),
        'completed':   Sighting.query.filter_by(status='completed').count(),
    }

    return render_template('sightings.html', sightings=results,
                           search=search, status_tab=status_tab, counts=counts)


@app.route('/sightings/<int:sighting_id>')
@login_required
def sighting_detail(sighting_id):
    """Detail view for a single sighting with its CAPA trail."""
    sighting = Sighting.query.get_or_404(sighting_id)
    return render_template('sighting_detail.html', sighting=sighting)


@app.route('/sightings/<int:sighting_id>/take-ownership', methods=['POST'])
@login_required
def take_ownership(sighting_id):
    sighting = Sighting.query.get_or_404(sighting_id)
    if sighting.status == 'open':
        sighting.status         = 'in_progress'
        sighting.owner_id       = current_user.id
        sighting.owner_taken_at = datetime.utcnow()
        db.session.commit()
        flash('You have taken ownership of this sighting.', 'success')
    return redirect(url_for('sighting_detail', sighting_id=sighting_id))


@app.route('/sightings/<int:sighting_id>/release-ownership', methods=['POST'])
@login_required
def release_ownership(sighting_id):
    sighting = Sighting.query.get_or_404(sighting_id)
    if sighting.owner_id == current_user.id or current_user.is_admin:
        sighting.status         = 'open'
        sighting.owner_id       = None
        sighting.owner_taken_at = None
        db.session.commit()
        flash('Ownership released — sighting is back to Open.', 'success')
    return redirect(url_for('sighting_detail', sighting_id=sighting_id))


@app.route('/sightings/<int:sighting_id>/complete', methods=['POST'])
@login_required
def complete_sighting(sighting_id):
    sighting = Sighting.query.get_or_404(sighting_id)
    if sighting.owner_id == current_user.id or current_user.is_admin:
        sighting.status = 'completed'
        db.session.commit()
        flash('Sighting marked as Completed.', 'success')
    return redirect(url_for('sighting_detail', sighting_id=sighting_id))


@app.route('/sightings/<int:sighting_id>/reopen', methods=['POST'])
@login_required
def reopen_sighting(sighting_id):
    """Admin-only: reopen a completed sighting."""
    if not current_user.is_admin:
        flash('Admin access required.', 'error')
        return redirect(url_for('sighting_detail', sighting_id=sighting_id))
    sighting = Sighting.query.get_or_404(sighting_id)
    sighting.status = 'in_progress'
    db.session.commit()
    flash('Sighting reopened and set back to In Progress.', 'success')
    return redirect(url_for('sighting_detail', sighting_id=sighting_id))


@app.route('/sightings/<int:sighting_id>/capa', methods=['POST'])
@login_required
def add_capa(sighting_id):
    """Add CAPA entries to a sighting.

    form_type='response' creates up to 3 entries at once (CA + Root Cause + Preventive).
    form_type='followup' creates a single Verification or Comment entry.
    """
    sighting  = Sighting.query.get_or_404(sighting_id)
    form_type = request.form.get('form_type', 'followup')

    # Handle optional photo (shared by both form types)
    photo_filename = None
    photo_file = request.files.get('photo')
    if photo_file and photo_file.filename and allowed_file(photo_file.filename):
        ext = photo_file.filename.rsplit('.', 1)[1].lower()
        photo_filename = f'{uuid.uuid4().hex}.{ext}'
        photo_file.save(os.path.join(UPLOAD_FOLDER, photo_filename))

    if form_type == 'response':
        corrective = request.form.get('corrective', '').strip()
        root_cause = request.form.get('root_cause', '').strip()
        preventive = request.form.get('preventive', '').strip()

        if not corrective:
            flash('Corrective Action is required.', 'error')
            return redirect(url_for('sighting_detail', sighting_id=sighting_id))

        added = 0
        for entry_type, text in [
            ('Corrective Action', corrective),
            ('Root Cause',        root_cause),
            ('Preventive Action', preventive),
        ]:
            if text:
                entry = CAPAEntry(
                    sighting_id=sighting_id,
                    user_id=current_user.id,
                    entry_type=entry_type,
                    description=text,
                    photo_filename=photo_filename if entry_type == 'Corrective Action' else None
                )
                db.session.add(entry)
                added += 1

        db.session.commit()
        flash(f'CAPA response logged ({added} entr{"y" if added == 1 else "ies"} added).', 'success')

    else:  # followup
        entry_type  = request.form.get('entry_type', '').strip()
        description = request.form.get('description', '').strip()

        if not entry_type or not description:
            flash('Entry type and description are required.', 'error')
            return redirect(url_for('sighting_detail', sighting_id=sighting_id))

        entry = CAPAEntry(
            sighting_id=sighting_id,
            user_id=current_user.id,
            entry_type=entry_type,
            description=description,
            photo_filename=photo_filename
        )
        db.session.add(entry)
        db.session.commit()
        flash('Follow-up entry added.', 'success')

    return redirect(url_for('sighting_detail', sighting_id=sighting_id))


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

    username   = request.form.get('username', '').strip()
    password   = request.form.get('password', '').strip()
    first_name = request.form.get('first_name', '').strip()
    last_name  = request.form.get('last_name', '').strip()
    is_admin   = request.form.get('is_admin') == 'on'

    if not username or not password or not first_name or not last_name:
        flash('All fields are required.', 'error')
    elif User.query.filter_by(username=username).first():
        flash('That username is already taken.', 'error')
    elif len(password) < 6:
        flash('Password must be at least 6 characters.', 'error')
    else:
        user = User(username=username, is_admin=is_admin,
                    first_name=first_name, last_name=last_name)
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


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve an uploaded photo."""
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/admin/users/<int:user_id>/edit-name', methods=['POST'])
@login_required
def edit_user_name(user_id):
    """Admin-only: update a user's first and last name."""
    if not current_user.is_admin:
        flash('Admin access required.', 'error')
        return redirect(url_for('sightings'))
    user = User.query.get_or_404(user_id)
    user.first_name = request.form.get('first_name', '').strip()
    user.last_name  = request.form.get('last_name', '').strip()
    db.session.commit()
    flash(f'Name updated for "{user.username}".', 'success')
    return redirect(url_for('manage_users'))


@app.route('/admin/users/<int:user_id>/set-password', methods=['POST'])
@login_required
def set_user_password(user_id):
    """Admin-only: reset another user's password."""
    if not current_user.is_admin:
        flash('Admin access required.', 'error')
        return redirect(url_for('sightings'))
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password', '').strip()
    if len(new_password) < 6:
        flash('Password must be at least 6 characters.', 'error')
    else:
        user.set_password(new_password)
        db.session.commit()
        flash(f'Password for "{user.username}" has been updated.', 'success')
    return redirect(url_for('manage_users'))


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Allow any logged-in user to change their own password."""
    if request.method == 'POST':
        current_pw = request.form.get('current_password', '')
        new_pw     = request.form.get('new_password', '').strip()
        confirm_pw = request.form.get('confirm_password', '').strip()

        if not current_user.check_password(current_pw):
            flash('Current password is incorrect.', 'error')
        elif len(new_pw) < 6:
            flash('New password must be at least 6 characters.', 'error')
        elif new_pw != confirm_pw:
            flash('New passwords do not match.', 'error')
        else:
            current_user.set_password(new_pw)
            db.session.commit()
            flash('Password changed successfully.', 'success')
            return redirect(url_for('sightings'))

    return render_template('change_password.html')


# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=False)
