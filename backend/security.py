# security.py
"""
Security utilities for WhisperChain.
Input validation, sanitization, and access control.
"""

import re
import html
from functools import wraps
from flask import request, jsonify
import time


# ============================================
# INPUT SANITIZATION
# ============================================

def sanitize_input(text):
    """
    Sanitize user input by escaping HTML and removing dangerous characters.
    """
    if not isinstance(text, str):
        return ""

    text = html.escape(text.strip())
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')

    return text


def validate_username(username, config):
    """
    Validate username format and length.
    """
    if not username:
        return False, "Username cannot be empty"

    if len(username) < config.MIN_USERNAME_LENGTH:
        return False, f"Username must be at least {config.MIN_USERNAME_LENGTH} characters"

    if len(username) > config.MAX_USERNAME_LENGTH:
        return False, f"Username too long (max {config.MAX_USERNAME_LENGTH} characters)"

    if not re.match(r'^[a-zA-Z0-9_ -]+$', username):
        return False, "Username contains invalid characters"

    return True, ""


def validate_room_code_secure(code):
    """
    Validate room code format with security checks.
    """
    if not code or not isinstance(code, str):
        return False

    if len(code) != 3:
        return False

    if not (code[:2].isdigit() and code[2].isupper()):
        return False

    return True


def validate_message(message, config):
    """
    Validate game message.
    """
    if not message:
        return False, "Message cannot be empty"

    if len(message) > config.MAX_MESSAGE_LENGTH:
        return False, f"Message too long (max {config.MAX_MESSAGE_LENGTH} characters)"

    if not re.match(r'^[a-zA-Z0-9_ ]+$', message):
        return False, "Message contains invalid characters"

    return True, ""


def validate_payload_size(data, max_size):
    """
    Check if payload size is within limits.
    """
    import json
    try:
        size = len(json.dumps(data).encode('utf-8'))
        return size <= max_size
    except:
        return False


# ============================================
# RATE LIMITING
# ============================================

class SimpleRateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self):
        self.requests = {}
        self.cleanup_interval = 60
        self.last_cleanup = time.time()

    def check_limit(self, identifier, max_requests, window):
        """
        Check if identifier is within rate limit.
        """
        now = time.time()

        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup(now, window)

        if identifier not in self.requests:
            self.requests[identifier] = []

        history = self.requests[identifier]

        cutoff = now - window
        history = [ts for ts in history if ts > cutoff]

        if len(history) >= max_requests:
            return False

        history.append(now)
        self.requests[identifier] = history

        return True

    def _cleanup(self, now, window):
        """Remove old entries to prevent memory bloat."""
        cutoff = now - window
        for identifier in list(self.requests.keys()):
            self.requests[identifier] = [
                ts for ts in self.requests[identifier] if ts > cutoff
            ]
            if not self.requests[identifier]:
                del self.requests[identifier]

        self.last_cleanup = now


_rate_limiter = SimpleRateLimiter()


def check_rate_limit(identifier, max_requests=100, window=60):
    """
    Check if identifier is within rate limit.
    """
    return _rate_limiter.check_limit(identifier, max_requests, window)


# ============================================
# AUTHENTICATION
# ============================================

def verify_admin_token(token, config):
    """
    Verify admin authentication token.
    """
    if not token or not config.ADMIN_TOKEN:
        return False

    return token == config.ADMIN_TOKEN


def require_admin(config):
    """
    Decorator to require admin authentication.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.headers.get('Authorization', '').replace('Bearer ', '')

            if not verify_admin_token(token, config):
                return jsonify({'error': 'Unauthorized'}), 401

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================
# IP TRACKING
# ============================================

class ConnectionTracker:
    """Track connections per IP address."""

    def __init__(self):
        self.connections = {}

    def add_connection(self, ip, max_per_ip=5):
        """
        Add connection for IP.
        """
        current = self.connections.get(ip, 0)

        if current >= max_per_ip:
            return False

        self.connections[ip] = current + 1
        return True

    def remove_connection(self, ip):
        """Remove connection for IP."""
        if ip in self.connections:
            self.connections[ip] = max(0, self.connections[ip] - 1)
            if self.connections[ip] == 0:
                del self.connections[ip]

    def get_count(self, ip):
        """Get current connection count for IP."""
        return self.connections.get(ip, 0)


# ============================================
# TESTS
# ============================================
if __name__ == "__main__":
    print("=" * 60)
    print("SECURITY TESTS")
    print("=" * 60)

    print("\n--- Input Sanitization ---")
    test_inputs = [
        "<script>alert('xss')</script>",
        "Normal username",
        "Test & User",
        "  spaces  ",
    ]

    for inp in test_inputs:
        sanitized = sanitize_input(inp)
        print(f"'{inp}' -> '{sanitized}'")

    print("\n--- Rate Limiting ---")
    for i in range(15):
        allowed = check_rate_limit("test_ip", max_requests=10, window=60)
        status = "OK" if allowed else "BLOCKED"
        print(f"Request {i+1}: {status}")

    print("\n--- Connection Tracking ---")
    tracker = ConnectionTracker()

    for i in range(7):
        allowed = tracker.add_connection("192.168.1.1", max_per_ip=5)
        count = tracker.get_count("192.168.1.1")
        status = "Allowed" if allowed else "BLOCKED"
        print(f"Connection {i+1}: {status} (total: {count})")

    print("\n" + "=" * 60)
    print("SECURITY TESTS COMPLETE")
    print("=" * 60)
