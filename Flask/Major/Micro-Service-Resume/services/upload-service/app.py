from flask import Flask,request,jsonify
from datetime import datetime
from flask_cors import CORS
import pika  # To make a Communicate between RabbitMQ with Python
import uuid
import json 
import os
import psycopg2
from werkzeug.utils import secure_filename # safely handle uploaded file names before saving them to your server
import logging

# Configuration
app = Flask(__name__)
CORS(app)

# File Upload Setting
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER","/app/uploads")
ALLOWED_EXTENSIONS = {'pdf',"docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024   # 10 MB limit

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_FILE_SIZE'] = MAX_FILE_SIZE

# 🔗 Database & RabbitMQ connections
DATABASE_URL = os.getenv("DATABASE_URL")
RABBITMQ_URL = os.getenv("RABBITMQ_URL")

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper Function
def allowed_file(filename):
    # Check if file extension is allowed (PDF only)
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    # Connection with Data base
    try:
        connection = psycopg2.connect(DATABASE_URL)
        return connection
    except Exception as e:
        logger.error(f"Database Connection Failed : {e}")
        return None

def publish_to_queue(queue_name, message):
    # RabbitMQ message publish
    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()

        # Queue Declare 
        channel.queue_declare(queue=queue_name,durable=True)

        # Message Publish Kro
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2) # Message persistent
        )
        connection.close()
        return True

    except Exception as e:
        logger.error(f"RabbitMQ publish failed: {e}")
        return False

def save_resume_to_db(filename,file_path,file_size,user_id = 1):
    # Save Record into Database
    try:
        connection = get_db_connection()
        if not connection:
            return None
        cursor = connection.cursor()

        # Insert Resume Record
        cursor.execute("""
            INSERT INTO uploaded_resumes (user_id,filename,file_path,file_size,upload_status)
            VALUES (%s,%s,%s,%s,%s)
            RETURNING id
            """,(user_id,filename,file_path,file_size,"uploaded"))
        
        resume_id = cursor.fetchone()[0]
        # Create Entry into Processing status table
        cursor.execute("""
            INSERT INTO processing_status (resume_id, upload_status, current_step)
            VALUES (%s, %s, %s)
            """,(resume_id, True, 'uploaded'))
        connection.commit()
        cursor.close()
        connection.close()

        return resume_id
    except Exception as e:
        logger.error(f"Database save failed: {e}")
        return None
    
# API Endpoints
@app.route("/",methods=['GET'])
def health_check():
    return jsonify({
        "status" : "UP 🔝",
        'service': 'Upload Service',
        'timestamp': datetime.now().isoformat()
    })

@app.route("/upload",methods=['POST'])
def upload_resume():
    # Main upload endpoint
    try:
        # Check if file present 
        if 'resume' not in request.files:
            return jsonify({'error': 'No resume file provided'}),400
        
        file = request.files['resume']
        jb_text = request.form.get("job_description","")

        # File validation
        if file.filename == '':
            return jsonify({"error" : "No file selected"}),400
        
        if not allowed_file(file.filename):
            return jsonify({"error" : "Only PDF and Docx are Allowed"}),400

        # Secure filename
        original_filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{original_filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'],unique_filename)

        # File save
        os.makedirs(app.config['UPLOAD_FOLDER'],exist_ok=True)
        file.save(file_path)
        file_size = os.path.getsize(file_path)

        logger.info(f"File saved: {file_path} ({file_size} bytes)")

        # Save Record into Database
        resume_id = save_resume_to_db(unique_filename,file_path,file_size)

        if not resume_id:
            return jsonify({'error': 'Database save failed'}), 500
        
        # RabbitMQ message publish
        message = {
            'resume_id' : resume_id,
            'user_id' : 1,
            'resume_path' : file_path,
            'original_filename' : original_filename,
            'jd_text' : jb_text,
            'timestamp' : datetime.now().isoformat()
        }

        if not publish_to_queue('parser_queue',message):
            return jsonify({'error': 'Failed to queue for processing'}), 500
        
        # Success response  
        return jsonify({
            'success': True,
            'message': 'Resume uploaded successfully',
            'resume_id': resume_id,
            'filename': original_filename,
            'file_size': file_size,
            'status': 'queued_for_parsing'
        }),200
    except Exception as e:
        logger.error(f"Upload Failed : {e}")
        return jsonify({'error': 'Internal server error'}), 500
    
@app.route("/status/<int:resume_id>",methods=['GET'])
def get_status(resume_id):
    # Processing status check
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}),500
        cursor = connection.cursor()

        # Processing status fetch
        cursor.execute("""
            SELECT ps.*,ur.filename,ur.upload_status as file_status FROM processing_status ps
            JOIN
            uploaded_resumes ur ON ps.resume_id = ur.id
            WHERE ps.resume_id = %s
        """,(resume_id,))

        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if not result:
            return jsonify({'error': 'Resume not found'}), 404
        
        status = {
            'resume_id': result[1],
            'filename': result[11],
            'steps': {
                'upload': result[2],      # upload_status
                'parsing': result[3],     # parsing_status  
                'analytics': result[4],   # analytics_status
                'ai_feedback': result[5], # ai_feedback_status
                'finalized': result[6]    # finalized_status
            },
            'current_step': result[7],
            'error_message': result[8],
            'updated_at': result[9].isoformat() if result[9] else None
        }
        return jsonify(status),200

    except Exception as e:
        logging.error(f"Status check failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/uploads', methods=['GET'])
def list_uploads():
    # All uploads list
    try:
        connection = get_db_connection()

        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor()

        cursor.execute("""
            SELECT id, filename, file_size, upload_status, created_at
            FROM uploaded_resumes
            ORDER BY created_at DESC
            LIMIT 20 
        """)
        results = cursor.fetchall()
        cursor.close()
        connection.close()

        uploads = []
        for row in results:
            uploads.append({
                'id': row[0],
                'filename': row[1],
                'file_size': row[2],
                'status': row[3],
                'uploaded_at': row[4].isoformat() if row[4] else None
            })
        
        return jsonify({
            'uploads': uploads,
            'count': len(uploads)
        }), 200
    
    except Exception as e:
        logger.error(f"List uploads failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    

@app.errorhandler(413)
def file_too_large(error):
    # File size limit exceeded
    return jsonify({'error': 'File too large. Maximum size: 10MB'}), 413

@app.errorhandler(404)
def not_found(error):
    # Route not found
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    # Internal server error
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Upload folder create karo agar nahi hai
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    logger.info("🚀 Upload Service starting...")
    logger.info(f"📁 Upload folder: {UPLOAD_FOLDER}")
    logger.info(f"🔗 Database: {DATABASE_URL}")
    logger.info(f"🐰 RabbitMQ: {RABBITMQ_URL}")
    app.run(host='0.0.0.0', port=5000, debug=True)