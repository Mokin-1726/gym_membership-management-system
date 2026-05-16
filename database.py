"""
=====================================================
GYM MANAGEMENT SYSTEM - MYSQL DATABASE MODULE
=====================================================
"""

import mysql.connector
from mysql.connector import pooling
from datetime import datetime
import hashlib
import os

# ─────────────────────────────────────────────────
# MySQL CONFIG — update these values!
# ─────────────────────────────────────────────────
DB_CONFIG = {
    'host':     os.environ.get('DB_HOST', 'localhost'),
    'port':     int(os.environ.get('DB_PORT', 3306)),
    'user':     os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'Mokin@1726'),
    'database': os.environ.get('DB_NAME', 'gym_management'),
    'charset':  'utf8mb4',
}

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name='gym_pool',
            pool_size=20,
            pool_reset_session=True,
            **DB_CONFIG
        )
    return _pool

def get_connection():
    try:
        return get_pool().get_connection()
    except Exception:
        # Reset pool if exhausted
        global _pool
        _pool = None
        return get_pool().get_connection()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ─────────────────────────────────────────────────
# DATABASE INIT — No default plans seeded
# ─────────────────────────────────────────────────

def init_database():
    cfg = {k: v for k, v in DB_CONFIG.items() if k != 'database'}
    conn = mysql.connector.connect(**cfg)
    cur  = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute(f"USE `{DB_CONFIG['database']}`")
    # Increase max connections to prevent pool exhaustion
    cur.execute("SET GLOBAL max_connections = 200")
    cur.execute("SET GLOBAL wait_timeout = 28800")
    cur.execute("SET GLOBAL interactive_timeout = 28800")

    ddl = [
        """CREATE TABLE IF NOT EXISTS admins (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS trainers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            phone VARCHAR(20) NOT NULL,
            specialization VARCHAR(100),
            experience_years INT DEFAULT 0,
            bio TEXT,
            status ENUM('active','inactive') DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS plans (
            id INT AUTO_INCREMENT PRIMARY KEY,
            plan_name VARCHAR(100) NOT NULL,
            duration_months INT NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            description TEXT,
            features TEXT,
            status ENUM('active','inactive') DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS members (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            phone VARCHAR(20) NOT NULL,
            date_of_birth DATE NOT NULL,
            gender ENUM('Male','Female','Other') NOT NULL,
            address TEXT,
            plan_id INT,
            trainer_id INT,
            join_date DATE NOT NULL,
            end_date DATE NOT NULL,
            status ENUM('active','expired','pending') DEFAULT 'active',
            weight DECIMAL(5,2),
            height DECIMAL(5,2),
            fitness_goal VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE SET NULL,
            FOREIGN KEY (trainer_id) REFERENCES trainers(id) ON DELETE SET NULL
        )""",
        """CREATE TABLE IF NOT EXISTS payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            member_id INT NOT NULL,
            plan_id INT NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            payment_method ENUM('cash','card','online','upi') NOT NULL,
            payment_date DATE NOT NULL,
            transaction_id VARCHAR(100),
            status ENUM('completed','pending','failed') DEFAULT 'completed',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
            FOREIGN KEY (plan_id) REFERENCES plans(id)
        )""",
        """CREATE TABLE IF NOT EXISTS trainer_feedback (
            id INT AUTO_INCREMENT PRIMARY KEY,
            member_id INT NOT NULL,
            trainer_id INT NOT NULL,
            week_start DATE NOT NULL,
            rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
            punctuality INT NOT NULL CHECK (punctuality BETWEEN 1 AND 5),
            knowledge INT NOT NULL CHECK (knowledge BETWEEN 1 AND 5),
            motivation INT NOT NULL CHECK (motivation BETWEEN 1 AND 5),
            comments TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
            FOREIGN KEY (trainer_id) REFERENCES trainers(id) ON DELETE CASCADE,
            UNIQUE KEY unique_feedback (member_id, trainer_id, week_start)
        )""",
        """CREATE TABLE IF NOT EXISTS member_performance (
            id INT AUTO_INCREMENT PRIMARY KEY,
            member_id INT NOT NULL,
            week_start DATE NOT NULL,
            workouts_completed INT DEFAULT 0,
            workouts_planned INT DEFAULT 0,
            weight_kg DECIMAL(5,2),
            cardio_minutes INT DEFAULT 0,
            strength_sessions INT DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
            UNIQUE KEY unique_performance (member_id, week_start)
        )""",
        """CREATE TABLE IF NOT EXISTS attendance (
            id INT AUTO_INCREMENT PRIMARY KEY,
            member_id INT NOT NULL,
            date DATE NOT NULL,
            check_in DATETIME,
            check_out DATETIME,
            duration_minutes INT,
            notes TEXT,
            marked_by ENUM('admin','member') DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS trainer_attendance (
            id INT AUTO_INCREMENT PRIMARY KEY,
            trainer_id INT NOT NULL,
            date DATE NOT NULL,
            check_in DATETIME,
            check_out DATETIME,
            duration_minutes INT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (trainer_id) REFERENCES trainers(id) ON DELETE CASCADE
        )""",
    ]

    for stmt in ddl:
        cur.execute(stmt)
    conn.commit()

    # Seed only admin — NO default plans
    try:
        cur.execute("INSERT INTO admins (username,password,full_name,email) VALUES (%s,%s,%s,%s)",
                    ('admin', hash_password('admin123'), 'System Administrator', 'admin@gym.com'))
        conn.commit()
    except:
        conn.rollback()

    cur.close()
    conn.close()
    print("✅ MySQL database initialized successfully!")


