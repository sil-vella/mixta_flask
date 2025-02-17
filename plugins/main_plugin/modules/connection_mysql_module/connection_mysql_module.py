import mysql.connector
import os
from tools.logger.custom_logging import custom_log

class ConnectionMySqlModule:
    def __init__(self, app_manager=None):
        self.registered_routes = []
        self.app = None  # Reference to Flask app
        self.db_connection = self.connect_to_db()  # Initialize DB connection
        self.app_manager = app_manager  # Reference to AppManager if provided

        # ✅ Ensure tables exist in the database
        self.initialize_database()

    def initialize(self, app):
        """Initialize the ConnectionMySqlModule with a Flask app."""
        if not hasattr(app, "add_url_rule"):
            raise RuntimeError("ConnectionMySqlModule requires a valid Flask app instance.")
        self.app = app

    def connect_to_db(self):
        """Establish a connection to the MySQL database and return the connection object."""
        try:
            connection = mysql.connector.connect(
                user=os.getenv("MYSQL_USER"),
                password=os.getenv("MYSQL_PASSWORD"),
                host=os.getenv("DB_HOST", "127.0.0.1"),
                port=os.getenv("DB_PORT", "3306"),
                database=os.getenv("MYSQL_DB")
            )
            custom_log("✅ Database connection established")
            return connection
        except Exception as e:
            custom_log(f"❌ Error connecting to database: {e}")
            return None

    def get_connection(self):
        """Retrieve an active database connection."""
        if self.db_connection is None or not self.db_connection.is_connected():
            custom_log("🔄 Reconnecting to database...")
            self.db_connection = self.connect_to_db()
        return self.db_connection

    def fetch_from_db(self, query, params=None, as_dict=False):
        """Execute a SELECT query and return results."""
        try:
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=as_dict)
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            cursor.close()
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
        self._create_user_category_progress_table()
        self._create_guessed_names_table()

        custom_log("✅ Database tables verified.")

    def _create_users_table(self):
        """Create users table if it doesn't exist."""
        query = """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.execute_query(query)
        custom_log("✅ Users table verified.")

    def _create_user_category_progress_table(self):
        """Create table to track user levels and points per category."""
        query = """
        CREATE TABLE IF NOT EXISTS user_category_progress (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            category VARCHAR(50) NOT NULL,
            points INT DEFAULT 0,
            level INT DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE (user_id, category)  -- Ensures each user has only one entry per category
        );
        """
        self.execute_query(query)
        custom_log("✅ User category progress table verified.")

    def _create_guessed_names_table(self):
        """Create guessed_names table if it doesn't exist."""
        query = """
        CREATE TABLE IF NOT EXISTS guessed_names (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            category VARCHAR(50) NOT NULL,
            guessed_name VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
        self.execute_query(query)
        custom_log("✅ Guessed names table verified.")

    def register_route(self, path, view_func, methods=None, endpoint=None):
        """Register a route with the Flask app."""
        if self.app is None:
            raise RuntimeError("ConnectionMySqlModule must be initialized with a Flask app before registering routes.")

        methods = methods or ["GET"]
        endpoint = endpoint or view_func.__name__  # If no endpoint is provided, use the function name

        self.app.add_url_rule(path, endpoint=endpoint, view_func=view_func, methods=methods)
        self.registered_routes.append((path, methods))
        custom_log(f"🌐 Route registered: {path} [{', '.join(methods)}] as '{endpoint}'")

    def dispose(self):
        """Clean up registered routes and resources."""
        custom_log("🔄 Disposing ConnectionMySqlModule...")
        self.registered_routes.clear()
        if self.db_connection:
            self.db_connection.close()
            custom_log("🔌 Database connection closed.")
