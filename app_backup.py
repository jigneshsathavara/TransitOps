import os
import smtplib
import sqlite3
from email.message import EmailMessage
from flask import Flask, request, jsonify, send_file, send_from_directory, redirect, make_response
import mysql.connector
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json

load_dotenv()

app = Flask(__name__)

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'transitops'),
    'autocommit': True
}

DB_SQLITE_PATH = os.getenv('DB_SQLITE_PATH', os.path.join(os.path.dirname(__file__), 'contact_requests.db'))
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'sathavarajignesh2@gmal.com')
APP_PASSWORD = os.getenv('APP_PASSWORD', 'wcyu pmjg vlzr ljvw')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def is_authenticated():
    return request.cookies.get('transitops_auth') == '1'


@app.before_request
def require_login():
    allowed_paths = {'/', '/login.html', '/login', '/styles.css', '/script.js', '/favicon.ico', '/api/contact'}
    if request.path in allowed_paths:
        return None
    if request.path == '/logout':
        return None
    if request.path.startswith('/api/'):
        return None
    if request.path.endswith(('.css', '.js', '.png', '.jpg', '.jpeg', '.svg', '.webp')):
        return None
    if request.path in {'/login', '/login.html'}:
        return None
    if request.path == '/dashboard.html' and not is_authenticated():
        return redirect('/login.html')
    if not is_authenticated():
        return redirect('/login.html')


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
        connection = mysql.connector.connect(**DB_CONFIG)
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
        init_sqlite_db()
        conn = sqlite3.connect(DB_SQLITE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO contact_requests (full_name, email, company, message) VALUES (?, ?, ?, ?)',
            (name, email, company, message)
        )
        conn.commit()
        conn.close()
        return {'backend': 'sqlite', 'fallback_reason': str(exc)}


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
    """Send email reminder for expiring driver license"""
    msg = EmailMessage()
    msg['Subject'] = f'License Expiry Reminder - {driver_name}'
    msg['From'] = ADMIN_EMAIL
    msg['To'] = driver_email
    msg.set_content(
        f'Dear {driver_name},\n\nYour driving license will expire on {expiry_date}. '
        f'Please renew it before the expiry date to continue operations.\n\nRegards,\nTransitOps Team'
    )
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(ADMIN_EMAIL, APP_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending license reminder: {e}")
        return False


def get_db_connection():
    """Get database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        print(f"Database connection error: {e}")
        return None


# ===== Analytics APIs =====

@app.route('/api/analytics/dashboard', methods=['GET'])
def get_dashboard_analytics():
    """Get dashboard KPIs and analytics data"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Get vehicle statistics
        cursor.execute("SELECT COUNT(*) as total, status FROM vehicles GROUP BY status")
        vehicle_stats = cursor.fetchall()
        
        # Get driver statistics
        cursor.execute("SELECT COUNT(*) as total, status FROM drivers GROUP BY status")
        driver_stats = cursor.fetchall()
        
        # Get trip statistics
        cursor.execute("SELECT COUNT(*) as total, status FROM trips GROUP BY status")
        trip_stats = cursor.fetchall()
        
        # Get fuel consumption data
        cursor.execute("""
            SELECT v.registration_number, SUM(f.liters_filled) as total_liters, SUM(f.cost) as total_cost
            FROM fuel_logs f
            JOIN vehicles v ON f.vehicle_id = v.id
            GROUP BY v.id
        """)
        fuel_data = cursor.fetchall()
        
        # Calculate fleet utilization
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


@app.route('/api/analytics/vehicles', methods=['GET'])
def get_vehicle_analytics():
    """Get vehicle performance analytics"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                v.id,
                v.registration_number,
                v.vehicle_name,
                COUNT(t.id) as trips_completed,
                SUM(COALESCE(t.actual_distance, 0)) as total_distance,
                SUM(f.liters_filled) as total_fuel,
                (SUM(COALESCE(t.actual_distance, 0)) / NULLIF(SUM(f.liters_filled), 0)) as fuel_efficiency,
                SUM(f.cost) + SUM(COALESCE(m.cost, 0)) as total_operational_cost,
                v.acquisition_cost,
                ((SUM(COALESCE(t.actual_distance, 0)) * 50) - (SUM(f.cost) + SUM(COALESCE(m.cost, 0)))) / v.acquisition_cost as roi
            FROM vehicles v
            LEFT JOIN trips t ON v.id = t.vehicle_id AND t.status = 'Completed'
            LEFT JOIN fuel_logs f ON v.id = f.vehicle_id
            LEFT JOIN maintenance_logs m ON v.id = m.vehicle_id
            GROUP BY v.id
        """)
        analytics = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'data': analytics
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== Search & Filter APIs =====

