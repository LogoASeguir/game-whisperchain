"""
Configuration management for WhisperChain.
Loads from environment variables with fallbacks.
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    """Base configuration"""
    
    # Flask
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # Database
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('DB_PORT', 5432))
    DB_NAME = os.environ.get('DB_NAME', 'whisperchain')
    DB_USER = os.environ.get('DB_USER', 'RDev')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'dev123')
    
    # Admin Authentication
    ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'change-me-in-production')
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_DEFAULT = "100 per minute"
    RATELIMIT_ENABLED = True
    
    # WebSocket
    SOCKETIO_MESSAGE_QUEUE = None
    SOCKETIO_CORS_ALLOWED_ORIGINS = "*"
    
    # Game Settings
    MAX_PLAYERS_PER_ROOM = 10
    MAX_ROOMS = 100
    MAX_CONNECTIONS_PER_IP = 5
    STARTING_SIGNAL = 30
    
    # Security
    MAX_USERNAME_LENGTH = 20
    MIN_USERNAME_LENGTH = 3
    MAX_MESSAGE_LENGTH = 1000
    MAX_PAYLOAD_SIZE = 50000
    BAN_AFTER_ATTEMPTS = 3
    
    @classmethod
    def get_db_url(cls):
        """Get database connection URL"""
        return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    RATELIMIT_ENABLED = True
    SOCKETIO_CORS_ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '*').split(',')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DB_NAME = 'whisperchain_test'

# Select config based on environment
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get current configuration"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
