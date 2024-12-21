from flask import Flask, request, jsonify
import logging
import psycopg2

# Database connection for table creation
conn = psycopg2.connect(
    dbname="appdb",
    user="appuser",
    password="apppassword",
    host="postgres",
    port="5432"
)
cur = conn.cursor()

# Create users table if it does not exist
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
);
""")
conn.commit()
cur.close()
conn.close()

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Define the root route
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


@app.route('/register', methods=['POST'])
def register_user():
    """Endpoint to register a new user."""
    try:
        user = request.json  # Get the JSON data from the request
        if not user or 'name' not in user or 'email' not in user:
            return jsonify({'error': 'Invalid user data. "name" and "email" are required.'}), 400

        # Connect to the database
        conn = psycopg2.connect(
            dbname="appdb",
            user="appuser",
            password="apppassword",
            host="postgres",
            port="5432"
        )
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
def get_users():
    """Endpoint to retrieve all registered users."""
    try:
        # Connect to the database
        conn = psycopg2.connect(
            dbname="appdb",
            user="appuser",
            password="apppassword",
            host="postgres",
            port="5432"
        )
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
