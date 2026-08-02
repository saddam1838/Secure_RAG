"""
Database module - Supports both Supabase (cloud) and SQLite (local fallback).
"""

import sqlite3
import bcrypt
from pathlib import Path
from typing import Tuple, Optional, Dict
from config import settings
from services.cloud_storage import cloud_storage

DB_PATH = settings.DATA_DIR / "users.db"


def init_db():
    """Initialize the appropriate database based on configuration."""
    if cloud_storage.is_cloud_enabled:
        print("✅ Using Supabase for user management")
        return

    # Fallback to SQLite
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Create default admin
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        default_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode("utf-8")
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", default_hash, "admin"),
        )
    conn.commit()
    conn.close()
    print("✅ Using SQLite for user management (local fallback)")


def register_user(username: str, password: str) -> Tuple[bool, str]:
    """Register a new user in the active database."""
    if not username or not password:
        return False, "Username and password are required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )

    # Try cloud first
    if cloud_storage.is_cloud_enabled:
        return cloud_storage.register_user(username, password_hash)

    # Fallback to SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        conn.commit()
        return True, "User registered successfully."
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> Tuple[bool, str, str]:
    """Authenticate a user against the active database."""
    user = None
    # Try cloud first
    if cloud_storage.is_cloud_enabled:
        user = cloud_storage.get_user(username)
        if not user:
            return False, "User not found. Please register first.", ""
        if user and bcrypt.checkpw(
            password.encode("utf-8"), user["password_hash"].encode("utf-8")
        ):
            return True, "Login successful", user["role"]
        return False, "Incorrect password. Please try again.", ""
    
    # Fallback to SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password_hash, role FROM users WHERE username = ?", (username,)
    )
    user_row = cursor.fetchone()
    conn.close()
    
    if not user_row:
        return False, "User not found. Please register first.", ""
    if user_row and bcrypt.checkpw(
        password.encode("utf-8"), user_row[0].encode("utf-8")
    ):
        return True, "Login successful", user_row[1]
    return False, "Incorrect password. Please try again.", ""


# Initialize on import
init_db()
