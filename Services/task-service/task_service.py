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


_db_initialized = False


def init_db():
    """Create tasks table if it does not exist yet."""
    global _db_initialized
    if _db_initialized:
        return
    try:
        conn = get_db_connection()
        if not conn:
            return
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status BOOLEAN NOT NULL DEFAULT FALSE
                );
                """
            )
            # Ensure status column exists for upgrades from older schema
            cursor.execute(
                "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS status BOOLEAN NOT NULL DEFAULT FALSE;"
            )
            conn.commit()
        conn.close()
        _db_initialized = True
    except Exception as e:
        logging.warning(f"DB init deferred, will retry later: {e}")

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
        <p><strong>GET /health:</strong> Service health status</p>
    </body>
    </html>
    """, 200


# Health check endpoint
@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        init_db()
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
@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Endpoint to create a new task."""
    try:
        init_db()
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
                    "INSERT INTO tasks (id, title, description, status) VALUES (%s, %s, %s, FALSE)",
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
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Endpoint to retrieve all tasks."""
    try:
        init_db()
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, title, description, status FROM tasks ORDER BY title ASC")
                tasks = cursor.fetchall()
                conn.close()

            logging.info("Retrieved all tasks.")
            return jsonify([
                {'id': t[0], 'title': t[1], 'description': t[2], 'status': bool(t[3])}
                for t in tasks
            ]), 200
        else:
            return jsonify({'error': 'Failed to connect to the database.'}), 500
    except Exception as e:
        logging.error(f"Error retrieving tasks: {e}")
        return jsonify({'error': 'An error occurred while retrieving tasks.'}), 500

# Complete a task
@app.route('/tasks/<task_id>/complete', methods=['PATCH', 'POST'])
@app.route('/api/tasks/<task_id>/complete', methods=['PATCH', 'POST'])
def complete_task(task_id):
    try:
        init_db()
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE tasks SET status = TRUE WHERE id = %s", (task_id,))
                conn.commit()
                cursor.execute("SELECT id, title, description, status FROM tasks WHERE id = %s", (task_id,))
                row = cursor.fetchone()
            conn.close()
            if not row:
                return jsonify({'error': 'Task not found'}), 404
            return jsonify({'id': row[0], 'title': row[1], 'description': row[2], 'status': bool(row[3])}), 200
        else:
            return jsonify({'error': 'Failed to connect to the database.'}), 500
    except Exception as e:
        logging.error(f"Error completing task: {e}")
        return jsonify({'error': 'An error occurred while completing the task.'}), 500

# Delete a task
@app.route('/tasks/<task_id>', methods=['DELETE'])
@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    try:
        init_db()
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
                deleted = cursor.rowcount
                conn.commit()
            conn.close()
            if deleted == 0:
                return jsonify({'error': 'Task not found'}), 404
            return jsonify({'message': 'Task deleted'}), 200
        else:
            return jsonify({'error': 'Failed to connect to the database.'}), 500
    except Exception as e:
        logging.error(f"Error deleting task: {e}")
        return jsonify({'error': 'An error occurred while deleting the task.'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
