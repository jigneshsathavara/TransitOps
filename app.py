import os
import smtplib
import sqlite3
import csv
import io
from email.message import EmailMessage
from urllib.parse import urlparse
from flask import Flask, request, jsonify, send_file, send_from_directory, redirect, make_response
import mysql.connector
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
from functools import wraps

load_dotenv()

app = Flask(__name__)

#dbconfig
def get_db_config():
    db_uri = os.getenv('DB_URI', '').strip()
    if db_uri:
        parsed = urlparse(db_uri)
        if parsed.scheme and parsed.hostname:
            return {
                'host': parsed.hostname,
                'port': parsed.port or 3306,
                'user': parsed.username or os.getenv('DB_USER', 'root'),
                'password': parsed.password or os.getenv('DB_PASSWORD', ''),
                'database': parsed.path.lstrip('/') or os.getenv('DB_NAME', 'transitops'),
                'autocommit': True
            }

    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'transitops'),
        'autocommit': True
    }


DB_CONFIG = get_db_config()

DB_SQLITE_PATH = os.getenv('DB_SQLITE_PATH', os.path.join(os.path.dirname(__file__), 'contact_requests.db'))
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'sathavarajignesh2@gmal.com')
APP_PASSWORD = os.getenv('APP_PASSWORD', 'wcyu pmjg vlzr ljvw')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Demo accounts with roles
DEMO_ACCOUNTS = {
    'fleetmanager@transitops.com': {'password': 'Fleet@123', 'role': 'Fleet Manager'},
    'dispatcher@transitops.com': {'password': 'Dispatcher@123', 'role': 'Dispatcher'},
    'safetyofficer@transitops.com': {'password': 'Safety@123', 'role': 'Safety Officer'},
    'financialanalyst@transitops.com': {'password': 'Finance@123', 'role': 'Financial Analyst'}
}


def is_authenticated():
    return request.cookies.get('transitops_auth') == '1'


