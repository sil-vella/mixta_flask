import psycopg2
import psycopg2.extras
import os
from tools.logger.custom_logging import custom_log, log_function_call

class ConnectionModule:
    def __init__(self, app_manager=None):
        self.registered_routes = []
        self.app = None  # Reference to Flask app
        self.db_connection = self.connect_to_db()  # Initialize DB connection
        self.app_manager = app_manager  # Reference to AppManager if provided

        # ✅ Ensure tables exist in the database
        self.initialize_database()

    def initialize(self, app):
        """Initialize the ConnectionModule with a Flask app."""
        if not hasattr(app, "add_url_rule"):
            raise RuntimeError("ConnectionModule requires a valid Flask app instance.")
        self.app = app

    def connect_to_db(self):
        """Establish a connection to the database and return the connection object."""
        try:
            connection = psycopg2.connect(
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
                host=os.getenv("DB_HOST", "127.0.0.1"),
                port=os.getenv("DB_PORT", "5432"),
                database=os.getenv("POSTGRES_DB")
            )
            custom_log("✅ Database connection established")
            return connection
        except Exception as e:
            custom_log(f"❌ Error connecting to database: {e}")
            return None

    def get_connection(self):
        """Retrieve an active database connection."""
        if self.db_connection is None or self.db_connection.closed:
            custom_log("🔄 Reconnecting to database...")
            self.db_connection = self.connect_to_db()
        return self.db_connection

    def fetch_from_db(self, query, params=None, as_dict=False):
        """Execute a SELECT query and return results."""
        try:
            connection = self.get_connection()
            cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor if as_dict else None)
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            cursor.close()

            if as_dict:
                return [dict(row) for row in result]
            return result
        except Exception as e:
            custom_log(f"❌ Error executing query: {e}")
            return None

    def execute_query(self, query, params=None):
        """Execute INSERT, UPDATE, or DELETE queries."""
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(query, params or ())
            connection.commit()
            cursor.close()
            custom_log("✅ Query executed successfully")
        except Exception as e:
            custom_log(f"❌ Error executing query: {e}")

    def initialize_database(self):
        """Ensure required tables exist in the database."""
        custom_log("⚙️ Initializing database tables...")

        self._create_users_table()
        self._create_scores_table()

        custom_log("✅ Database tables verified.")

    def _create_users_table(self):
        """Create users table if it doesn't exist."""
        query = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password TEXT NOT NULL,
            points INT DEFAULT 0,
            level INT DEFAULT 1,  -- ✅ Added level column with default 1
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.execute_query(query)
        custom_log("✅ Users table verified (Level column included).")


    def _create_scores_table(self):
        """Create scores table if it doesn't exist."""
        query = """
        CREATE TABLE IF NOT EXISTS scores (
            id SERIAL PRIMARY KEY,
            user_id INT REFERENCES users(id) ON DELETE CASCADE,
            points INT DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.execute_query(query)
        custom_log("✅ Scores table verified.")

    def register_route(self, path, view_func, methods=None, endpoint=None):
        """Register a route with the Flask app."""
        if self.app is None:
            raise RuntimeError("ConnectionModule must be initialized with a Flask app before registering routes.")

        methods = methods or ["GET"]
        endpoint = endpoint or view_func.__name__  # If no endpoint is provided, use the function name

        self.app.add_url_rule(path, endpoint=endpoint, view_func=view_func, methods=methods)
        self.registered_routes.append((path, methods))
        custom_log(f"🌐 Route registered: {path} [{', '.join(methods)}] as '{endpoint}'")

    def dispose(self):
        """Clean up registered routes and resources."""
        custom_log("🔄 Disposing ConnectionModule...")
        self.registered_routes.clear()
        if self.db_connection:
            self.db_connection.close()
            custom_log("🔌 Database connection closed.")