# ─────────────────────────────────────────────────
# ADMIN
# ─────────────────────────────────────────────────

def get_admin(username, hashed_password):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT id,username,full_name,email FROM admins WHERE username=%s AND password=%s",
                (username, hashed_password))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row

def change_admin_password(admin_id, current_hashed, new_hashed):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id FROM admins WHERE id=%s AND password=%s", (admin_id, current_hashed))
        if not cur.fetchone():
            return False
        cur.execute("UPDATE admins SET password=%s WHERE id=%s", (new_hashed, admin_id))
        conn.commit()
        return True
    finally:
        cur.close(); conn.close()

# ─────────────────────────────────────────────────
# MEMBER AUTH
# ─────────────────────────────────────────────────

def get_member_by_credentials(email, hashed_password):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""SELECT m.*, p.plan_name FROM members m
                   LEFT JOIN plans p ON m.plan_id=p.id
                   WHERE m.email=%s AND m.password=%s""", (email, hashed_password))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row

def get_member_by_email(email):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT id,email FROM members WHERE email=%s", (email,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row

def register_member(data):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""INSERT INTO members (full_name,email,password,phone,date_of_birth,gender,
                   address,plan_id,join_date,end_date,status,fitness_goal)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'active',%s)""",
                (data['full_name'], data['email'], data['password'], data['phone'],
                 data['date_of_birth'], data['gender'], data.get('address',''),
                 data['plan_id'], data['join_date'], data['end_date'],
                 data.get('fitness_goal','')))
    conn.commit()
    new_id = cur.lastrowid
    cur.close(); conn.close()
    return new_id

def change_member_password(member_id, current_hashed, new_hashed):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id FROM members WHERE id=%s AND password=%s", (member_id, current_hashed))
        if not cur.fetchone():
            return False
        cur.execute("UPDATE members SET password=%s WHERE id=%s", (new_hashed, member_id))
        conn.commit()
        return True
    finally:
        cur.close(); conn.close()

# ─────────────────────────────────────────────────
# MEMBERS
# ─────────────────────────────────────────────────

def get_members(search='', status=''):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    q = """SELECT m.*, p.plan_name, t.full_name AS trainer_name
           FROM members m
           LEFT JOIN plans p ON m.plan_id=p.id
           LEFT JOIN trainers t ON m.trainer_id=t.id
           WHERE 1=1"""
    params = []
    if search:
        q += " AND (m.full_name LIKE %s OR m.email LIKE %s OR m.phone LIKE %s)"
        s = f'%{search}%'
        params += [s, s, s]
    if status:
        q += " AND m.status=%s"
        params.append(status)
    q += " ORDER BY m.created_at DESC"
    cur.execute(q, params)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_all_members():
    return get_members()

