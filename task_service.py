from flask import Flask, request, jsonify
import psycopg2

app = Flask(__name__)

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname="appdb",
    user="appuser",
    password="apppassword",
    host="postgres",  # Use the Kubernetes service name
    port="5432"
)
cursor = conn.cursor()

# Create tasks table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL
)
""")
conn.commit()

@app.route('/tasks', methods=['POST'])
def create_task():
    task = request.json  # Get the JSON data from the request
    if not task or 'title' not in task or 'description' not in task:
        return jsonify({'error': 'Invalid task data'}), 400
    
    try:
        cursor.execute("INSERT INTO tasks (title, description) VALUES (%s, %s) RETURNING id", (task['title'], task['description']))
        conn.commit()
        task_id = cursor.fetchone()[0]
        return jsonify({'message': 'Task added successfully', 'task_id': task_id}), 201
    except psycopg2.Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/tasks', methods=['GET'])
def get_tasks():
    cursor.execute("SELECT id, title, description FROM tasks")
    tasks = cursor.fetchall()
    return jsonify([{'id': row[0], 'title': row[1], 'description': row[2]} for row in tasks]), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