def get_user_role():
    return request.cookies.get('transitops_role', 'Dispatcher')


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_authenticated():
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not is_authenticated():
                return jsonify({'success': False, 'error': 'Unauthorized'}), 401
            user_role = get_user_role()
            if roles and user_role not in roles:
                return jsonify({'success': False, 'error': f'Forbidden: {user_role} cannot access this'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        print(f"Database connection error: {e}")
        return None


def init_sqlite_db():
    conn = sqlite3.connect(DB_SQLITE_PATH)
    conn.execute(
        '''CREATE TABLE IF NOT EXISTS contact_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            company TEXT NOT NULL,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''
    )
    conn.commit()
    conn.close()


def save_contact(name, email, company, message):
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute(
                'INSERT INTO contact_requests (full_name, email, company, message) VALUES (%s, %s, %s, %s)',
                (name, email, company, message)
            )
            connection.commit()
            cursor.close()
            connection.close()
            return {'backend': 'mysql'}
    except Exception as exc:
        print(f"MySQL contact save failed: {exc}")

    init_sqlite_db()
    conn = sqlite3.connect(DB_SQLITE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO contact_requests (full_name, email, company, message) VALUES (?, ?, ?, ?)',
        (name, email, company, message)
    )
    conn.commit()
    conn.close()
    return {'backend': 'sqlite'}


def send_admin_email(name, email, company, message):
    msg = EmailMessage()
    msg['Subject'] = 'New TransitOps Contact Request'
    msg['From'] = ADMIN_EMAIL
    msg['To'] = ADMIN_EMAIL
    msg.set_content(
        f'Name: {name}\nEmail: {email}\nCompany: {company}\n\nMessage:\n{message or "No message provided"}'
    )
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(ADMIN_EMAIL, APP_PASSWORD)
        smtp.send_message(msg)


def send_license_expiry_reminder(driver_email, driver_name, expiry_date):
    msg = EmailMessage()
    msg['Subject'] = f'License Expiry Reminder - {driver_name}'
    msg['From'] = ADMIN_EMAIL
    msg['To'] = driver_email
    msg.set_content(
        f'Dear {driver_name},\n\nYour driving license will expire on {expiry_date}. '
        'Please renew it before the expiry date to continue operations.\n\nRegards,\nTransitOps Team'
    )
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(ADMIN_EMAIL, APP_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending license reminder: {e}")
        return False


# ===== AUTHENTICATION =====

@app.route('/login', methods=['POST'])
def login():
    email = (request.form.get('email') or '').strip().lower()
    password = (request.form.get('password') or '').strip()

    account = DEMO_ACCOUNTS.get(email)
    if account and account['password'] == password:
        response = make_response(redirect('/dashboard.html'))
        response.set_cookie('transitops_auth', '1', max_age=3600, path='/')
        response.set_cookie('transitops_role', account['role'], max_age=3600, path='/')
        response.set_cookie('transitops_email', email, max_age=3600, path='/')
        return response

    return redirect('/login.html?error=1')


@app.route('/logout')
def logout():
    response = make_response(redirect('/login.html'))
    response.set_cookie('transitops_auth', '', max_age=0, path='/')
    response.set_cookie('transitops_role', '', max_age=0, path='/')
    response.set_cookie('transitops_email', '', max_age=0, path='/')
    return response


@app.route('/api/auth/current', methods=['GET'])
@require_auth
def get_current_user():
    return jsonify({
        'success': True,
        'email': request.cookies.get('transitops_email'),
        'role': get_user_role()
    })


# ===== DASHBOARD KPIs =====

@app.route('/api/dashboard/kpis', methods=['GET'])
@require_auth
def get_dashboard_kpis():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Active Vehicles
        cursor.execute("SELECT COUNT(*) as count FROM vehicles WHERE status != 'Retired'")
        active_vehicles = cursor.fetchone()['count']
        
        # Available Vehicles
        cursor.execute("SELECT COUNT(*) as count FROM vehicles WHERE status = 'Available'")
        available_vehicles = cursor.fetchone()['count']
        
        # Vehicles in Maintenance
        cursor.execute("SELECT COUNT(*) as count FROM vehicles WHERE status = 'In Shop'")
        vehicles_in_maintenance = cursor.fetchone()['count']
        
        # Active Trips
        cursor.execute("SELECT COUNT(*) as count FROM trips WHERE status IN ('Dispatched')")
        active_trips = cursor.fetchone()['count']
        
        # Pending Trips
        cursor.execute("SELECT COUNT(*) as count FROM trips WHERE status IN ('Draft', 'Awaiting driver')")
        pending_trips = cursor.fetchone()['count']
        
        # Drivers On Duty
        cursor.execute("SELECT COUNT(*) as count FROM drivers WHERE status = 'On Trip'")
        drivers_on_duty = cursor.fetchone()['count']
        
        # Fleet Utilization
        cursor.execute("SELECT COUNT(*) as total FROM vehicles WHERE status != 'Retired'")
        total = cursor.fetchone()['total']
        fleet_util = ((total - available_vehicles) / total * 100) if total > 0 else 0
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'active_vehicles': active_vehicles,
            'available_vehicles': available_vehicles,
            'vehicles_in_maintenance': vehicles_in_maintenance,
            'active_trips': active_trips,
            'pending_trips': pending_trips,
            'drivers_on_duty': drivers_on_duty,
            'fleet_utilization': round(fleet_util, 2)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== VEHICLE REGISTRY (CRUD) =====

@app.route('/api/vehicles', methods=['GET'])
@require_auth
def get_vehicles():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        status = request.args.get('status')
        vehicle_type = request.args.get('type')
        region = request.args.get('region')
        search = request.args.get('search', '').strip()
        
        sql = "SELECT * FROM vehicles WHERE 1=1"
        params = []
        
        if status:
            sql += " AND status = %s"
            params.append(status)
        if vehicle_type:
            sql += " AND vehicle_type = %s"
            params.append(vehicle_type)
        if region:
            sql += " AND region = %s"
            params.append(region)
        if search:
            sql += " AND (registration_number LIKE %s OR vehicle_name LIKE %s)"
            params.extend([f"%{search}%", f"%{search}%"])
        
        sql += " ORDER BY registration_number"
        cursor.execute(sql, params)
        vehicles = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'data': vehicles})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/vehicles', methods=['POST'])
@require_role('Fleet Manager', 'Dispatcher')
def create_vehicle():
    try:
        data = request.get_json()
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            INSERT INTO vehicles 
            (registration_number, vehicle_name, vehicle_type, region, max_load_capacity, odometer, acquisition_cost, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data['registration_number'],
            data['vehicle_name'],
            data['vehicle_type'],
            data.get('region', 'Central'),
            data['max_load_capacity'],
            data.get('odometer', 0),
            data['acquisition_cost'],
            data.get('status', 'Available')
        ))
        
        connection.commit()
        vehicle_id = cursor.lastrowid
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'id': vehicle_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/vehicles/<int:vehicle_id>', methods=['PUT'])
@require_role('Fleet Manager', 'Dispatcher')
def update_vehicle(vehicle_id):
    try:
        data = request.get_json()
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            UPDATE vehicles 
            SET registration_number=%s, vehicle_name=%s, vehicle_type=%s, region=%s,
                max_load_capacity=%s, odometer=%s, acquisition_cost=%s, status=%s
            WHERE id=%s
        """, (
            data['registration_number'],
            data['vehicle_name'],
            data['vehicle_type'],
            data.get('region', 'Central'),
            data['max_load_capacity'],
            data.get('odometer', 0),
            data['acquisition_cost'],
            data.get('status', 'Available'),
            vehicle_id
        ))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/vehicles/<int:vehicle_id>', methods=['DELETE'])
@require_role('Fleet Manager')
def delete_vehicle(vehicle_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM vehicles WHERE id=%s", (vehicle_id,))
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== DRIVER MANAGEMENT (CRUD) =====

@app.route('/api/drivers', methods=['GET'])
@require_auth
def get_drivers():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        status = request.args.get('status')
        search = request.args.get('search', '').strip()
        
        sql = "SELECT * FROM drivers WHERE 1=1"
        params = []
        
        if status:
            sql += " AND status = %s"
            params.append(status)
        if search:
            sql += " AND (name LIKE %s OR license_number LIKE %s)"
            params.extend([f"%{search}%", f"%{search}%"])
        
        sql += " ORDER BY name"
        cursor.execute(sql, params)
        drivers = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'data': drivers})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/drivers', methods=['POST'])
@require_role('Fleet Manager', 'Safety Officer')
def create_driver():
    try:
        data = request.get_json()
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            INSERT INTO drivers 
            (name, license_number, license_category, license_expiry_date, contact_number, safety_score, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            data['name'],
            data['license_number'],
            data['license_category'],
            data['license_expiry_date'],
            data['contact_number'],
            data.get('safety_score', 5.0),
            'Available'
        ))
        
        connection.commit()
        driver_id = cursor.lastrowid
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'id': driver_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/drivers/<int:driver_id>', methods=['PUT'])
@require_role('Fleet Manager', 'Safety Officer')
def update_driver(driver_id):
    try:
        data = request.get_json()
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            UPDATE drivers 
            SET name=%s, license_number=%s, license_category=%s, 
                license_expiry_date=%s, contact_number=%s, safety_score=%s, status=%s
            WHERE id=%s
        """, (
            data['name'],
            data['license_number'],
            data['license_category'],
            data['license_expiry_date'],
            data['contact_number'],
            data.get('safety_score', 5.0),
            data.get('status', 'Available'),
            driver_id
        ))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/drivers/<int:driver_id>', methods=['DELETE'])
@require_role('Fleet Manager')
def delete_driver(driver_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM drivers WHERE id=%s", (driver_id,))
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== TRIP MANAGEMENT =====

@app.route('/api/trips', methods=['GET'])
@require_auth
def get_trips():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        status = request.args.get('status')
        
        sql = """
            SELECT t.*, v.registration_number, d.name as driver_name
            FROM trips t
            LEFT JOIN vehicles v ON t.vehicle_id = v.id
            LEFT JOIN drivers d ON t.driver_id = d.id
            WHERE 1=1
        """
        params = []
        
        if status:
            sql += " AND t.status = %s"
            params.append(status)
        
        sql += " ORDER BY t.created_at DESC"
        cursor.execute(sql, params)
        trips = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'data': trips})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/trips', methods=['POST'])
@require_role('Dispatcher', 'Fleet Manager')
def create_trip():
    try:
        data = request.get_json()
        
        vehicle_id = int(data['vehicle_id'])
        driver_id = int(data['driver_id'])
        cargo_weight = int(data.get('cargo_weight', 0))
        planned_distance = int(data.get('planned_distance', 0))
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Validate cargo weight
        cursor.execute("SELECT max_load_capacity, status FROM vehicles WHERE id=%s", (vehicle_id,))
        vehicle = cursor.fetchone()
        
        if not vehicle:
            return jsonify({'success': False, 'error': 'Vehicle not found'}), 404
        if vehicle['status'] != 'Available':
            return jsonify({'success': False, 'error': 'Vehicle is not available for dispatch'}), 400
        if cargo_weight > vehicle['max_load_capacity']:
            return jsonify({
                'success': False, 
                'error': f"Cargo weight exceeds capacity. Max: {vehicle['max_load_capacity']}kg"
            }), 400
        
        # Validate driver license and availability
        cursor.execute("""
            SELECT status, license_expiry_date FROM drivers 
            WHERE id=%s AND license_expiry_date >= CURDATE()
        """, (driver_id,))
        driver = cursor.fetchone()
        
        if not driver or driver['status'] != 'Available':
            return jsonify({'success': False, 'error': 'Driver not available or license expired'}), 400
        if driver['status'] == 'Suspended':
            return jsonify({'success': False, 'error': 'Driver is suspended'}), 400
        
        cursor.execute("""
            INSERT INTO trips 
            (source, destination, vehicle_id, driver_id, cargo_weight, planned_distance, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            data['source'],
            data['destination'],
            vehicle_id,
            driver_id,
            cargo_weight,
            planned_distance,
            'Draft'
        ))
        
        connection.commit()
        trip_id = cursor.lastrowid
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'id': trip_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/trips/<int:trip_id>/dispatch', methods=['POST'])
@require_role('Dispatcher', 'Fleet Manager')
def dispatch_trip(trip_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT status, vehicle_id, driver_id FROM trips WHERE id=%s", (trip_id,))
        trip = cursor.fetchone()
        if not trip:
            return jsonify({'success': False, 'error': 'Trip not found'}), 404
        if trip['status'] != 'Draft':
            return jsonify({'success': False, 'error': 'Only draft trips can be dispatched'}), 400
        
        cursor.execute("SELECT status FROM vehicles WHERE id=%s", (trip['vehicle_id'],))
        vehicle = cursor.fetchone()
        if not vehicle or vehicle['status'] != 'Available':
            return jsonify({'success': False, 'error': 'Vehicle is not available for dispatch'}), 400
        
        cursor.execute("SELECT status, license_expiry_date FROM drivers WHERE id=%s", (trip['driver_id'],))
        driver = cursor.fetchone()
        if not driver or driver['status'] != 'Available' or driver['license_expiry_date'] < datetime.now().date():
            return jsonify({'success': False, 'error': 'Driver is not available for dispatch'}), 400
        
        cursor.execute("UPDATE trips SET status='Dispatched' WHERE id=%s", (trip_id,))
        cursor.execute("UPDATE vehicles SET status='On Trip' WHERE id=%s", (trip['vehicle_id'],))
        cursor.execute("UPDATE drivers SET status='On Trip' WHERE id=%s", (trip['driver_id'],))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/trips/<int:trip_id>/complete', methods=['POST'])
@require_role('Dispatcher', 'Fleet Manager')
def complete_trip(trip_id):
    try:
        data = request.get_json()
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Get trip details
        cursor.execute("SELECT vehicle_id, driver_id, cargo_weight FROM trips WHERE id=%s", (trip_id,))
        trip = cursor.fetchone()
        
        # Update trip
        cursor.execute("""
            UPDATE trips 
            SET status='Completed', actual_distance=%s 
            WHERE id=%s
        """, (data.get('actual_distance', 0), trip_id))
        
        # Restore vehicle & driver status
        cursor.execute("UPDATE vehicles SET status='Available' WHERE id=%s", (trip['vehicle_id'],))
        cursor.execute("UPDATE drivers SET status='Available' WHERE id=%s", (trip['driver_id'],))
        
        # Record fuel log if provided
        if data.get('fuel_liters'):
            cursor.execute("""
                INSERT INTO fuel_logs (vehicle_id, liters_filled, cost, fuel_date)
                VALUES (%s, %s, %s, CURDATE())
            """, (trip['vehicle_id'], data['fuel_liters'], data.get('fuel_cost', 0)))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/trips/<int:trip_id>/cancel', methods=['POST'])
@require_role('Dispatcher', 'Fleet Manager')
def cancel_trip(trip_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT vehicle_id, driver_id FROM trips WHERE id=%s", (trip_id,))
        trip = cursor.fetchone()
        
        cursor.execute("UPDATE trips SET status='Cancelled' WHERE id=%s", (trip_id,))
        cursor.execute("UPDATE vehicles SET status='Available' WHERE id=%s", (trip['vehicle_id'],))
        cursor.execute("UPDATE drivers SET status='Available' WHERE id=%s", (trip['driver_id'],))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== MAINTENANCE =====

@app.route('/api/maintenance', methods=['GET'])
@require_auth
def get_maintenance():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT m.*, v.registration_number 
            FROM maintenance_logs m
            LEFT JOIN vehicles v ON m.vehicle_id = v.id
            ORDER BY m.created_at DESC
        """)
        maintenance = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'data': maintenance})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/maintenance', methods=['POST'])
@require_role('Fleet Manager', 'Safety Officer')
def create_maintenance():
    try:
        data = request.get_json()
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            INSERT INTO maintenance_logs 
            (vehicle_id, maintenance_type, description, cost, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data['vehicle_id'],
            data['maintenance_type'],
            data.get('description', ''),
            data['cost'],
            'In Progress'
        ))
        
        # Set vehicle status to In Shop
        cursor.execute("UPDATE vehicles SET status='In Shop' WHERE id=%s", (data['vehicle_id'],))
        
        connection.commit()
        maintenance_id = cursor.lastrowid
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'id': maintenance_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/maintenance/<int:maintenance_id>/close', methods=['POST'])
@require_role('Fleet Manager', 'Safety Officer')
def close_maintenance(maintenance_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT vehicle_id FROM maintenance_logs WHERE id=%s", (maintenance_id,))
        maintenance = cursor.fetchone()
        if not maintenance:
            return jsonify({'success': False, 'error': 'Maintenance record not found'}), 404
        
        cursor.execute("UPDATE maintenance_logs SET status='Closed', end_date=NOW() WHERE id=%s", (maintenance_id,))
        cursor.execute(
            "UPDATE vehicles SET status = CASE WHEN status='Retired' THEN 'Retired' ELSE 'Available' END WHERE id=%s",
            (maintenance['vehicle_id'],)
        )
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== FUEL & EXPENSES =====

@app.route('/api/fuel', methods=['GET'])
@require_auth
def get_fuel_logs():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        vehicle_id = request.args.get('vehicle_id')
        
        sql = "SELECT * FROM fuel_logs WHERE 1=1"
        params = []
        
        if vehicle_id:
            sql += " AND vehicle_id=%s"
            params.append(vehicle_id)
        
        sql += " ORDER BY fuel_date DESC"
        cursor.execute(sql, params)
        fuel_logs = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'data': fuel_logs})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/fuel', methods=['POST'])
@require_role('Dispatcher', 'Fleet Manager')
def create_fuel_log():
    try:
        data = request.get_json()
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            INSERT INTO fuel_logs (vehicle_id, liters_filled, cost, fuel_date)
            VALUES (%s, %s, %s, %s)
        """, (
            data['vehicle_id'],
            data['liters_filled'],
            data['cost'],
            data.get('fuel_date', datetime.now().date())
        ))
        
        connection.commit()
        fuel_id = cursor.lastrowid
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'id': fuel_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/expenses', methods=['GET'])
@require_auth
def get_expenses():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM expenses ORDER BY expense_date DESC")
        expenses = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'data': expenses})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/expenses', methods=['POST'])
@require_role('Financial Analyst', 'Fleet Manager')
def create_expense():
    try:
        data = request.get_json()
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            INSERT INTO expenses (vehicle_id, expense_type, amount, description, expense_date)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data['vehicle_id'],
            data['expense_type'],
            data['amount'],
            data.get('description', ''),
            data.get('expense_date', datetime.now().date())
        ))
        
        connection.commit()
        expense_id = cursor.lastrowid
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'id': expense_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== REPORTS & ANALYTICS =====

@app.route('/api/analytics/report', methods=['GET'])
@require_auth
def get_analytics_report():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Vehicle analytics
        cursor.execute("""
            SELECT 
                v.id,
                v.registration_number,
                v.vehicle_name,
                COUNT(DISTINCT t.id) as trips_completed,
                SUM(COALESCE(t.actual_distance, 0)) as total_distance,
                SUM(f.liters_filled) as total_fuel_liters,
                SUM(f.cost) as total_fuel_cost,
                (SUM(COALESCE(t.actual_distance, 0)) / NULLIF(SUM(f.liters_filled), 0)) as fuel_efficiency,
                SUM(f.cost) + SUM(COALESCE(m.cost, 0)) + SUM(COALESCE(e.amount, 0)) as operational_cost,
                v.acquisition_cost,
                ((SUM(COALESCE(t.actual_distance, 0)) * 50) - (SUM(f.cost) + SUM(COALESCE(m.cost, 0)))) / NULLIF(v.acquisition_cost, 0) as roi
            FROM vehicles v
            LEFT JOIN trips t ON v.id = t.vehicle_id AND t.status = 'Completed'
            LEFT JOIN fuel_logs f ON v.id = f.vehicle_id
            LEFT JOIN maintenance_logs m ON v.id = m.vehicle_id
            LEFT JOIN expenses e ON v.id = e.vehicle_id
            GROUP BY v.id
            ORDER BY v.registration_number
        """)
        analytics = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'data': analytics})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analytics/dashboard', methods=['GET'])
@require_auth
def get_dashboard_analytics():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) as total, status FROM vehicles GROUP BY status")
        vehicle_stats = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) as total, status FROM drivers GROUP BY status")
        driver_stats = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) as total, status FROM trips GROUP BY status")
        trip_stats = cursor.fetchall()
        
        cursor.execute("SELECT v.registration_number, SUM(f.liters_filled) as total_liters, SUM(f.cost) as total_cost FROM fuel_logs f JOIN vehicles v ON f.vehicle_id = v.id GROUP BY v.id")
        fuel_data = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) as total FROM vehicles WHERE status='Available'")
        available_vehicles = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM vehicles")
        total_vehicles = cursor.fetchone()['total']
        fleet_utilization = (total_vehicles - available_vehicles) / total_vehicles * 100 if total_vehicles > 0 else 0
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'vehicle_stats': vehicle_stats,
            'driver_stats': driver_stats,
            'trip_stats': trip_stats,
            'fuel_data': fuel_data,
            'fleet_utilization': round(fleet_utilization, 2)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/vehicles/search', methods=['GET'])
@require_auth
def search_vehicles():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = request.args.get('q', '')
        status = request.args.get('status', '')
        vehicle_type = request.args.get('type', '')
        region = request.args.get('region', '')
        
        sql = "SELECT * FROM vehicles WHERE 1=1"
        params = []
        
        if query:
            sql += " AND (registration_number LIKE %s OR vehicle_name LIKE %s)"
            params.extend([f"%{query}%", f"%{query}%"])
        if status:
            sql += " AND status = %s"
            params.append(status)
        if vehicle_type:
            sql += " AND vehicle_type = %s"
            params.append(vehicle_type)
        if region:
            sql += " AND region = %s"
            params.append(region)
        
        cursor.execute(sql, params)
        vehicles = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'data': vehicles})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/drivers/search', methods=['GET'])
@require_auth
def search_drivers():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = request.args.get('q', '')
        status = request.args.get('status', '')
        
        sql = "SELECT * FROM drivers WHERE 1=1"
        params = []
        
        if query:
            sql += " AND (name LIKE %s OR license_number LIKE %s)"
            params.extend([f"%{query}%", f"%{query}%"])
        if status:
            sql += " AND status = %s"
            params.append(status)
        
        cursor.execute(sql, params)
        drivers = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'data': drivers})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/documents/vehicle/<int:vehicle_id>', methods=['POST'])
@require_auth
def upload_vehicle_document(vehicle_id):
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        file = request.files['file']
        document_type = request.form.get('type', 'General')
        expiry_date = request.form.get('expiry_date', None)
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        filename = f"vehicle_{vehicle_id}_{datetime.now().timestamp()}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO vehicle_documents (vehicle_id, document_type, document_path, expiry_date) VALUES (%s, %s, %s, %s)",
            (vehicle_id, document_type, filepath, expiry_date)
        )
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'success': True, 'message': 'Document uploaded successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/documents/driver/<int:driver_id>', methods=['POST'])
@require_auth
def upload_driver_document(driver_id):
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        file = request.files['file']
        document_type = request.form.get('type', 'License')
        expiry_date = request.form.get('expiry_date', None)
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        filename = f"driver_{driver_id}_{datetime.now().timestamp()}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO driver_documents (driver_id, document_type, document_path, expiry_date) VALUES (%s, %s, %s, %s)",
            (driver_id, document_type, filepath, expiry_date)
        )
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'success': True, 'message': 'Document uploaded successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/reminders/check-expiring-licenses', methods=['POST'])
@require_auth
def check_expiring_licenses():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        expiry_threshold = datetime.now() + timedelta(days=30)
        cursor.execute(
            "SELECT id, name, license_expiry_date FROM drivers WHERE license_expiry_date <= %s AND license_expiry_date > %s",
            (expiry_threshold.date(), datetime.now().date())
        )
        expiring_drivers = cursor.fetchall()
        reminders_sent = 0
        for driver in expiring_drivers:
            if send_license_expiry_reminder('admin@transitops.com', driver['name'], driver['license_expiry_date']):
                cursor.execute(
                    "INSERT INTO email_reminders (recipient_email, reminder_type, entity_id, entity_type) VALUES (%s, %s, %s, %s)",
                    ('admin@transitops.com', 'license_expiry', driver['id'], 'driver')
                )
                reminders_sent += 1
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'success': True, 'reminders_sent': reminders_sent})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/report', methods=['POST'])
@require_auth
def export_report():
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors

        report_type = request.json.get('type', 'fleet')
        filename = f"TransitOps_{report_type}_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#1e40af'), spaceAfter=30, alignment=1)
        story.append(Paragraph(f"TransitOps {report_type.title()} Report", title_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        if report_type == 'fleet':
            cursor.execute("SELECT COUNT(*) as total FROM vehicles")
            total_vehicles = cursor.fetchone()['total']
            cursor.execute("SELECT COUNT(*) as total FROM vehicles WHERE status='Available'")
            available = cursor.fetchone()['total']
            story.append(Paragraph("Fleet Overview", styles['Heading2']))
            data = [['Metric', 'Value'], ['Total Vehicles', str(total_vehicles)], ['Available Vehicles', str(available)], ['In Service', str(total_vehicles - available)], ['Utilization Rate', f"{(total_vehicles - available) / total_vehicles * 100:.2f}%"]]
        elif report_type == 'drivers':
            cursor.execute("SELECT COUNT(*) as total FROM drivers")
            total_drivers = cursor.fetchone()['total']
            cursor.execute("SELECT COUNT(*) as total FROM drivers WHERE status='Available'")
            available = cursor.fetchone()['total']
            story.append(Paragraph("Driver Overview", styles['Heading2']))
            data = [['Metric', 'Value'], ['Total Drivers', str(total_drivers)], ['Available Drivers', str(available)], ['On Duty', str(total_drivers - available)]]
        else:
            cursor.execute("SELECT COUNT(*) as total FROM trips WHERE status='Completed'")
            completed_trips = cursor.fetchone()['total']
            cursor.execute("SELECT SUM(actual_distance) as total FROM trips WHERE status='Completed'")
            total_distance = cursor.fetchone()['total'] or 0
            story.append(Paragraph("Operations Overview", styles['Heading2']))
            data = [['Metric', 'Value'], ['Completed Trips', str(completed_trips)], ['Total Distance (km)', str(total_distance)], ['Avg Distance/Trip', f"{total_distance / completed_trips if completed_trips > 0 else 0:.2f}"]]
        table = Table(data)
        table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 12), ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
        story.append(table)
        cursor.close()
        connection.close()
        doc.build(story)
        return send_file(filepath, as_attachment=True, download_name=filename, mimetype='application/pdf')
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/contact', methods=['POST'])
def contact():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip()
    company = (data.get('company') or '').strip()
    message = (data.get('message') or '').strip()
    if not name or not email or not company:
        return jsonify({'success': False, 'message': 'Please fill all required fields.'}), 400
    save_result = save_contact(name, email, company, message)
    try:
        send_admin_email(name, email, company, message)
        return jsonify({'success': True, 'message': f'Your request was saved and the admin has been notified. Storage: {save_result["backend"]}.'})
    except Exception as exc:
        return jsonify({'success': True, 'message': f'Your request was saved successfully. Storage: {save_result["backend"]}. Email delivery failed: {exc}'}), 200


@app.route('/api/export/csv', methods=['POST'])
@require_auth
def export_csv():
    try:
        data = request.get_json()
        export_type = data.get('type', 'vehicles')
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        if export_type == 'vehicles':
            cursor.execute("SELECT * FROM vehicles ORDER BY registration_number")
            rows = cursor.fetchall()
            columns = ['id', 'registration_number', 'vehicle_name', 'vehicle_type', 'max_load_capacity', 'odometer', 'acquisition_cost', 'status']
            
        elif export_type == 'drivers':
            cursor.execute("SELECT * FROM drivers ORDER BY name")
            rows = cursor.fetchall()
            columns = ['id', 'name', 'license_number', 'license_category', 'license_expiry_date', 'contact_number', 'safety_score', 'status']
            
        elif export_type == 'trips':
            cursor.execute("""
                SELECT t.*, v.registration_number, d.name as driver_name 
                FROM trips t
                LEFT JOIN vehicles v ON t.vehicle_id = v.id
                LEFT JOIN drivers d ON t.driver_id = d.id
                ORDER BY t.created_at DESC
            """)
            rows = cursor.fetchall()
            columns = ['id', 'source', 'destination', 'registration_number', 'driver_name', 'cargo_weight', 'planned_distance', 'actual_distance', 'status']
            
        else:  # analytics
            cursor.execute("""
                SELECT 
                    v.registration_number,
                    v.vehicle_name,
                    COUNT(DISTINCT t.id) as trips,
                    SUM(COALESCE(t.actual_distance, 0)) as distance,
                    SUM(f.liters_filled) as fuel_liters,
                    SUM(f.cost) as fuel_cost,
                    SUM(f.cost) + SUM(COALESCE(m.cost, 0)) as operational_cost
                FROM vehicles v
                LEFT JOIN trips t ON v.id = t.vehicle_id AND t.status = 'Completed'
                LEFT JOIN fuel_logs f ON v.id = f.vehicle_id
                LEFT JOIN maintenance_logs m ON v.id = m.vehicle_id
                GROUP BY v.id
            """)
            rows = cursor.fetchall()
            columns = ['registration_number', 'vehicle_name', 'trips', 'distance', 'fuel_liters', 'fuel_cost', 'operational_cost']
        
        # Create CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        
        for row in rows:
            row_dict = {col: row.get(col, '') for col in columns}
            writer.writerow(row_dict)
        
        cursor.close()
        connection.close()
        
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'transitops_{export_type}_{datetime.now().strftime("%Y%m%d")}.csv'
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== STATIC FILES =====

@app.route('/')
def index():
    return send_file('login.html')


@app.route('/dashboard.html')
def dashboard():
    if not is_authenticated():
        return redirect('/login.html')
    return send_file('dashboard.html')


@app.route('/<path:filename>')
def serve_static(filename):
    if os.path.exists(filename):
        return send_from_directory('.', filename)
    return 'Not found', 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 3000)), debug=True)