def get_member_by_id(member_id):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""SELECT m.*, p.plan_name, t.full_name AS trainer_name
                   FROM members m
                   LEFT JOIN plans p ON m.plan_id=p.id
                   LEFT JOIN trainers t ON m.trainer_id=t.id
                   WHERE m.id=%s""", (member_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row

def get_recent_members(limit=5):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""SELECT m.*, p.plan_name FROM members m
                   LEFT JOIN plans p ON m.plan_id=p.id
                   ORDER BY m.created_at DESC LIMIT %s""", (limit,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def add_member(data):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""INSERT INTO members (full_name,email,password,phone,date_of_birth,gender,
                   address,plan_id,trainer_id,join_date,end_date,status,fitness_goal)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (data['full_name'], data['email'], data.get('password', hash_password('changeme123')),
                 data['phone'], data['date_of_birth'], data['gender'],
                 data.get('address',''), data['plan_id'], data.get('trainer_id'),
                 data['join_date'], data['end_date'], data['status'],
                 data.get('fitness_goal','')))
    conn.commit()
    cur.close(); conn.close()

def update_member(member_id, data):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""UPDATE members SET full_name=%s, phone=%s, address=%s,
                   gender=%s, date_of_birth=%s, fitness_goal=%s,
                   weight=%s, height=%s, trainer_id=%s WHERE id=%s""",
                (data['full_name'], data['phone'], data.get('address',''),
                 data['gender'], data['date_of_birth'], data.get('fitness_goal',''),
                 data.get('weight'), data.get('height'), data.get('trainer_id'),
                 member_id))
    conn.commit()
    cur.close(); conn.close()

def update_member_plan(member_id, plan_id, end_date):
    """Update member plan after payment"""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""UPDATE members SET plan_id=%s, end_date=%s, status='active'
                   WHERE id=%s""", (plan_id, end_date, member_id))
    conn.commit()
    cur.close(); conn.close()

def delete_member(member_id):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM members WHERE id=%s", (member_id,))
    conn.commit()
    cur.close(); conn.close()

# ─────────────────────────────────────────────────
# PLANS
# ─────────────────────────────────────────────────

def get_all_plans():
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM plans WHERE status='active' ORDER BY price ASC")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_all_plans_with_count():
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""SELECT p.*, COUNT(m.id) AS member_count
                   FROM plans p LEFT JOIN members m ON p.id=m.plan_id AND m.status='active'
                   GROUP BY p.id ORDER BY p.price ASC""")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_plan_by_id(plan_id):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM plans WHERE id=%s", (plan_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row

def add_plan(data):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""INSERT INTO plans (plan_name,duration_months,price,description,features,status)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (data['plan_name'], data['duration_months'], data['price'],
                 data['description'], data['features'], data['status']))
    conn.commit()
    cur.close(); conn.close()

def delete_plan(plan_id):
    """
    Safely delete a plan.
    - Sets plan_id to NULL in members table first
    - Sets plan_id to NULL in payments table first
    - Then deletes the plan
    """
    conn = get_connection()
    cur  = conn.cursor()
    try:
        # Remove plan reference from members
        cur.execute("UPDATE members SET plan_id=NULL WHERE plan_id=%s", (plan_id,))
        # Remove plan reference from payments (set to first available plan or NULL)
        cur.execute("UPDATE payments SET plan_id=(SELECT id FROM plans WHERE id != %s LIMIT 1) WHERE plan_id=%s",
                    (plan_id, plan_id))
        # Now safely delete the plan
        cur.execute("DELETE FROM plans WHERE id=%s", (plan_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close(); conn.close()

def update_plan(plan_id, data):
    """Update an existing plan"""
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute("""UPDATE plans
                       SET plan_name=%s, duration_months=%s, price=%s,
                           description=%s, features=%s
                       WHERE id=%s""",
                    (data['plan_name'], data['duration_months'], data['price'],
                     data['description'], data['features'], plan_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close(); conn.close()

# ─────────────────────────────────────────────────
# TRAINERS
# ─────────────────────────────────────────────────

def get_all_trainers():
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""SELECT t.*,
                   COUNT(DISTINCT m.id) AS active_members,
                   COALESCE(AVG(f.rating),0) AS avg_rating
                   FROM trainers t
                   LEFT JOIN members m ON t.id=m.trainer_id AND m.status='active'
                   LEFT JOIN trainer_feedback f ON t.id=f.trainer_id
                   WHERE t.status='active'
                   GROUP BY t.id ORDER BY avg_rating DESC""")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_trainer_by_id(trainer_id):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM trainers WHERE id=%s", (trainer_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row

