from flask import Flask, request, jsonify
import psycopg2
import os
import uuid
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Database connection
def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('POSTGRES_DB', 'defaultdb'),
            user=os.getenv('POSTGRES_USER', 'defaultuser'),
            password=os.getenv('POSTGRES_PASSWORD', 'defaultpassword'),
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432')
        )
        return conn
    except psycopg2.OperationalError as e:
        logging.error(f"Database connection failed: {e}")
        return None

# Home endpoint
@app.route('/')
def home():
    """Serve a user-friendly HTML page."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Task Service</title>
    </head>
    <body>
        <h1>Welcome to the Task Service API</h1>
        <p>Available Endpoints:</p>
        <ul>
            <li><strong>POST /tasks:</strong> Add a new task</li>
            <li><strong>GET /tasks:</strong> Retrieve all tasks</li>
            <li><strong>GET /health:</strong> Check service health</li>
        </ul>
    </body>
    </html>
    """, 200


# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        if conn:
            conn.close()
            logging.info("Health check: Service is healthy.")
            return jsonify({'status': 'healthy'}), 200
        else:
            return jsonify({'status': 'unhealthy', 'error': 'Database connection failed'}), 500
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# Create task endpoint
@app.route('/tasks', methods=['POST'])
def create_task():
    """Endpoint to create a new task."""
    try:
        task = request.json
        if not task or 'title' not in task or 'description' not in task:
            return jsonify({'error': 'Invalid task data. "title" and "description" are required.'}), 400

        # Generate a unique ID for the task
        task_id = str(uuid.uuid4())

        # Save task to database
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO tasks (id, title, description) VALUES (%s, %s, %s)",
                    (task_id, task['title'], task['description'])
                )
                conn.commit()
                conn.close()

            logging.info(f"Task created: {task_id}")
            return jsonify({'message': 'Task added successfully', 'task': {'id': task_id, 'title': task['title'], 'description': task['description']}}), 201
        else:
            return jsonify({'error': 'Failed to connect to the database.'}), 500
    except Exception as e:
        logging.error(f"Error creating task: {e}")
        return jsonify({'error': 'An error occurred while creating the task.'}), 500

# Get tasks endpoint
@app.route('/tasks', methods=['GET'])
def get_tasks():
    """Endpoint to retrieve all tasks."""
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, title, description FROM tasks")
                tasks = cursor.fetchall()
                conn.close()

            logging.info("Retrieved all tasks.")
            return jsonify([{'id': task[0], 'title': task[1], 'description': task[2]} for task in tasks]), 200
        else:
            return jsonify({'error': 'Failed to connect to the database.'}), 500
    except Exception as e:
        logging.error(f"Error retrieving tasks: {e}")
        return jsonify({'error': 'An error occurred while retrieving tasks.'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
