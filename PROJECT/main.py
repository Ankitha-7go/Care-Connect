# ──────────────────────────────────────────────
#  Hospital Management System (HMS)
#  Author  : Ankitha
#  Version : 1.0
#  Description: A Flask-based Hospital Management
#               System with patient booking, doctor
#               management, and user authentication.
# ──────────────────────────────────────────────

import os
import pymysql
pymysql.install_as_MySQLdb()

from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    UserMixin, LoginManager, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
# from flask_mail import Mail
import json


# ──────────────────────────────────────────────
#  APP SETUP
# ──────────────────────────────────────────────
app = Flask(__name__)

# ✅ FIX: Use environment variable for secret key (never hardcode in production)
app.secret_key = os.environ.get('SECRET_KEY', 'hmsprojects_dev_key')

# ✅ FIX: Use environment variable for DB URI
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'mysql://root:@localhost/hmdbmss'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ──────────────────────────────────────────────
#  LOGIN MANAGER
# ──────────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ──────────────────────────────────────────────
#  SMTP MAIL (uncomment and configure to enable)
# ──────────────────────────────────────────────
# app.config.update(
#     MAIL_SERVER='smtp.gmail.com',
#     MAIL_PORT='465',
#     MAIL_USE_SSL=True,
#     MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
#     MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD')
# )
# mail = Mail(app)


# ──────────────────────────────────────────────
#  DATABASE MODELS
# ──────────────────────────────────────────────
class Test(db.Model):
    id    = db.Column(db.Integer, primary_key=True)
    name  = db.Column(db.String(100))
    email = db.Column(db.String(100))


class User(UserMixin, db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    usertype = db.Column(db.String(50))                  # 'Admin', 'Doctor', 'Patient'
    email    = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(1000))


class Patients(db.Model):
    pid     = db.Column(db.Integer, primary_key=True)
    email   = db.Column(db.String(50))
    name    = db.Column(db.String(50))
    gender  = db.Column(db.String(50))
    slot    = db.Column(db.String(50))
    disease = db.Column(db.String(50))
    time    = db.Column(db.String(50), nullable=False)
    date    = db.Column(db.String(50), nullable=False)
    dept    = db.Column(db.String(50))
    number  = db.Column(db.String(50))
    # ✅ NEW: Track appointment status
    status  = db.Column(db.String(20), default='Pending')  # Pending / Confirmed / Cancelled


class Doctors(db.Model):
    did        = db.Column(db.Integer, primary_key=True)
    email      = db.Column(db.String(50))
    doctorname = db.Column(db.String(50))
    dept       = db.Column(db.String(50))


class Trigr(db.Model):
    tid       = db.Column(db.Integer, primary_key=True)
    pid       = db.Column(db.Integer)
    email     = db.Column(db.String(50))
    name      = db.Column(db.String(50))
    action    = db.Column(db.String(50))
    timestamp = db.Column(db.String(50))


# ──────────────────────────────────────────────
#  HELPER: Admin check
# ──────────────────────────────────────────────
def is_admin():
    return current_user.is_authenticated and current_user.usertype == "Admin"


# ──────────────────────────────────────────────
#  ROUTES
# ──────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


# ✅ FIX: Restrict doctor creation to Admin only
@app.route('/doctors', methods=['POST', 'GET'])
@login_required
def doctors():
    if not is_admin():
        flash("Unauthorized! Only Admins can add doctors.", "danger")
        return redirect(url_for('index'))

    if request.method == "POST":
        email      = request.form.get('email', '').strip()
        doctorname = request.form.get('doctorname', '').strip()
        dept       = request.form.get('dept', '').strip()

        # ✅ NEW: Basic empty-field validation
        if not email or not doctorname or not dept:
            flash("All fields are required.", "warning")
            return render_template('doctor.html')

        query = Doctors(email=email, doctorname=doctorname, dept=dept)
        db.session.add(query)
        db.session.commit()
        flash("Doctor information stored successfully.", "primary")

    return render_template('doctor.html')


@app.route('/patients', methods=['POST', 'GET'])
@login_required
def patient():
    doct = Doctors.query.all()

    if request.method == "POST":
        email   = request.form.get('email', '').strip()
        name    = request.form.get('name', '').strip()
        gender  = request.form.get('gender', '').strip()
        slot    = request.form.get('slot', '').strip()
        disease = request.form.get('disease', '').strip()
        time    = request.form.get('time', '').strip()
        date    = request.form.get('date', '').strip()
        dept    = request.form.get('dept', '').strip()
        number  = request.form.get('number', '').strip()

        # ✅ FIX: Cleaner phone number validation (checks length AND digits only)
        if not number.isdigit() or len(number) != 10:
            flash("Please enter a valid 10-digit phone number (digits only).", "warning")
            return render_template('patient.html', doct=doct)

        # ✅ NEW: Validate required fields
        if not all([email, name, gender, slot, disease, time, date, dept]):
            flash("All fields are required.", "warning")
            return render_template('patient.html', doct=doct)

        query = Patients(
            email=email, name=name, gender=gender, slot=slot,
            disease=disease, time=time, date=date, dept=dept,
            number=number, status='Pending'
        )
        db.session.add(query)
        db.session.commit()

        # Uncomment to send confirmation email:
        # mail.send_message(
        #     "Hospital Booking Confirmed",
        #     sender=app.config['MAIL_USERNAME'],
        #     recipients=[email],
        #     body=f"Booking confirmed!\nName: {name}\nSlot: {slot}\nDate: {date}"
        # )

        flash("Booking Confirmed Successfully!", "info")

    return render_template('patient.html', doct=doct)


