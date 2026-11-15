"""
Enhanced Admin Dashboard - Database Statistics
==============================================
Displays user registrations, system statistics, and activity metrics.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, session, render_template, redirect, url_for

admin_dashboard_bp = Blueprint("admin_dashboard", __name__)

# ============================================================
# Helper Functions
# ============================================================

def get_db(db_name):
    conn = sqlite3.connect(db_name, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_stats():
    """Get user registration statistics"""
    conn = get_db("users.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Total users
        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()['count']

        # Users registered today
        cursor.execute("""
            SELECT COUNT(*) as count FROM users
            WHERE DATE(created_at) = DATE('now')
        """)
        today_users = cursor.fetchone()['count']

        # Users registered this week
        cursor.execute("""
            SELECT COUNT(*) as count FROM users
            WHERE DATE(created_at) >= DATE('now', '-7 days')
        """)
        week_users = cursor.fetchone()['count']

        # Recent users (last 10)
        cursor.execute("""
            SELECT id, username, email, created_at FROM users
            ORDER BY created_at DESC LIMIT 10
        """)
        recent_users = [dict(row) for row in cursor.fetchall()]

        return {
            'total': total_users,
            'today': today_users,
            'week': week_users,
            'recent': recent_users
        }
    finally:
        conn.close()


def get_telemetry_stats():
    """Get sensor data statistics"""
    conn = get_db("telemetry.db")
    cursor = conn.cursor()

    try:
        # Total readings
        cursor.execute("SELECT COUNT(*) as count FROM readings")
        total_readings = cursor.fetchone()['count']

        # Readings today
        cursor.execute("""
            SELECT COUNT(*) as count FROM readings
            WHERE DATE(ts) = DATE('now')
        """)
        today_readings = cursor.fetchone()['count']

        # Active alerts
        cursor.execute("""
            SELECT COUNT(*) as count FROM alerts
            WHERE ts_cleared IS NULL
        """)
        active_alerts = cursor.fetchone()['count']

        # Total alerts (all time)
        cursor.execute("SELECT COUNT(*) as count FROM alerts")
        total_alerts = cursor.fetchone()['count']

        # Average sensor values (latest)
        cursor.execute("""
            SELECT
                AVG(moisture_pct) as avg_moisture,
                AVG(air_temp_c) as avg_temp,
                AVG(humidity_pct) as avg_humidity,
                AVG(ph) as avg_ph
            FROM readings
            WHERE ts >= datetime('now', '-1 hour')
        """)
        row = cursor.fetchone()
        avg_values = {
            'moisture': round(row['avg_moisture'], 1) if row['avg_moisture'] else 0,
            'temp': round(row['avg_temp'], 1) if row['avg_temp'] else 0,
            'humidity': round(row['avg_humidity'], 1) if row['avg_humidity'] else 0,
            'ph': round(row['avg_ph'], 2) if row['avg_ph'] else 0
        }

        return {
            'total_readings': total_readings,
            'today_readings': today_readings,
            'active_alerts': active_alerts,
            'total_alerts': total_alerts,
            'average_values': avg_values
        }
    finally:
        conn.close()


def get_price_stats():
    """Get price prediction statistics"""
    conn = get_db("prices.db")
    cursor = conn.cursor()

    try:
        # Total price records
        cursor.execute("SELECT COUNT(*) as count FROM prices")
        total_prices = cursor.fetchone()['count']

        # Commodities tracked
        cursor.execute("SELECT COUNT(DISTINCT Commodity) as count FROM prices")
        commodities = cursor.fetchone()['count']

        # Markets tracked
        cursor.execute("SELECT COUNT(DISTINCT Market) as count FROM prices")
        markets = cursor.fetchone()['count']

        # Latest price date
        cursor.execute("SELECT MAX(Date) as latest_date FROM prices")
        latest_date = cursor.fetchone()['latest_date']

        return {
            'total_prices': total_prices,
            'commodities': commodities,
            'markets': markets,
            'latest_date': latest_date
        }
    finally:
        conn.close()


def get_system_stats():
    """Get system activity statistics"""
    conn = get_db("users.db")
    cursor = conn.cursor()

    try:
        # Check if activity_log table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='activity_log'
        """)

        if cursor.fetchone():
            # Total activities
            cursor.execute("SELECT COUNT(*) as count FROM activity_log")
            total_activities = cursor.fetchone()['count']

            # Activities today
            cursor.execute("""
                SELECT COUNT(*) as count FROM activity_log
                WHERE DATE(timestamp) = DATE('now')
            """)
            today_activities = cursor.fetchone()['count']

            # Action breakdown
            cursor.execute("""
                SELECT action_type, COUNT(*) as count
                FROM activity_log
                GROUP BY action_type
            """)
            action_breakdown = {row['action_type']: row['count'] for row in cursor.fetchall()}
        else:
            total_activities = 0
            today_activities = 0
            action_breakdown = {}

        return {
            'total_activities': total_activities,
            'today_activities': today_activities,
            'action_breakdown': action_breakdown
        }
    finally:
        conn.close()


