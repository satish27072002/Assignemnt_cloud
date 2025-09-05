from flask import Flask, request, jsonify
import logging
import os
import psycopg2

POSTGRES_DB = os.getenv("POSTGRES_DB", "appdb")
POSTGRES_USER = os.getenv("POSTGRES_USER", "appuser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "apppassword")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")


def get_db_connection():
    """Create and return a new PostgreSQL connection using env vars."""
    return psycopg2.connect(
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
    )


_db_initialized = False


def init_db():
    """Initialize database tables if not already created."""
    global _db_initialized
    if _db_initialized:
        return
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            );
            """
        )
        conn.commit()
        cur.close()
        conn.close()
        _db_initialized = True
    except Exception as e:
        # Defer initialization; health/readiness will surface availability
        logging.warning(f"DB init deferred, will retry on demand: {e}")

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Define the root route
@app.route('/')
@app.route('/user')
@app.route('/user/')
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
        <p><strong>GET /health:</strong> Service health status</p>
    </body>
    </html>
    """, 200


@app.route('/register', methods=['POST'])
@app.route('/user/register', methods=['POST'])
def register_user():
    """Endpoint to register a new user."""
    try:
        init_db()
        user = request.json  # Get the JSON data from the request
        if not user or 'name' not in user or 'email' not in user:
            return jsonify({'error': 'Invalid user data. "name" and "email" are required.'}), 400

        # Connect to the database
        conn = get_db_connection()
        cur = conn.cursor()

        # Insert user into the database
        cur.execute(
            "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id",
            (user['name'], user['email'])
        )
        user_id = cur.fetchone()[0]
        conn.commit()

        # Close database connection
        cur.close()
        conn.close()

        logging.info(f"User registered: {user}")
        return jsonify({'message': 'User registered successfully', 'user': {'id': user_id, 'name': user['name'], 'email': user['email']}}), 201
    except psycopg2.IntegrityError:
        logging.error("Email already exists.")
        return jsonify({'error': 'A user with this email already exists.'}), 409
    except Exception as e:
        logging.error(f"Error registering user: {e}")
        return jsonify({'error': 'An error occurred while registering the user.'}), 500

@app.route('/users', methods=['GET'])
@app.route('/user/users', methods=['GET'])
def get_users():
    """Endpoint to retrieve all registered users."""
    try:
        init_db()
        # Connect to the database
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch all users from the database
        cur.execute("SELECT id, name, email FROM users")
        users = cur.fetchall()

        # Close database connection
        cur.close()
        conn.close()

        logging.info("Retrieved all users.")
        return jsonify([{'id': user[0], 'name': user[1], 'email': user[2]} for user in users]), 200
    except Exception as e:
        logging.error(f"Error retrieving users: {e}")
        return jsonify({'error': 'An error occurred while retrieving users.'}), 500


@app.route('/health', methods=['GET'])
@app.route('/user/health', methods=['GET'])
def health():
    try:
        init_db()
        conn = get_db_connection()
        conn.close()
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
