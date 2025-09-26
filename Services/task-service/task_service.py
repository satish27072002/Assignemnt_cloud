from flask import Flask, request, jsonify
import logging
import os
import psycopg2
from psycopg2 import OperationalError
import uuid

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


def get_db_connection():
    """Return a database connection using environment variables."""
    try:
        return psycopg2.connect(
            dbname=os.getenv('POSTGRES_DB', 'defaultdb'),
            user=os.getenv('POSTGRES_USER', 'defaultuser'),
            password=os.getenv('POSTGRES_PASSWORD', 'defaultpassword'),
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432')
        )
    except OperationalError as exc:
        logging.error("Database connection failed: %s", exc)
        return None


def init_db():
    """Create the tasks table if it is missing."""
    conn = get_db_connection()
    if not conn:
        logging.warning("Skipping task table initialization; database unavailable")
        return
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id UUID PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status BOOLEAN NOT NULL DEFAULT FALSE
                );
                """
            )
    except Exception as exc:
        logging.error("Failed to initialize tasks table: %s", exc)
    finally:
        conn.close()


init_db()


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


@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'status': 'unhealthy', 'error': 'Database connection failed'}), 500
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
        logging.info("Health check: Service is healthy.")
        return jsonify({'status': 'healthy'}), 200
    except Exception as exc:
        logging.error("Health check failed: %s", exc)
        return jsonify({'status': 'unhealthy', 'error': 'Query failed'}), 500
    finally:
        conn.close()


@app.route('/tasks', methods=['POST'])
@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Endpoint to create a new task."""
    task = request.json
    if not task or 'title' not in task or 'description' not in task:
        return jsonify({'error': 'Invalid task data. "title" and "description" are required.'}), 400

    task_id = str(uuid.uuid4())
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Failed to connect to the database.'}), 500

    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO tasks (id, title, description) VALUES (%s, %s, %s)",
                    (task_id, task['title'], task['description'])
                )
        logging.info("Task created: %s", task_id)
        return jsonify({'message': 'Task added successfully', 'task': {'id': task_id, 'title': task['title'], 'description': task['description'], 'status': False}}), 201
    except Exception as exc:
        conn.rollback()
        logging.error("Error creating task: %s", exc)
        return jsonify({'error': 'An error occurred while creating the task.'}), 500
    finally:
        conn.close()


@app.route('/tasks', methods=['GET'])
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Endpoint to retrieve all tasks."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Failed to connect to the database.'}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT id, title, description, status FROM tasks ORDER BY title ASC')
            tasks = cursor.fetchall()
        logging.info("Retrieved all tasks.")
        return jsonify([
            {'id': row[0], 'title': row[1], 'description': row[2], 'status': row[3]}
            for row in tasks
        ]), 200
    except Exception as exc:
        logging.error("Error retrieving tasks: %s", exc)
        return jsonify({'error': 'An error occurred while retrieving tasks.'}), 500
    finally:
        conn.close()


@app.route('/tasks/<task_id>/complete', methods=['PATCH'])
@app.route('/api/tasks/<task_id>/complete', methods=['PATCH'])
def complete_task(task_id):
    """Mark a task as completed."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Failed to connect to the database.'}), 500

    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    'UPDATE tasks SET status = TRUE WHERE id = %s AND status = FALSE',
                    (task_id,)
                )
                if cursor.rowcount == 0:
                    return jsonify({'error': 'Task not found or already completed.'}), 404
        logging.info("Task completed: %s", task_id)
        return jsonify({'message': 'Task marked as complete.'}), 200
    except Exception as exc:
        conn.rollback()
        logging.error("Error completing task %s: %s", task_id, exc)
        return jsonify({'error': 'An error occurred while completing the task.'}), 500
    finally:
        conn.close()


@app.route('/tasks/<task_id>', methods=['DELETE'])
@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Failed to connect to the database.'}), 500

    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute('DELETE FROM tasks WHERE id = %s', (task_id,))
                if cursor.rowcount == 0:
                    return jsonify({'error': 'Task not found.'}), 404
        logging.info("Task deleted: %s", task_id)
        return jsonify({'message': 'Task deleted successfully.'}), 200
    except Exception as exc:
        conn.rollback()
        logging.error("Error deleting task %s: %s", task_id, exc)
        return jsonify({'error': 'An error occurred while deleting the task.'}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