# ============================================================
# Routes
# ============================================================

@admin_dashboard_bp.route('/admin/dashboard')
@admin_dashboard_bp.route('/admin-dashboard')
def admin_dashboard():
    """Render admin dashboard"""
    if 'is_admin' not in session or not session['is_admin']:
        return redirect(url_for('login'))

    return render_template('admin_dashboard.html', username=session.get('username'))


@admin_dashboard_bp.route('/api/admin/stats')
def get_all_stats():
    """API endpoint for all statistics"""
    if 'is_admin' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401

    stats = {
        'users': get_user_stats(),
        'telemetry': get_telemetry_stats(),
        'prices': get_price_stats(),
        'system': get_system_stats(),
        'timestamp': datetime.now().isoformat()
    }

    return jsonify(stats)


@admin_dashboard_bp.route('/api/admin/users')
def get_all_users():
    """Get all registered users"""
    if 'is_admin' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db("users.db")
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, username, email, created_at, last_login
            FROM users
            ORDER BY created_at DESC
        """)
        users = [dict(row) for row in cursor.fetchall()]
        return jsonify({'users': users, 'total': len(users)})
    finally:
        conn.close()


@admin_dashboard_bp.route('/api/admin/telemetry/latest')
def get_latest_telemetry():
    """Get latest telemetry readings"""
    if 'is_admin' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db("telemetry.db")
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT * FROM readings
            ORDER BY ts DESC LIMIT 100
        """)
        readings = [dict(row) for row in cursor.fetchall()]
        return jsonify({'readings': readings, 'total': len(readings)})
    finally:
        conn.close()


@admin_dashboard_bp.route('/api/admin/alerts/active')
def get_active_alerts():
    """Get active alerts"""
    if 'is_admin' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db("telemetry.db")
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT * FROM alerts
            WHERE ts_cleared IS NULL
            ORDER BY ts_raised DESC LIMIT 50
        """)
        alerts = [dict(row) for row in cursor.fetchall()]
        return jsonify({'alerts': alerts, 'total': len(alerts)})
    finally:
        conn.close()


@admin_dashboard_bp.route('/api/admin/alerts/history')
def get_alert_history():
    """Get alert history (last 30 days)"""
    if 'is_admin' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db("telemetry.db")
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT * FROM alerts
            WHERE ts_raised >= datetime('now', '-30 days')
            ORDER BY ts_raised DESC LIMIT 500
        """)
        alerts = [dict(row) for row in cursor.fetchall()]
        return jsonify({'alerts': alerts, 'total': len(alerts)})
    finally:
        conn.close()


@admin_dashboard_bp.route('/api/admin/sensors/stats')
def get_sensor_stats():
    """Get sensor statistics and trends"""
    if 'is_admin' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db("telemetry.db")
    cursor = conn.cursor()

    try:
        # Stats by hour
        cursor.execute("""
            SELECT
                strftime('%Y-%m-%d %H:00', ts) as hour,
                COUNT(*) as reading_count,
                AVG(moisture_pct) as avg_moisture,
                AVG(air_temp_c) as avg_temp,
                AVG(humidity_pct) as avg_humidity
            FROM readings
            WHERE ts >= datetime('now', '-7 days')
            GROUP BY hour
            ORDER BY hour DESC
            LIMIT 24
        """)
        hourly = [dict(row) for row in cursor.fetchall()]

        return jsonify({'hourly_stats': hourly})
    finally:
        conn.close()
