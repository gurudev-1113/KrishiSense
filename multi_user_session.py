"""
multi_user_session.py
======================
Handles concurrent multi-device user sessions without conflicts.

Features:
- Per-device session isolation
- Device fingerprinting (user-agent, OS, device ID)
- Concurrent login limit management
- Session conflict detection & resolution
- Real-time device sync
"""

import hashlib
import json
import threading
from datetime import datetime, timedelta
from functools import wraps
from flask import request, session, jsonify, g

# Thread-safe session storage
_sessions_lock = threading.RLock()
_device_sessions = {}  # {user_id: {device_id: session_data}}
_session_timeout = 7 * 24 * 60 * 60  # 7 days


def get_device_fingerprint():
    """Generate unique device fingerprint from user-agent and headers."""
    user_agent = request.headers.get('User-Agent', '')
    accept_language = request.headers.get('Accept-Language', '')
    remote_addr = request.remote_addr

    fingerprint_str = f"{user_agent}|{accept_language}|{remote_addr}"
    device_id = hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]

    return device_id


def get_device_info():
    """Extract device info from request headers."""
    user_agent = request.headers.get('User-Agent', 'Unknown')

    # Detect device type
    device_type = 'desktop'
    if 'mobile' in user_agent.lower() or 'android' in user_agent.lower():
        device_type = 'mobile'
    elif 'tablet' in user_agent.lower() or 'ipad' in user_agent.lower():
        device_type = 'tablet'

    return {
        'device_id': get_device_fingerprint(),
        'user_agent': user_agent,
        'device_type': device_type,
        'ip_address': request.remote_addr,
        'timestamp': datetime.utcnow().isoformat(),
    }


def register_device_session(user_id, max_concurrent=5):
    """
    Register a device session for a user.

    Args:
        user_id: User's ID
        max_concurrent: Maximum concurrent devices allowed (default 5)

    Returns:
        {success: bool, message: str, sessions: list}
    """
    device_info = get_device_info()
    device_id = device_info['device_id']

    with _sessions_lock:
        if user_id not in _device_sessions:
            _device_sessions[user_id] = {}

        user_devices = _device_sessions[user_id]
        active_devices = [d for d, s in user_devices.items()
                         if datetime.fromisoformat(s['last_active']) >
                         datetime.utcnow() - timedelta(seconds=_session_timeout)]

        # Check if max concurrent limit reached
        if len(active_devices) >= max_concurrent and device_id not in user_devices:
            return {
                'success': False,
                'message': f'Maximum {max_concurrent} concurrent devices allowed. Please logout from another device.',
                'active_count': len(active_devices),
                'max_allowed': max_concurrent,
                'sessions': [_format_session(user_devices[d]) for d in active_devices[:3]]
            }

        # Register/update device session
        session_data = {
            **device_info,
            'session_id': session.get('session_id', hashlib.sha256(f"{user_id}_{device_id}_{datetime.utcnow().timestamp()}".encode()).hexdigest()[:24]),
            'first_active': user_devices.get(device_id, {}).get('first_active', datetime.utcnow().isoformat()),
            'last_active': datetime.utcnow().isoformat(),
        }

        user_devices[device_id] = session_data

        return {
            'success': True,
            'message': f'Device registered ({device_info["device_type"]} from {device_info["ip_address"]})',
            'device_id': device_id,
            'device_info': device_info,
            'total_active': len(active_devices) + (0 if device_id in active_devices else 1),
        }


def get_user_devices(user_id):
    """Get all active device sessions for a user."""
    with _sessions_lock:
        if user_id not in _device_sessions:
            return []

        user_devices = _device_sessions[user_id]
        active = []

        for device_id, session_data in user_devices.items():
            last_active = datetime.fromisoformat(session_data['last_active'])
            if last_active > datetime.utcnow() - timedelta(seconds=_session_timeout):
                active.append(_format_session(session_data))

        return active


def _format_session(session_data):
    """Format session data for API response."""
    last_active = datetime.fromisoformat(session_data['last_active'])
    return {
        'device_id': session_data['device_id'][:8] + '****',
        'device_type': session_data['device_type'],
        'ip_address': session_data['ip_address'],
        'user_agent': session_data['user_agent'][:40] + '...',
        'last_active': last_active.isoformat(),
        'is_current': session_data['device_id'] == get_device_fingerprint(),
    }


def logout_device(user_id, device_id=None):
    """
    Logout a specific device or current device.

    Args:
        user_id: User's ID
        device_id: Device ID to logout (default: current device)
    """
    if device_id is None:
        device_id = get_device_fingerprint()

    with _sessions_lock:
        if user_id in _device_sessions:
            _device_sessions[user_id].pop(device_id, None)
            return {'success': True, 'message': 'Device logged out'}

    return {'success': False, 'message': 'Device not found'}


def logout_all_devices(user_id):
    """Logout all devices for a user."""
    with _sessions_lock:
        _device_sessions.pop(user_id, None)
    return {'success': True, 'message': 'All devices logged out'}


def update_device_activity(user_id):
    """Update last activity timestamp for current device."""
    device_id = get_device_fingerprint()

    with _sessions_lock:
        if user_id in _device_sessions and device_id in _device_sessions[user_id]:
            _device_sessions[user_id][device_id]['last_active'] = datetime.utcnow().isoformat()


def check_session_conflicts(user_id):
    """Check for session conflicts (login from new location)."""
    device_info = get_device_info()
    device_id = device_info['device_id']

    with _sessions_lock:
        if user_id not in _device_sessions:
            return None

        user_devices = _device_sessions[user_id]

        # Check if this is a new device/location
        if device_id not in user_devices:
            # New device - return suspicious activity alert
            other_devices = [_format_session(user_devices[d]) for d in user_devices if d != device_id]
            if other_devices:
                return {
                    'alert': 'new_location',
                    'message': 'Login detected from new location/device',
                    'new_device': device_info,
                    'other_devices': other_devices[:2],
                }

        return None


def require_multi_user_session(f):
    """Decorator to ensure user has valid multi-device session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401

        # Update device activity
        update_device_activity(user_id)

        # Check for conflicts
        conflict = check_session_conflicts(user_id)
        if conflict:
            g.session_alert = conflict

        return f(*args, **kwargs)

    return decorated_function


def cleanup_expired_sessions():
    """Remove expired sessions (background cleanup)."""
    with _sessions_lock:
        cutoff_time = datetime.utcnow() - timedelta(seconds=_session_timeout)

        for user_id in list(_device_sessions.keys()):
            user_devices = _device_sessions[user_id]
            expired = [d for d, s in user_devices.items()
                      if datetime.fromisoformat(s['last_active']) < cutoff_time]

            for device_id in expired:
                del user_devices[device_id]

            # Remove user entry if no active sessions
            if not user_devices:
                del _device_sessions[user_id]


# Thread to cleanup expired sessions every 6 hours
def _start_cleanup_thread():
    def cleanup_loop():
        while True:
            try:
                import time
                time.sleep(6 * 60 * 60)  # 6 hours
                cleanup_expired_sessions()
            except Exception as e:
                print(f"[Multi-User Session] Cleanup error: {e}")

    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()


_start_cleanup_thread()