def add_trainer(data):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""INSERT INTO trainers (full_name,email,phone,specialization,experience_years,bio,status)
                   VALUES (%s,%s,%s,%s,%s,%s,'active')""",
                (data['full_name'], data['email'], data['phone'],
                 data['specialization'], data['experience_years'], data.get('bio','')))
    conn.commit()
    cur.close(); conn.close()

def delete_trainer(trainer_id):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM trainers WHERE id=%s", (trainer_id,))
    conn.commit()
    cur.close(); conn.close()

def get_trainer_performance_ranking():
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""SELECT t.id, t.full_name, t.specialization, t.experience_years,
                   COUNT(f.id) AS total_reviews,
                   ROUND(AVG(f.rating),2) AS avg_overall,
                   ROUND(AVG(f.punctuality),2) AS avg_punctuality,
                   ROUND(AVG(f.knowledge),2) AS avg_knowledge,
                   ROUND(AVG(f.motivation),2) AS avg_motivation,
                   COUNT(DISTINCT m.id) AS active_members
                   FROM trainers t
                   LEFT JOIN trainer_feedback f ON t.id=f.trainer_id
                   LEFT JOIN members m ON t.id=m.trainer_id AND m.status='active'
                   WHERE t.status='active'
                   GROUP BY t.id ORDER BY avg_overall DESC""")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_trainer_weekly_feedback(trainer_id, weeks=8):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""SELECT week_start,
                   ROUND(AVG(rating),2) AS avg_rating,
                   ROUND(AVG(punctuality),2) AS avg_punctuality,
                   ROUND(AVG(knowledge),2) AS avg_knowledge,
                   ROUND(AVG(motivation),2) AS avg_motivation,
                   COUNT(*) AS review_count
                   FROM trainer_feedback WHERE trainer_id=%s
                   GROUP BY week_start ORDER BY week_start DESC LIMIT %s""",
                (trainer_id, weeks))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

# ─────────────────────────────────────────────────
# TRAINER FEEDBACK
# ─────────────────────────────────────────────────

def add_trainer_feedback(data):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""INSERT INTO trainer_feedback
                   (member_id,trainer_id,week_start,rating,punctuality,knowledge,motivation,comments)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE
                   rating=%s, punctuality=%s, knowledge=%s, motivation=%s, comments=%s""",
                (data['member_id'], data['trainer_id'], data['week_start'],
                 data['rating'], data['punctuality'], data['knowledge'],
                 data['motivation'], data.get('comments',''),
                 data['rating'], data['punctuality'], data['knowledge'],
                 data['motivation'], data.get('comments','')))
    conn.commit()
    cur.close(); conn.close()

def get_member_feedback_given(member_id):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""SELECT f.*, t.full_name AS trainer_name
                   FROM trainer_feedback f JOIN trainers t ON f.trainer_id=t.id
                   WHERE f.member_id=%s ORDER BY f.week_start DESC""", (member_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

# ─────────────────────────────────────────────────
# MEMBER PERFORMANCE
# ─────────────────────────────────────────────────

def add_member_performance(data):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""INSERT INTO member_performance
                   (member_id,week_start,workouts_completed,workouts_planned,
                    weight_kg,cardio_minutes,strength_sessions,notes)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE
                   workouts_completed=%s, workouts_planned=%s,
                   weight_kg=%s, cardio_minutes=%s, strength_sessions=%s, notes=%s""",
                (data['member_id'], data['week_start'],
                 data['workouts_completed'], data['workouts_planned'],
                 data.get('weight_kg'), data['cardio_minutes'], data['strength_sessions'],
                 data.get('notes',''),
                 data['workouts_completed'], data['workouts_planned'],
                 data.get('weight_kg'), data['cardio_minutes'], data['strength_sessions'],
                 data.get('notes','')))
    conn.commit()
    cur.close(); conn.close()

