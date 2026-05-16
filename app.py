"""
=====================================================
GYM MANAGEMENT SYSTEM - FLASK BACKEND (MySQL)
=====================================================
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_cors import CORS
import hashlib
from datetime import datetime, timedelta
import database as db

app = Flask(__name__)
app.secret_key = 'gym-secret-key-change-in-production-2024'
CORS(app)

@app.teardown_appcontext
def close_db_connections(error):
    """Ensure connections are returned to pool after each request"""
    pass  # Pool connections auto-return when conn.close() is called

# ─────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def is_admin():
    return session.get('logged_in') and session.get('role') == 'admin'

def is_member():
    return session.get('logged_in') and session.get('role') == 'member'

# ─────────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────────

@app.route('/')
def home():
    if is_admin():
        return redirect(url_for('dashboard'))
    if is_member():
        return redirect(url_for('member_dashboard'))
    return redirect(url_for('login'))

# ─────────────────────────────────────────────────
# ADMIN AUTH
# ─────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = db.get_admin(request.form['username'], hash_password(request.form['password']))
        if user:
            session.update({'user_id': user['id'], 'username': user['username'],
                            'full_name': user['full_name'], 'logged_in': True, 'role': 'admin'})
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Invalid credentials', portal='admin')
    return render_template('login.html', portal='admin')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─────────────────────────────────────────────────
# MEMBER AUTH
# ─────────────────────────────────────────────────

@app.route('/member/login', methods=['GET', 'POST'])
def member_login():
    if request.method == 'POST':
        member = db.get_member_by_credentials(request.form['email'], hash_password(request.form['password']))
        if member:
            session.update({'user_id': member['id'], 'full_name': member['full_name'],
                            'email': member['email'], 'logged_in': True, 'role': 'member'})
            return redirect(url_for('member_dashboard'))
        return render_template('login.html', error='Invalid email or password', portal='member')
    return render_template('login.html', portal='member')

@app.route('/member/register', methods=['GET', 'POST'])
def member_register():
    plans = db.get_all_plans()
    if request.method == 'POST':
        email = request.form['email']
        if db.get_member_by_email(email):
            return render_template('register.html', error='Email already registered', plans=plans)
        plan = db.get_plan_by_id(request.form['plan_id'])
        join_date = datetime.strptime(request.form['join_date'], '%Y-%m-%d')
        end_date = join_date + timedelta(days=plan['duration_months'] * 30)
        data = {
            'full_name':     request.form['full_name'],
            'email':         email,
            'password':      hash_password(request.form['password']),
            'phone':         request.form['phone'],
            'date_of_birth': request.form['date_of_birth'],
            'gender':        request.form['gender'],
            'address':       request.form.get('address', ''),
            'plan_id':       request.form['plan_id'],
            'join_date':     join_date.strftime('%Y-%m-%d'),
            'end_date':      end_date.strftime('%Y-%m-%d'),
            'fitness_goal':  request.form.get('fitness_goal', ''),
        }
        db.register_member(data)
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('member_login'))
    return render_template('register.html', plans=plans)

@app.route('/member/logout')
def member_logout():
    session.clear()
    return redirect(url_for('member_login'))

# ─────────────────────────────────────────────────
# MEMBER PORTAL
# ─────────────────────────────────────────────────

@app.route('/member/dashboard')
def member_dashboard():
    if not is_member(): return redirect(url_for('member_login'))
    member = db.get_member_by_id(session['user_id'])
    perf_history = db.get_member_performance_history(session['user_id'], 8)
    perf_summary = db.get_member_performance_summary(session['user_id'])
    feedback_given = db.get_member_feedback_given(session['user_id'])
    trainers = db.get_all_trainers()
    return render_template('member_dashboard.html',
                           member=member,
                           perf_history=perf_history,
                           perf_summary=perf_summary,
                           feedback_given=feedback_given,
                           trainers=trainers)

@app.route('/member/profile', methods=['GET', 'POST'])
def member_profile():
    if not is_member(): return redirect(url_for('member_login'))
    member = db.get_member_by_id(session['user_id'])
    trainers = db.get_all_trainers()
    if request.method == 'POST':
        data = {
            'full_name':     request.form['full_name'],
            'phone':         request.form['phone'],
            'address':       request.form.get('address', ''),
            'gender':        request.form['gender'],
            'date_of_birth': request.form['date_of_birth'],
            'fitness_goal':  request.form.get('fitness_goal', ''),
            'weight':        request.form.get('weight') or None,
            'height':        request.form.get('height') or None,
            'trainer_id':    request.form.get('trainer_id') or None,
        }
        db.update_member(session['user_id'], data)
        session['full_name'] = data['full_name']
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('member_profile'))
    return render_template('member_profile.html', member=member, trainers=trainers)

@app.route('/member/performance/add', methods=['POST'])
def add_performance():
    if not is_member(): return redirect(url_for('member_login'))
    data = {
        'member_id':          session['user_id'],
        'week_start':         request.form['week_start'],
        'workouts_completed': int(request.form.get('workouts_completed', 0)),
        'workouts_planned':   int(request.form.get('workouts_planned', 0)),
        'weight_kg':          request.form.get('weight_kg') or None,
        'cardio_minutes':     int(request.form.get('cardio_minutes', 0)),
        'strength_sessions':  int(request.form.get('strength_sessions', 0)),
        'notes':              request.form.get('notes', ''),
    }
    db.add_member_performance(data)
    flash('Performance log saved!', 'success')
    return redirect(url_for('member_dashboard'))

@app.route('/member/feedback/add', methods=['POST'])
def add_feedback():
    if not is_member(): return redirect(url_for('member_login'))
    data = {
        'member_id':  session['user_id'],
        'trainer_id': request.form['trainer_id'],
        'week_start': request.form['week_start'],
        'rating':     int(request.form['rating']),
        'punctuality':int(request.form['punctuality']),
        'knowledge':  int(request.form['knowledge']),
        'motivation': int(request.form['motivation']),
        'comments':   request.form.get('comments', ''),
    }
    db.add_trainer_feedback(data)
    flash('Feedback submitted! Thank you.', 'success')
    return redirect(url_for('member_dashboard'))

# ─────────────────────────────────────────────────
# MEMBER — PAYMENT (NEW FEATURE)
# ─────────────────────────────────────────────────

@app.route('/member/payments')
def member_payments():
    if not is_member(): return redirect(url_for('member_login'))
    member = db.get_member_by_id(session['user_id'])
    payments = db.get_member_payment_history(session['user_id'])
    plans = db.get_all_plans()
    return render_template('member_payments.html',
                           member=member,
                           payments=payments,
                           plans=plans)

@app.route('/member/payments/make', methods=['POST'])
def member_make_payment():
    if not is_member(): return redirect(url_for('member_login'))
    plan_id = request.form.get('plan_id')
    payment_method = request.form.get('payment_method')
    plan = db.get_plan_by_id(plan_id)
    if not plan:
        flash('Invalid plan selected.', 'error')
        return redirect(url_for('member_payments'))
    data = {
        'member_id':      session['user_id'],
        'plan_id':        plan_id,
        'amount':         plan['price'],
        'payment_method': payment_method,
        'payment_date':   datetime.now().strftime('%Y-%m-%d'),
        'transaction_id': f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'status':         'completed',
        'notes':          f"Member self-payment for {plan['plan_name']}",
    }
    db.add_payment(data)
    # Update member plan and extend end date
    join_date = datetime.now()
    end_date = join_date + timedelta(days=plan['duration_months'] * 30)
    db.update_member_plan(session['user_id'], plan_id, end_date.strftime('%Y-%m-%d'))
    flash(f'Payment of ${plan["price"]} for {plan["plan_name"]} successful! Your membership has been updated.', 'success')
    return redirect(url_for('member_payments'))

# ─────────────────────────────────────────────────
# MEMBER — ATTENDANCE
# ─────────────────────────────────────────────────

@app.route('/member/attendance')
def member_attendance():
    if not is_member(): return redirect(url_for('member_login'))
    member_id = session['user_id']
    records   = db.get_attendance_list(member_id=member_id)
    stats     = db.get_member_attendance_stats(member_id)
    weekly    = db.get_attendance_by_week()
    now = datetime.now()
    calendar_data  = db.get_member_monthly_attendance(member_id, now.year, now.month)
    attended_dates = [str(r['date']) for r in calendar_data]
    return render_template('member_attendance.html',
                           records=records, stats=stats, weekly=weekly,
                           attended_dates=attended_dates,
                           current_month=now.strftime('%B %Y'),
                           current_year=now.year,
                           current_month_num=now.month)

@app.route('/member/attendance/checkin', methods=['POST'])
def member_checkin():
    if not is_member(): return redirect(url_for('member_login'))
    # Check if already checked in today without checkout
    stats = db.get_member_attendance_stats(session['user_id'])
    if stats['active_checkin_id']:
        flash('You are already checked in! Please check out first.', 'error')
        return redirect(url_for('member_attendance'))
    db.mark_attendance(session['user_id'], notes=request.form.get('notes', ''), marked_by='member')
    flash('✅ Checked in successfully! Have a great workout!', 'success')
    return redirect(url_for('member_attendance'))

@app.route('/member/attendance/checkout/<int:attendance_id>')
def member_checkout(attendance_id):
    if not is_member(): return redirect(url_for('member_login'))
    db.mark_checkout(attendance_id)
    flash('✅ Checked out successfully! Great workout today!', 'success')
    return redirect(url_for('member_attendance'))

# ─────────────────────────────────────────────────
# MEMBER — CHANGE PASSWORD
# ─────────────────────────────────────────────────

@app.route('/member/change-password', methods=['GET', 'POST'])
def member_change_password():
    if not is_member(): return redirect(url_for('member_login'))
    if request.method == 'POST':
        current_pw = hash_password(request.form['current_password'])
        new_pw     = hash_password(request.form['new_password'])
        if db.change_member_password(session['user_id'], current_pw, new_pw):
            flash('Password updated successfully!', 'success')
            return redirect(url_for('member_dashboard'))
        else:
            flash('Current password is incorrect.', 'error')
    return render_template('member_change_password.html')

# ─────────────────────────────────────────────────
# ADMIN DASHBOARD
# ─────────────────────────────────────────────────

@app.route('/dashboard')
def dashboard():
    if not is_admin(): return redirect(url_for('login'))
    stats = db.get_dashboard_stats()
    recent_members = db.get_recent_members(5)
    return render_template('dashboard.html',
                           admin_name=session.get('full_name'),
                           stats=stats, recent_members=recent_members)

# ─────────────────────────────────────────────────
# ADMIN — MEMBERS
# ─────────────────────────────────────────────────

@app.route('/members')
def members():
    if not is_admin(): return redirect(url_for('login'))
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    members_list = db.get_members(search, status)
    plans   = db.get_all_plans()
    trainers = db.get_all_trainers()
    return render_template('members.html', members=members_list,
                           plans=plans, trainers=trainers,
                           search=search, status=status)

@app.route('/members/add', methods=['POST'])
def add_member():
    if not is_admin(): return redirect(url_for('login'))
    plan = db.get_plan_by_id(request.form['plan_id'])
    join_date = datetime.strptime(request.form['join_date'], '%Y-%m-%d')
    end_date  = join_date + timedelta(days=plan['duration_months'] * 30)
    data = {
        'full_name':     request.form['full_name'],
        'email':         request.form['email'],
        'password':      hash_password(request.form.get('password', 'changeme123')),
        'phone':         request.form['phone'],
        'date_of_birth': request.form['date_of_birth'],
        'gender':        request.form['gender'],
        'address':       request.form.get('address', ''),
        'plan_id':       request.form['plan_id'],
        'trainer_id':    request.form.get('trainer_id') or None,
        'join_date':     join_date.strftime('%Y-%m-%d'),
        'end_date':      end_date.strftime('%Y-%m-%d'),
        'status':        'active',
        'fitness_goal':  request.form.get('fitness_goal', ''),
    }
    db.add_member(data)
    flash('Member added successfully!', 'success')
    return redirect(url_for('members'))

@app.route('/members/delete/<int:member_id>')
def delete_member(member_id):
    if not is_admin(): return redirect(url_for('login'))
    db.delete_member(member_id)
    flash('Member deleted.', 'success')
    return redirect(url_for('members'))

# ─────────────────────────────────────────────────
# ADMIN — PLANS
# ─────────────────────────────────────────────────

@app.route('/plans')
def plans():
    if not is_admin(): return redirect(url_for('login'))
    return render_template('plans.html', plans=db.get_all_plans_with_count())

@app.route('/plans/add', methods=['POST'])
def add_plan():
    if not is_admin(): return redirect(url_for('login'))
    db.add_plan({
        'plan_name':       request.form['plan_name'],
        'duration_months': request.form['duration_months'],
        'price':           request.form['price'],
        'description':     request.form['description'],
        'features':        request.form['features'],
        'status':          'active'
    })
    flash('Plan added successfully!', 'success')
    return redirect(url_for('plans'))

@app.route('/plans/delete/<int:plan_id>')
def delete_plan(plan_id):
    if not is_admin(): return redirect(url_for('login'))
    try:
        db.delete_plan(plan_id)
        flash('Plan deleted successfully!', 'success')
    except Exception as e:
        flash(f'Cannot delete this plan. It may still be linked to payments or members. Error: {str(e)}', 'error')
    return redirect(url_for('plans'))

@app.route('/plans/edit/<int:plan_id>', methods=['GET', 'POST'])
def edit_plan(plan_id):
    if not is_admin(): return redirect(url_for('login'))
    plan = db.get_plan_by_id(plan_id)
    if not plan:
        flash('Plan not found.', 'error')
        return redirect(url_for('plans'))
    if request.method == 'POST':
        data = {
            'plan_name':       request.form['plan_name'],
            'duration_months': request.form['duration_months'],
            'price':           request.form['price'],
            'description':     request.form['description'],
            'features':        request.form['features'],
        }
        db.update_plan(plan_id, data)
        flash('Plan updated successfully!', 'success')
        return redirect(url_for('plans'))
    return render_template('edit_plan.html', plan=plan)

# ─────────────────────────────────────────────────
# ADMIN — TRAINERS
# ─────────────────────────────────────────────────

@app.route('/trainers')
def trainers():
    if not is_admin(): return redirect(url_for('login'))
    return render_template('trainers.html', trainers=db.get_all_trainers(),
                           ranking=db.get_trainer_performance_ranking())

@app.route('/trainers/add', methods=['POST'])
def add_trainer():
    if not is_admin(): return redirect(url_for('login'))
    db.add_trainer({
        'full_name':        request.form['full_name'],
        'email':            request.form['email'],
        'phone':            request.form['phone'],
        'specialization':   request.form['specialization'],
        'experience_years': request.form['experience_years'],
        'bio':              request.form.get('bio', '')
    })
    flash('Trainer added successfully!', 'success')
    return redirect(url_for('trainers'))

@app.route('/trainers/delete/<int:trainer_id>')
def delete_trainer(trainer_id):
    if not is_admin(): return redirect(url_for('login'))
    db.delete_trainer(trainer_id)
    flash('Trainer deleted.', 'success')
    return redirect(url_for('trainers'))

@app.route('/trainers/<int:trainer_id>/analytics')
def trainer_analytics(trainer_id):
    if not is_admin(): return redirect(url_for('login'))
    trainer     = db.get_trainer_by_id(trainer_id)
    weekly      = db.get_trainer_weekly_feedback(trainer_id)
    ranking     = db.get_trainer_performance_ranking()
    all_feedback = db.get_trainer_all_feedback(trainer_id)
    return render_template('trainer_analytics.html',
                           trainer=trainer, weekly=weekly,
                           ranking=ranking, all_feedback=all_feedback)

@app.route('/members/expired')
def expired_members():
    if not is_admin(): return redirect(url_for('login'))
    expired = db.get_expired_members()
    plans   = db.get_all_plans()
    return render_template('expired_members.html', expired=expired, plans=plans)

# ─────────────────────────────────────────────────
# ADMIN — PAYMENTS
# ─────────────────────────────────────────────────

@app.route('/payments')
def payments():
    if not is_admin(): return redirect(url_for('login'))
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    method = request.args.get('method', '')
    return render_template('payments.html',
                           payments=db.get_payments(search, status, method),
                           stats=db.get_payment_stats(),
                           members=db.get_all_members(),
                           plans=db.get_all_plans(),
                           search=search, status_filter=status, method_filter=method)

@app.route('/payments/add', methods=['POST'])
def add_payment():
    if not is_admin(): return redirect(url_for('login'))
    db.add_payment({
        'member_id':      request.form['member_id'],
        'plan_id':        request.form['plan_id'],
        'amount':         request.form['amount'],
        'payment_method': request.form['payment_method'],
        'payment_date':   request.form['payment_date'],
        'transaction_id': request.form.get('transaction_id', ''),
        'notes':          request.form.get('notes', ''),
        'status':         'completed'
    })
    flash('Payment recorded successfully!', 'success')
    return redirect(url_for('payments'))

# ─────────────────────────────────────────────────
# ADMIN — ATTENDANCE
# ─────────────────────────────────────────────────

@app.route('/attendance')
def attendance():
    if not is_admin(): return redirect(url_for('login'))
    search      = request.args.get('search', '')
    date_filter = request.args.get('date', '')
    records  = db.get_attendance_list(search, date_filter)
    stats    = db.get_attendance_stats()
    today    = db.get_today_attendance()
    members_list = db.get_all_members()
    return render_template('attendance.html',
                           records=records, stats=stats, today=today,
                           members=members_list, search=search, date_filter=date_filter)

@app.route('/attendance/mark', methods=['POST'])
def mark_attendance():
    if not is_admin(): return redirect(url_for('login'))
    db.mark_attendance(request.form.get('member_id'),
                       notes=request.form.get('notes', ''), marked_by='admin')
    flash('Attendance marked successfully!', 'success')
    return redirect(url_for('attendance'))

@app.route('/attendance/checkout/<int:attendance_id>')
def checkout(attendance_id):
    if not is_admin(): return redirect(url_for('login'))
    db.mark_checkout(attendance_id)
    flash('Check-out recorded!', 'success')
    return redirect(url_for('attendance'))

@app.route('/attendance/delete/<int:attendance_id>')
def delete_attendance(attendance_id):
    if not is_admin(): return redirect(url_for('login'))
    db.delete_attendance(attendance_id)
    flash('Record deleted.', 'success')
    return redirect(url_for('attendance'))

# ─────────────────────────────────────────────────
# ADMIN — TRAINER ATTENDANCE
# ─────────────────────────────────────────────────

@app.route('/trainer-attendance')
def trainer_attendance():
    if not is_admin(): return redirect(url_for('login'))
    search      = request.args.get('search', '')
    date_filter = request.args.get('date', '')
    records  = db.get_trainer_attendance_list(search, date_filter)
    stats    = db.get_trainer_attendance_stats()
    today    = db.get_today_trainer_attendance()
    trainers_list = db.get_all_trainers()
    summary  = db.get_trainer_attendance_summary()
    return render_template('trainer_attendance.html',
                           records=records, stats=stats, today=today,
                           trainers=trainers_list, summary=summary,
                           search=search, date_filter=date_filter)

@app.route('/trainer-attendance/mark', methods=['POST'])
def mark_trainer_attendance():
    if not is_admin(): return redirect(url_for('login'))
    db.mark_trainer_attendance(request.form.get('trainer_id'),
                               notes=request.form.get('notes', ''))
    flash('Trainer attendance marked!', 'success')
    return redirect(url_for('trainer_attendance'))

@app.route('/trainer-attendance/checkout/<int:attendance_id>')
def trainer_checkout(attendance_id):
    if not is_admin(): return redirect(url_for('login'))
    db.mark_trainer_checkout(attendance_id)
    flash('Trainer check-out recorded!', 'success')
    return redirect(url_for('trainer_attendance'))

@app.route('/trainer-attendance/delete/<int:attendance_id>')
def delete_trainer_attendance(attendance_id):
    if not is_admin(): return redirect(url_for('login'))
    db.delete_trainer_attendance(attendance_id)
    flash('Record deleted.', 'success')
    return redirect(url_for('trainer_attendance'))

# ─────────────────────────────────────────────────
# ADMIN — CHANGE PASSWORD
# ─────────────────────────────────────────────────

@app.route('/admin/change-password', methods=['GET', 'POST'])
def admin_change_password():
    if not is_admin(): return redirect(url_for('login'))
    if request.method == 'POST':
        current_pw = hash_password(request.form['current_password'])
        new_pw     = hash_password(request.form['new_password'])
        if db.change_admin_password(session['user_id'], current_pw, new_pw):
            flash('Password updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Current password is incorrect.', 'error')
    return render_template('admin_change_password.html')

# ─────────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────────

@app.route('/api/trainer/<int:trainer_id>/weekly')
def api_trainer_weekly(trainer_id):
    if not is_admin(): return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(db.get_trainer_weekly_feedback(trainer_id))

@app.route('/api/member/performance')
def api_member_performance():
    if not is_member(): return jsonify({'error': 'Unauthorized'}), 401
    history = db.get_member_performance_history(session['user_id'])
    return jsonify([{k: str(v) if hasattr(v, 'isoformat') else v
                     for k, v in row.items()} for row in history])

@app.route('/api/attendance/weekly')
def api_attendance_weekly():
    if not is_admin(): return jsonify({'error': 'Unauthorized'}), 401
    data = db.get_attendance_by_week(12)
    return jsonify([{k: str(v) if hasattr(v, 'isoformat') else v
                     for k, v in row.items()} for row in data])

# ─────────────────────────────────────────────────
# ERROR HANDLERS
# ─────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('login.html', error='Page not found', portal='admin'), 404

@app.errorhandler(500)
def server_error(e):
    return "Internal server error", 500

# ─────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────

if __name__ == '__main__':
    db.init_database()
    print("=" * 55)
    print("🏋️  GYM MANAGEMENT SYSTEM — MySQL Edition")
    print("=" * 55)
    print("🌐 http://localhost:5000")
    print("👑 Admin:  /login  →  admin / admin123")
    print("👤 Member: /member/login  or  /member/register")
    print("=" * 55)
    app.run(debug=True, port=5000)