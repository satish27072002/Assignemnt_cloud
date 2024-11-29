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

# Create users table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
)
""")
conn.commit()

@app.route('/register', methods=['POST'])
def register_user():
    user = request.json  # Get the JSON data from the request
    if not user or 'name' not in user or 'email' not in user:
        return jsonify({'error': 'Invalid user data'}), 400

    try:
        cursor.execute("INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id", (user['name'], user['email']))
        conn.commit()
        user_id = cursor.fetchone()[0]
        return jsonify({'message': 'User registered successfully', 'user_id': user_id}), 201
    except psycopg2.Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/users', methods=['GET'])
def get_users():
    cursor.execute("SELECT id, name, email FROM users")
    users = cursor.fetchall()
    return jsonify([{'id': row[0], 'name': row[1], 'email': row[2]} for row in users]), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