def get_member_performance_history(member_id, weeks=12):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""SELECT * FROM member_performance
                   WHERE member_id=%s ORDER BY week_start DESC LIMIT %s""",
                (member_id, weeks))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_member_performance_summary(member_id):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""SELECT COUNT(*) AS total_weeks,
                   SUM(workouts_completed) AS total_workouts,
                   ROUND(AVG(workouts_completed/NULLIF(workouts_planned,0))*100,1) AS avg_adherence,
                   SUM(cardio_minutes) AS total_cardio,
                   SUM(strength_sessions) AS total_strength
                   FROM member_performance WHERE member_id=%s""", (member_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row

# ─────────────────────────────────────────────────
# PAYMENTS
# ─────────────────────────────────────────────────

def get_payments(search='', status='', method=''):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    q = """SELECT pay.*, m.full_name, pl.plan_name
           FROM payments pay
           JOIN members m ON pay.member_id=m.id
           JOIN plans pl ON pay.plan_id=pl.id
           WHERE 1=1"""
    params = []
    if search:
        q += " AND m.full_name LIKE %s"
        params.append(f'%{search}%')
    if status:
        q += " AND pay.status=%s"; params.append(status)
    if method:
        q += " AND pay.payment_method=%s"; params.append(method)
    q += " ORDER BY pay.payment_date DESC"
    cur.execute(q, params)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_member_payment_history(member_id):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""SELECT pay.*, pl.plan_name
                   FROM payments pay
                   JOIN plans pl ON pay.plan_id=pl.id
                   WHERE pay.member_id=%s
                   ORDER BY pay.payment_date DESC""", (member_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def add_payment(data):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""INSERT INTO payments
                   (member_id,plan_id,amount,payment_method,payment_date,
                    transaction_id,status,notes)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (data['member_id'], data['plan_id'], data['amount'],
                 data['payment_method'], data['payment_date'],
                 data.get('transaction_id',''), data['status'],
                 data.get('notes','')))
    conn.commit()
    cur.close(); conn.close()

def get_payment_stats():
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    today = datetime.now().strftime('%Y-%m-%d')
    year  = datetime.now().strftime('%Y')
    month = datetime.now().strftime('%m')
    cur.execute("""SELECT SUM(amount) AS total, COUNT(*) AS cnt 
                   FROM payments WHERE payment_date = %s""", (today,))
    t = cur.fetchone()
    cur.execute("""SELECT SUM(amount) AS total, COUNT(*) AS cnt 
                   FROM payments 
                   WHERE YEAR(payment_date) = %s AND MONTH(payment_date) = %s""", (year, month))
    m = cur.fetchone()
    cur.close(); conn.close()
    return {
        'today_revenue':   float(t['total'] or 0),
        'today_count':     t['cnt'],
        'monthly_revenue': float(m['total'] or 0),
        'monthly_count':   m['cnt'],
    }

# ─────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────

def get_dashboard_stats():
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) AS c FROM members"); total = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM members WHERE status='active'"); active = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM plans WHERE status='active'"); plans_count = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM trainers WHERE status='active'"); trainers_count = cur.fetchone()['c']
    year  = datetime.now().strftime('%Y')
    month = datetime.now().strftime('%m')
    cur.execute("""SELECT SUM(amount) AS s FROM payments 
                   WHERE YEAR(payment_date) = %s AND MONTH(payment_date) = %s""", (year, month))
    revenue = float(cur.fetchone()['s'] or 0)
    cur.execute("""SELECT COUNT(*) AS c FROM members WHERE status='active'
                   AND end_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)""")
    expiring = cur.fetchone()['c']
    cur.close(); conn.close()
    return {
        'total_members':   total,
        'active_members':  active,
        'total_plans':     plans_count,
        'total_trainers':  trainers_count,
        'monthly_revenue': revenue,
        'expiring_soon':   expiring,
    }

# ─────────────────────────────────────────────────
# ATTENDANCE
# ─────────────────────────────────────────────────

def mark_attendance(member_id, check_in_time=None, notes='', marked_by='admin'):
    conn = get_connection()
    cur  = conn.cursor()
    now  = check_in_time or datetime.now()
    cur.execute("""INSERT INTO attendance (member_id, check_in, date, notes, marked_by)
                   VALUES (%s,%s,%s,%s,%s)""",
                (member_id, now, now.strftime('%Y-%m-%d'), notes, marked_by))
    conn.commit()
    new_id = cur.lastrowid
    cur.close(); conn.close()
    return new_id

def mark_checkout(attendance_id):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT check_in FROM attendance WHERE id=%s", (attendance_id,))
    row = cur.fetchone()
    if row:
        check_out = datetime.now()
        raw_duration = int((check_out - row['check_in']).total_seconds() / 60)
        # Cap at 480 minutes (8 hours) — anything more is bad data
        duration = max(1, min(raw_duration, 480))
        cur.execute("UPDATE attendance SET check_out=%s, duration_minutes=%s WHERE id=%s",
                    (check_out, duration, attendance_id))
        conn.commit()
    cur.close(); conn.close()

def get_attendance_list(search='', date_filter='', member_id=None):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    q = """SELECT a.*, m.full_name, m.email
           FROM attendance a JOIN members m ON a.member_id=m.id WHERE 1=1"""
    params = []
    if search:
        q += " AND m.full_name LIKE %s"; params.append(f'%{search}%')
    if date_filter:
        q += " AND a.date=%s"; params.append(date_filter)
    if member_id:
        q += " AND a.member_id=%s"; params.append(member_id)
    q += " ORDER BY a.check_in DESC"
    cur.execute(q, params)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_today_attendance():
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    today = datetime.now().strftime('%Y-%m-%d')
    cur.execute("""SELECT a.*, m.full_name, m.email, p.plan_name
                   FROM attendance a JOIN members m ON a.member_id=m.id
                   LEFT JOIN plans p ON m.plan_id=p.id
                   WHERE a.date=%s ORDER BY a.check_in DESC""", (today,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_attendance_stats():
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    today = datetime.now().strftime('%Y-%m-%d')
    year  = datetime.now().strftime('%Y')
    month = datetime.now().strftime('%m')
    cur.execute("SELECT COUNT(*) AS c FROM attendance WHERE date=%s", (today,))
    today_count = cur.fetchone()['c']
    cur.execute("""SELECT COUNT(*) AS c FROM attendance
                   WHERE YEAR(date)=%s AND MONTH(date)=%s""", (year, month))
    month_count = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM attendance WHERE date=%s AND check_out IS NULL", (today,))
    currently_in = cur.fetchone()['c']
    cur.execute("""SELECT COALESCE(ROUND(AVG(CASE WHEN duration_minutes > 0
                   THEN duration_minutes END), 0), 0) AS avg_dur
                   FROM attendance
                   WHERE YEAR(date)=%s AND MONTH(date)=%s""", (year, month))
    avg_dur = cur.fetchone()['avg_dur'] or 0
    cur.close(); conn.close()
    return {'today_count': today_count, 'month_count': month_count,
            'currently_in': currently_in, 'avg_duration': int(avg_dur)}

def get_member_attendance_stats(member_id):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    year  = datetime.now().strftime('%Y')
    month = datetime.now().strftime('%m')
    today = datetime.now().strftime('%Y-%m-%d')

    # FIRST: Fix any NULL duration_minutes where check_out exists
    # Use TIMESTAMPDIFF to calculate from actual check_in/check_out times
    cur.execute("""UPDATE attendance
                   SET duration_minutes = LEAST(
                       GREATEST(TIMESTAMPDIFF(MINUTE, check_in, check_out), 1),
                       480
                   )
                   WHERE member_id=%s
                   AND check_out IS NOT NULL
                   AND (duration_minutes IS NULL OR duration_minutes <= 0)""",
                (member_id,))
    conn.commit()

    # Total visits and all-time stats
    # Use TIMESTAMPDIFF as fallback if duration_minutes is still NULL
    cur.execute("""SELECT COUNT(*) AS total_visits,
                   COALESCE(SUM(
                       CASE
                           WHEN duration_minutes BETWEEN 1 AND 480 THEN duration_minutes
                           WHEN check_out IS NOT NULL THEN
                               LEAST(GREATEST(TIMESTAMPDIFF(MINUTE, check_in, check_out),1),480)
                           ELSE 0
                       END
                   ), 0) AS total_minutes,
                   COALESCE(ROUND(AVG(
                       CASE
                           WHEN duration_minutes BETWEEN 1 AND 480 THEN duration_minutes
                           WHEN check_out IS NOT NULL THEN
                               LEAST(GREATEST(TIMESTAMPDIFF(MINUTE, check_in, check_out),1),480)
                           ELSE NULL
                       END
                   ), 0), 0) AS avg_duration,
                   MAX(date) AS last_visit
                   FROM attendance WHERE member_id=%s""", (member_id,))
    overall = cur.fetchone()

    # This month visit count
    cur.execute("""SELECT COUNT(*) AS c FROM attendance
                   WHERE member_id=%s AND YEAR(date)=%s AND MONTH(date)=%s""",
                (member_id, year, month))
    this_month = cur.fetchone()['c']

    # This month total minutes — use duration_minutes OR calculate from timestamps
    cur.execute("""SELECT COALESCE(SUM(
                       CASE
                           WHEN duration_minutes BETWEEN 1 AND 480 THEN duration_minutes
                           WHEN check_out IS NOT NULL THEN
                               LEAST(GREATEST(TIMESTAMPDIFF(MINUTE, check_in, check_out),1),480)
                           ELSE 0
                       END
                   ), 0) AS total_mins
                   FROM attendance
                   WHERE member_id=%s AND YEAR(date)=%s AND MONTH(date)=%s""",
                (member_id, year, month))
    month_mins = cur.fetchone()['total_mins']

    # This month avg session
    cur.execute("""SELECT COALESCE(ROUND(AVG(
                       CASE
                           WHEN duration_minutes BETWEEN 1 AND 480 THEN duration_minutes
                           WHEN check_out IS NOT NULL THEN
                               LEAST(GREATEST(TIMESTAMPDIFF(MINUTE, check_in, check_out),1),480)
                           ELSE NULL
                       END
                   ), 0), 0) AS avg_month
                   FROM attendance
                   WHERE member_id=%s AND YEAR(date)=%s AND MONTH(date)=%s""",
                (member_id, year, month))
    month_avg = cur.fetchone()['avg_month'] or 0

    # Currently checked in today (no checkout)
    cur.execute("""SELECT id FROM attendance
                   WHERE member_id=%s AND date=%s AND check_out IS NULL
                   ORDER BY check_in DESC LIMIT 1""", (member_id, today))
    active_checkin = cur.fetchone()
    cur.close()
    conn.close()

    total_mins_all      = int(overall['total_minutes'] or 0)
    this_month_mins_val = int(month_mins or 0)
    return {
        'total_visits':      overall['total_visits'] or 0,
        'total_minutes':     total_mins_all,
        'total_hours':       round(total_mins_all / 60, 1),
        'avg_duration':      int(overall['avg_duration'] or 0),
        'last_visit':        overall['last_visit'],
        'this_month':        this_month,
        'this_month_mins':   this_month_mins_val,
        'this_month_hours':  round(this_month_mins_val / 60, 1),
        'this_month_avg':    int(month_avg),
        'active_checkin_id': active_checkin['id'] if active_checkin else None,
    }

def get_attendance_by_week(weeks=8):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""SELECT DATE_FORMAT(date,'%%Y-%%u') AS week_key,
                   MIN(date) AS week_start, COUNT(*) AS total_visits,
                   COUNT(DISTINCT member_id) AS unique_members
                   FROM attendance GROUP BY week_key
                   ORDER BY week_key DESC LIMIT %s""", (weeks,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def delete_attendance(attendance_id):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM attendance WHERE id=%s", (attendance_id,))
    conn.commit()
    cur.close(); conn.close()

def get_member_monthly_attendance(member_id, year, month):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""SELECT date, check_in, check_out, duration_minutes FROM attendance
                   WHERE member_id=%s AND YEAR(date)=%s AND MONTH(date)=%s
                   ORDER BY date ASC""", (member_id, year, month))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

# ─────────────────────────────────────────────────
# TRAINER ATTENDANCE
# ─────────────────────────────────────────────────

def mark_trainer_attendance(trainer_id, notes=''):
    conn = get_connection()
    cur  = conn.cursor()
    now  = datetime.now()
    cur.execute("""INSERT INTO trainer_attendance (trainer_id, check_in, date, notes)
                   VALUES (%s,%s,%s,%s)""",
                (trainer_id, now, now.strftime('%Y-%m-%d'), notes))
    conn.commit()
    new_id = cur.lastrowid
    cur.close(); conn.close()
    return new_id

def mark_trainer_checkout(attendance_id):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT check_in FROM trainer_attendance WHERE id=%s", (attendance_id,))
    row = cur.fetchone()
    if row:
        check_out = datetime.now()
        duration  = int((check_out - row['check_in']).total_seconds() / 60)
        cur.execute("UPDATE trainer_attendance SET check_out=%s, duration_minutes=%s WHERE id=%s",
                    (check_out, duration, attendance_id))
        conn.commit()
    cur.close(); conn.close()

def get_trainer_attendance_list(search='', date_filter='', trainer_id=None):
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    q = """SELECT ta.*, t.full_name, t.specialization
           FROM trainer_attendance ta JOIN trainers t ON ta.trainer_id=t.id WHERE 1=1"""
    params = []
    if search:
        q += " AND t.full_name LIKE %s"; params.append(f'%{search}%')
    if date_filter:
        q += " AND ta.date=%s"; params.append(date_filter)
    if trainer_id:
        q += " AND ta.trainer_id=%s"; params.append(trainer_id)
    q += " ORDER BY ta.check_in DESC"
    cur.execute(q, params)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_today_trainer_attendance():
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    today = datetime.now().strftime('%Y-%m-%d')
    cur.execute("""SELECT ta.*, t.full_name, t.specialization
                   FROM trainer_attendance ta JOIN trainers t ON ta.trainer_id=t.id
                   WHERE ta.date=%s ORDER BY ta.check_in DESC""", (today,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_trainer_attendance_stats():
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    today = datetime.now().strftime('%Y-%m-%d')
    year  = datetime.now().strftime('%Y')
    month = datetime.now().strftime('%m')
    cur.execute("SELECT COUNT(*) AS c FROM trainer_attendance WHERE date=%s", (today,))
    today_count = cur.fetchone()['c']
    cur.execute("""SELECT COUNT(*) AS c FROM trainer_attendance
                   WHERE YEAR(date)=%s AND MONTH(date)=%s""", (year, month))
    month_count = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM trainer_attendance WHERE date=%s AND check_out IS NULL", (today,))
    currently_in = cur.fetchone()['c']
    # Avg duration - only completed sessions
    cur.execute("""SELECT COALESCE(ROUND(AVG(CASE WHEN duration_minutes > 0
                   THEN duration_minutes END), 0), 0) AS avg_dur
                   FROM trainer_attendance
                   WHERE YEAR(date)=%s AND MONTH(date)=%s""", (year, month))
    avg_dur = cur.fetchone()['avg_dur'] or 0
    # Total mins - completed sessions this month
    cur.execute("""SELECT COALESCE(SUM(duration_minutes), 0) AS total_mins
                   FROM trainer_attendance
                   WHERE YEAR(date)=%s AND MONTH(date)=%s
                   AND duration_minutes IS NOT NULL""", (year, month))
    total_mins = int(cur.fetchone()['total_mins'] or 0)
    cur.close(); conn.close()
    return {'today_count': today_count, 'month_count': month_count,
            'currently_in': currently_in, 'avg_duration': int(avg_dur),
            'total_hours': round(total_mins / 60, 1),
            'total_mins': total_mins}

def get_trainer_attendance_summary():
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    year  = datetime.now().strftime('%Y')
    month = datetime.now().strftime('%m')
    cur.execute("""SELECT t.id, t.full_name, t.specialization,
                   COUNT(ta.id) AS total_days,
                   COALESCE(SUM(CASE WHEN ta.duration_minutes IS NOT NULL THEN ta.duration_minutes ELSE 0 END), 0) AS total_minutes,
                   COALESCE(ROUND(AVG(CASE WHEN ta.duration_minutes > 0 THEN ta.duration_minutes ELSE NULL END), 0), 0) AS avg_duration
                   FROM trainers t
                   LEFT JOIN trainer_attendance ta ON t.id=ta.trainer_id
                       AND YEAR(ta.date)=%s AND MONTH(ta.date)=%s
                   WHERE t.status='active'
                   GROUP BY t.id ORDER BY total_days DESC""", (year, month))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_expired_members():
    """Get all members whose membership has expired"""
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""SELECT m.*, p.plan_name, t.full_name AS trainer_name,
                   DATEDIFF(CURDATE(), m.end_date) AS days_expired
                   FROM members m
                   LEFT JOIN plans p ON m.plan_id=p.id
                   LEFT JOIN trainers t ON m.trainer_id=t.id
                   WHERE m.end_date < CURDATE()
                   ORDER BY m.end_date DESC""")
    rows = cur.fetchall()
    # Auto-update status to expired
    cur.execute("UPDATE members SET status='expired' WHERE end_date < CURDATE() AND status='active'")
    conn.commit()
    cur.close(); conn.close()
    return rows

def get_trainer_all_feedback(trainer_id):
    """Get all individual feedback entries for a trainer"""
    conn = get_connection()
    cur  = conn.cursor(dictionary=True)
    cur.execute("""SELECT f.*, m.full_name AS member_name
                   FROM trainer_feedback f
                   JOIN members m ON f.member_id=m.id
                   WHERE f.trainer_id=%s
                   ORDER BY f.week_start DESC""", (trainer_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def delete_trainer_attendance(attendance_id):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM trainer_attendance WHERE id=%s", (attendance_id,))
    conn.commit()
    cur.close(); conn.close()