@app.route('/bookings')
@login_required
def bookings():
    em = current_user.email

    if current_user.usertype == "Doctor":
        # Doctors see all patient bookings
        query = Patients.query.all()
    elif is_admin():
        # Admins also see everything
        query = Patients.query.all()
    else:
        # Patients see only their own bookings
        query = Patients.query.filter_by(email=em).all()

    return render_template('booking.html', query=query)


@app.route("/edit/<string:pid>", methods=['POST', 'GET'])
@login_required
def edit(pid):
    post = Patients.query.filter_by(pid=pid).first()

    # ✅ NEW: Prevent patients from editing other patients' records
    if not post:
        flash("Record not found.", "danger")
        return redirect('/bookings')

    if current_user.usertype not in ("Doctor", "Admin") and post.email != current_user.email:
        flash("Unauthorized action.", "danger")
        return redirect('/bookings')

    if request.method == "POST":
        email   = request.form.get('email', '').strip()
        name    = request.form.get('name', '').strip()
        gender  = request.form.get('gender', '').strip()
        slot    = request.form.get('slot', '').strip()
        disease = request.form.get('disease', '').strip()
        time    = request.form.get('time', '').strip()
        date    = request.form.get('date', '').strip()
        dept    = request.form.get('dept', '').strip()
        number  = request.form.get('number', '').strip()
        status  = request.form.get('status', post.status).strip()

        # ✅ FIX: Validate phone number on edit too
        if not number.isdigit() or len(number) != 10:
            flash("Please enter a valid 10-digit phone number.", "warning")
            return render_template('edit.html', posts=post)

        post.email   = email
        post.name    = name
        post.gender  = gender
        post.slot    = slot
        post.disease = disease
        post.time    = time
        post.date    = date
        post.dept    = dept
        post.number  = number
        post.status  = status
        db.session.commit()

        flash("Appointment updated successfully.", "success")
        return redirect('/bookings')

    return render_template('edit.html', posts=post)


@app.route("/delete/<string:pid>", methods=['POST', 'GET'])
@login_required
def delete(pid):
    query = Patients.query.filter_by(pid=pid).first()

    if not query:
        flash("Record not found.", "danger")
        return redirect('/bookings')

    # ✅ NEW: Only admin/doctor or the patient themselves can delete
    if current_user.usertype not in ("Doctor", "Admin") and query.email != current_user.email:
        flash("Unauthorized action.", "danger")
        return redirect('/bookings')

    db.session.delete(query)
    db.session.commit()
    flash("Appointment deleted successfully.", "danger")
    return redirect('/bookings')


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == "POST":
        username = request.form.get('username', '').strip()
        usertype = request.form.get('usertype', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        # ✅ NEW: Basic field validation
        if not all([username, usertype, email, password]):
            flash("All fields are required.", "warning")
            return render_template('signup.html')

        # ✅ NEW: Minimum password length
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "warning")
            return render_template('signup.html')

        user = User.query.filter_by(email=email).first()
        if user:
            flash("Email already exists. Please login.", "warning")
            return render_template('signup.html')

        # ✅ FIX: Hash the password before storing
        enc_password = generate_password_hash(password)
        myquery = User(username=username, usertype=usertype, email=email, password=enc_password)
        db.session.add(myquery)
        db.session.commit()

        flash("Signup successful! Please login.", "success")
        return render_template('login.html')

    return render_template('signup.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == "POST":
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash("Email and password are required.", "warning")
            return render_template('login.html')

        user = User.query.filter_by(email=email).first()

        # ✅ FIX: Use check_password_hash instead of plain text comparison
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash(f"Welcome back, {user.username}!", "primary")
            return redirect(url_for('index'))
        else:
            flash("Invalid email or password. Please try again.", "danger")
            return render_template('login.html')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "warning")
    return redirect(url_for('login'))


@app.route('/test')
def test():
    try:
        Test.query.all()
        return 'Database is Connected ✅'
    except Exception as e:
        return f'Database is NOT Connected ❌ Error: {str(e)}'


@app.route('/details')
@login_required
def details():
    # ✅ NEW: Only admins can view trigger/audit logs
    if not is_admin():
        flash("Unauthorized! Only Admins can view audit logs.", "danger")
        return redirect(url_for('index'))
    posts = Trigr.query.all()
    return render_template('trigers.html', posts=posts)


@app.route('/search', methods=['POST', 'GET'])
@login_required
def search():
    if request.method == "POST":
        query_str = request.form.get('search', '').strip()

        if not query_str:
            flash("Please enter a search term.", "warning")
            return render_template('index.html')

        # Search by department OR doctor name (case-insensitive, partial match)
        dept_result = Doctors.query.filter(Doctors.dept.ilike(f"%{query_str}%"))
        name_result = Doctors.query.filter(Doctors.doctorname.ilike(f"%{query_str}%"))

        if dept_result.first() or name_result.first():
            flash("Doctor is Available ✅", "info")
        else:
            flash("Doctor is Not Available ❌", "danger")

    return render_template('index.html')


# ──────────────────────────────────────────────
#  DB INIT & RUN
# ──────────────────────────────────────────────

# ✅ FIX: Proper app context for db creation
with app.app_context():
    db.create_all()

# ✅ FIX: Guard app.run() so it doesn't run on import
if __name__ == '__main__':
    # Set debug=False in production!
    app.run(debug=os.environ.get('FLASK_DEBUG', 'True') == 'True', host='0.0.0.0')