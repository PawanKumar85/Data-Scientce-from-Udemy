import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Base configuration class    

    # 🔐 Security Settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # 📁 File Upload Settings 
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '/app/uploads')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {'pdf','docx'}
    
    # 🗃 Database Configuration 
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres123@localhost:5432/microresume_db')
    
    # 🐰 RabbitMQ Configuration 
    RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://admin:password123@localhost:5672/')
    PARSER_QUEUE = 'parser_queue'
    
    # 📝 Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', '/app/logs/upload-service.log')
    
    # 🌐 CORS Settings 
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')

class DevelopmentConfig(Config):
    # Development environment config
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    # Production environment config
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    # Testing environment config
    DEBUG = True
    TESTING = True
    DATABASE_URL = os.getenv('TEST_DATABASE_URL', 'postgresql://postgres:postgres123@localhost:5432/test_microresume_db')

config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}

def get_config():
    # Current environment ka config return 
    env = os.getenv('FLASK_ENV', 'development')
    return config_by_name.get(env, DevelopmentConfig)