@app.route('/api/vehicles/search', methods=['GET'])
def search_vehicles():
    """Search and filter vehicles"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = request.args.get('q', '')
        status = request.args.get('status', '')
        vehicle_type = request.args.get('type', '')
        
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
        
        cursor.execute(sql, params)
        vehicles = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'data': vehicles
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/drivers/search', methods=['GET'])
def search_drivers():
    """Search and filter drivers"""
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
        
        return jsonify({
            'success': True,
            'data': drivers
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== Document Management APIs =====

@app.route('/api/documents/vehicle/<int:vehicle_id>', methods=['POST'])
def upload_vehicle_document(vehicle_id):
    """Upload vehicle document"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        document_type = request.form.get('type', 'General')
        expiry_date = request.form.get('expiry_date', '')
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Save file
        filename = f"vehicle_{vehicle_id}_{datetime.now().timestamp()}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Save to database
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO vehicle_documents (vehicle_id, document_type, document_path, expiry_date) VALUES (%s, %s, %s, %s)",
            (vehicle_id, document_type, filepath, expiry_date if expiry_date else None)
        )
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'message': 'Document uploaded successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/documents/driver/<int:driver_id>', methods=['POST'])
def upload_driver_document(driver_id):
    """Upload driver document"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        document_type = request.form.get('type', 'License')
        expiry_date = request.form.get('expiry_date', '')
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Save file
        filename = f"driver_{driver_id}_{datetime.now().timestamp()}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Save to database
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO driver_documents (driver_id, document_type, document_path, expiry_date) VALUES (%s, %s, %s, %s)",
            (driver_id, document_type, filepath, expiry_date if expiry_date else None)
        )
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'message': 'Document uploaded successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== Email Reminder APIs =====

@app.route('/api/reminders/check-expiring-licenses', methods=['POST'])
def check_expiring_licenses():
    """Check for expiring driver licenses and send reminders"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Check licenses expiring within 30 days
        expiry_threshold = datetime.now() + timedelta(days=30)
        cursor.execute("""
            SELECT id, name, license_expiry_date 
            FROM drivers 
            WHERE license_expiry_date <= %s AND license_expiry_date > %s
        """, (expiry_threshold.date(), datetime.now().date()))
        
        expiring_drivers = cursor.fetchall()
        reminders_sent = 0
        
        for driver in expiring_drivers:
            if send_license_expiry_reminder(driver['name'], driver['name'], driver['license_expiry_date']):
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


# ===== PDF Export API =====

@app.route('/api/export/report', methods=['POST'])
def export_report():
    """Export analytics report as PDF"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib import colors
        
        report_type = request.json.get('type', 'fleet')
        
        # Create PDF
        filename = f"TransitOps_{report_type}_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=30,
            alignment=1
        )
        story.append(Paragraph(f"TransitOps {report_type.title()} Report", title_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Get data
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        if report_type == 'fleet':
            cursor.execute("SELECT COUNT(*) as total FROM vehicles")
            total_vehicles = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as total FROM vehicles WHERE status='Available'")
            available = cursor.fetchone()['total']
            
            story.append(Paragraph("Fleet Overview", styles['Heading2']))
            data = [
                ['Metric', 'Value'],
                ['Total Vehicles', str(total_vehicles)],
                ['Available Vehicles', str(available)],
                ['In Service', str(total_vehicles - available)],
                ['Utilization Rate', f"{(total_vehicles - available) / total_vehicles * 100:.2f}%"]
            ]
            
        elif report_type == 'drivers':
            cursor.execute("SELECT COUNT(*) as total FROM drivers")
            total_drivers = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as total FROM drivers WHERE status='Available'")
            available = cursor.fetchone()['total']
            
            story.append(Paragraph("Driver Overview", styles['Heading2']))
            data = [
                ['Metric', 'Value'],
                ['Total Drivers', str(total_drivers)],
                ['Available Drivers', str(available)],
                ['On Duty', str(total_drivers - available)]
            ]
        
        else:  # operations
            cursor.execute("SELECT COUNT(*) as total FROM trips WHERE status='Completed'")
            completed_trips = cursor.fetchone()['total']
            
            cursor.execute("SELECT SUM(actual_distance) as total FROM trips WHERE status='Completed'")
            total_distance = cursor.fetchone()['total'] or 0
            
            story.append(Paragraph("Operations Overview", styles['Heading2']))
            data = [
                ['Metric', 'Value'],
                ['Completed Trips', str(completed_trips)],
                ['Total Distance (km)', str(total_distance)],
                ['Avg Distance/Trip', f"{total_distance / completed_trips if completed_trips > 0 else 0:.2f}"]
            ]
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
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


@app.route('/')
def index():
    return send_file('login.html')


@app.route('/login', methods=['POST'])
def login():
    email = (request.form.get('email') or '').strip().lower()
    password = (request.form.get('password') or '').strip()
    demo_accounts = {
        'fleetmanager@transitops.com': {'password': 'Fleet@123', 'role': 'Fleet Manager'},
        'dispatcher@transitops.com': {'password': 'Dispatcher@123', 'role': 'Dispatcher'},
        'safetyofficer@transitops.com': {'password': 'Safety@123', 'role': 'Safety Officer'},
        'financialanalyst@transitops.com': {'password': 'Finance@123', 'role': 'Financial Analyst'}
    }

    account = demo_accounts.get(email)
    if account and account['password'] == password:
        response = make_response(redirect('/dashboard.html'))
        response.set_cookie('transitops_auth', '1', max_age=3600, path='/')
        response.set_cookie('transitops_role', account['role'], max_age=3600, path='/')
        return response

    return redirect('/login.html?error=1')


@app.route('/dashboard.html')
def dashboard():
    if not is_authenticated():
        return redirect('/login.html')
    return send_file('dashboard.html')


@app.route('/logout')
def logout():
    response = make_response(redirect('/login.html'))
    response.set_cookie('transitops_auth', '', max_age=0, path='/')
    response.set_cookie('transitops_role', '', max_age=0, path='/')
    return response


@app.route('/<path:filename>')
def serve_static(filename):
    if os.path.exists(filename):
        return send_from_directory('.', filename)
    return 'Not found', 404


if __name__ == '__main__':
    init_sqlite_db()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 3000)), debug=True)
