from flask import Flask, request, jsonify
import logging
import os
import psycopg2
from psycopg2 import IntegrityError, OperationalError

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


def get_db_connection():
    """Return a database connection using environment-driven settings."""
    try:
        return psycopg2.connect(
            dbname=os.getenv('POSTGRES_DB', 'appdb'),
            user=os.getenv('POSTGRES_USER', 'appuser'),
            password=os.getenv('POSTGRES_PASSWORD', 'apppassword'),
            host=os.getenv('POSTGRES_HOST', 'postgres'),
            port=os.getenv('POSTGRES_PORT', '5432')
        )
    except OperationalError as exc:
        logging.error("Database connection failed: %s", exc)
        return None


def init_db():
    """Ensure the users table exists before serving requests."""
    conn = get_db_connection()
    if not conn:
        logging.warning("Skipping user table initialization; database unavailable")
        return
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL
                );
                """
            )
    except Exception as exc:
        logging.error("Failed to initialize users table: %s", exc)
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
        <title>User Service</title>
    </head>
    <body>
        <h1>Welcome to the User Service API</h1>
        <p>Available Endpoints:</p>
        <ul>
            <li><strong>POST /register:</strong> Register a new user</li>
            <li><strong>GET /users:</strong> Retrieve all users</li>
        </ul>
    </body>
    </html>
    """, 200


@app.route('/health', methods=['GET'])
@app.route('/api/user/health', methods=['GET'])
def health():
    """Health endpoint that validates database connectivity."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'status': 'unhealthy', 'error': 'Database connection failed'}), 500
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
        return jsonify({'status': 'healthy'}), 200
    except Exception as exc:
        logging.error("Health check failed: %s", exc)
        return jsonify({'status': 'unhealthy', 'error': 'Query failed'}), 500
    finally:
        conn.close()


@app.route('/register', methods=['POST'])
@app.route('/api/user/register', methods=['POST'])
def register_user():
    """Endpoint to register a new user."""
    user = request.json
    if not user or 'name' not in user or 'email' not in user:
        return jsonify({'error': 'Invalid user data. "name" and "email" are required.'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id",
                    (user['name'], user['email'])
                )
                user_id = cur.fetchone()[0]
        logging.info("User registered: %s", user)
        return jsonify({'message': 'User registered successfully', 'user': {'id': user_id, 'name': user['name'], 'email': user['email']}}), 201
    except IntegrityError:
        conn.rollback()
        logging.error("Email already exists: %s", user['email'])
        return jsonify({'error': 'A user with this email already exists.'}), 409
    except Exception as exc:
        conn.rollback()
        logging.error("Error registering user: %s", exc)
        return jsonify({'error': 'An error occurred while registering the user.'}), 500
    finally:
        conn.close()


@app.route('/users', methods=['GET'])
@app.route('/api/user/users', methods=['GET'])
def get_users():
    """Endpoint to retrieve all registered users."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed.'}), 500

    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, name, email FROM users ORDER BY id ASC')
            users = cur.fetchall()
        logging.info("Retrieved all users.")
        return jsonify([{'id': row[0], 'name': row[1], 'email': row[2]} for row in users]), 200
    except Exception as exc:
        logging.error("Error retrieving users: %s", exc)
        return jsonify({'error': 'An error occurred while retrieving users.'}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
