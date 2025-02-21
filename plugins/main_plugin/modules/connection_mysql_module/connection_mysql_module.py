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
            total_points INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.execute_query(query)
        custom_log("✅ Users table verified.")


    def _create_user_category_progress_table(self):
        """Create table to track user levels and points per category and level."""
        query = """
        CREATE TABLE IF NOT EXISTS user_category_progress (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            category VARCHAR(50) NOT NULL,
            level INT NOT NULL,
            points INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE (user_id, category, level)  -- Ensures each user has only one entry per category & level
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
            level INT NOT NULL DEFAULT 1,  -- ✅ Ensure level is included
            guessed_name VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE (user_id, category, level, guessed_name) -- ✅ Ensure unique guessed names per level
        );
        """
        self.execute_query(query)
        custom_log("✅ Guessed names table verified.")


    def add_guessed_name(self, user_id, category, level, guessed_name):
        """Add a guessed name for a specific user, category, and level."""
        query = """
        INSERT INTO guessed_names (user_id, category, level, guessed_name)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE guessed_name = guessed_name;
        """
        self.execute_query(query, (user_id, category, level, guessed_name))
        custom_log(f"✅ Added guessed name '{guessed_name}' for User {user_id} in {category} Level {level}")

    def get_guessed_names(self, user_id, category, level):
        """Retrieve guessed names for a user in a specific category and level."""
        query = "SELECT guessed_name FROM guessed_names WHERE user_id = %s AND category = %s AND level = %s"
        results = self.fetch_from_db(query, (user_id, category, level))
        return [row['guessed_name'] for row in results] if results else []

    def update_user_progress(self, user_id, category, level, points):
        """Update user points and level for a specific category, and update total points."""
        query = """
        INSERT INTO user_category_progress (user_id, category, level, points)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE points = points + %s;
        """
        self.execute_query(query, (user_id, category, level, points, points))

        # ✅ Update total points in users table
        total_query = """
        UPDATE users
        SET total_points = (SELECT COALESCE(SUM(points), 0) FROM user_category_progress WHERE user_id = %s)
        WHERE id = %s;
        """
        self.execute_query(total_query, (user_id, user_id))

        custom_log(f"✅ Updated progress: User {user_id} | {category} Level {level} | +{points} points")


    def get_user_progress(self, user_id, category, level):
        """Retrieve user points and level for a specific category."""
        query = "SELECT points FROM user_category_progress WHERE user_id = %s AND category = %s AND level = %s"
        result = self.fetch_from_db(query, (user_id, category, level), as_dict=True)
        return result[0] if result else {"points": 0}

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

    def get_all_user_data(self, user_id):
        """Retrieve all user data including profile, category progress, and guessed names."""
        try:
            # ✅ Fetch user details, including total_points
            user_query = "SELECT id, username, email, total_points, created_at FROM users WHERE id = %s"
            user_data = self.fetch_from_db(user_query, (user_id,), as_dict=True)

            if not user_data:
                return {"error": f"User with ID {user_id} not found"}, 404

            user_info = user_data[0]  # Extract user details

            # ✅ Fetch category progress (points and levels)
            progress_query = """
            SELECT category, level, points FROM user_category_progress WHERE user_id = %s
            """
            progress_data = self.fetch_from_db(progress_query, (user_id,), as_dict=True)
            
            category_progress = {}
            for row in progress_data:
                category = row["category"]
                level = row["level"]
                points = row["points"]

                if category not in category_progress:
                    category_progress[category] = {}
                category_progress[category][level] = {"points": points}

            # ✅ Fetch guessed names grouped by category and level
            guessed_query = """
            SELECT category, level, guessed_name FROM guessed_names WHERE user_id = %s
            """
            guessed_data = self.fetch_from_db(guessed_query, (user_id,), as_dict=True)

            guessed_names = {}
            for row in guessed_data:
                category = row["category"]
                level = row["level"]
                guessed_name = row["guessed_name"]

                if category not in guessed_names:
                    guessed_names[category] = {}
                if level not in guessed_names[category]:
                    guessed_names[category][level] = []
                
                guessed_names[category][level].append(guessed_name)

            # ✅ Include total_points in response
            user_response = {
                "user_info": user_info,
                "category_progress": category_progress,
                "guessed_names": guessed_names,
                "total_points": user_info["total_points"]  # ✅ Include total points
            }

            return user_response, 200

        except Exception as e:
            custom_log(f"❌ Error fetching user data: {e}")
            return {"error": f"Server error: {str(e)}"}, 500
