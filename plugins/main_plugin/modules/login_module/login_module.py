import bcrypt
import hashlib
from flask import request, jsonify
from tools.logger.custom_logging import custom_log
from core.managers.module_manager import ModuleManager
import jwt
from datetime import datetime, timedelta

class LoginModule:
    def __init__(self, app_manager=None):
        """Initialize the LoginModule without registering routes immediately."""
        self.app_manager = app_manager  # Reference to AppManager if provided
        self.connection_module = self.get_connection_module()
        self.SECRET_KEY = "your_secret_key"

        if not self.connection_module:
            raise RuntimeError("LoginModule: Failed to retrieve ConnectionModule from ModuleManager.")

        custom_log("LoginModule initialized. Waiting for ConnectionModule initialization.")

    def get_connection_module(self):
        """Retrieve ConnectionModule from ModuleManager."""
        module_manager = self.app_manager.module_manager if self.app_manager else ModuleManager()
        return module_manager.get_module("connection_module")

    def register_routes(self):
        """Register authentication routes only after ConnectionModule is ready."""
        if not self.connection_module:
            raise RuntimeError("ConnectionModule is not available yet.")

        self.connection_module.register_route('/register', self.register_user, methods=['POST'])
        self.connection_module.register_route('/login', self.login_user, methods=['POST'])
        custom_log("LoginModule: Authentication routes registered successfully.")

    def hash_password(self, password):
        """Hash the password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

    def check_password(self, password, hashed_password):
        """Check if a given password matches the stored hash."""
        return bcrypt.checkpw(password.encode(), hashed_password.encode())

    def _save_guessed_names(self, user_id, guessed_names):
        """Saves guessed names from the request into the database."""
        try:
            insert_query = """
            INSERT INTO guessed_names (user_id, category, guessed_name) VALUES (%s, %s, %s);
            """

            for category, levels in guessed_names.items():
                for level, names in levels.items():
                    for name in names:
                        self.connection_module.execute_query(insert_query, (user_id, category, name))

            custom_log(f"✅ Guessed names saved for user {user_id}: {guessed_names}")

        except Exception as e:
            custom_log(f"❌ Error saving guessed names: {e}")

    def _get_guessed_names(self, user_id):
        """Retrieves guessed names from the database, grouped by category and level."""
        try:
            query = """
            SELECT category, guessed_name FROM guessed_names WHERE user_id = %s;
            """
            results = self.connection_module.fetch_from_db(query, (user_id,), as_dict=True)

            guessed_names = {}

            for row in results:
                category = row["category"]
                name = row["guessed_name"]

                if category not in guessed_names:
                    guessed_names[category] = []

                guessed_names[category].append(name)

            custom_log(f"📜 Retrieved guessed names for user {user_id}: {guessed_names}")
            return guessed_names

        except Exception as e:
            custom_log(f"❌ Error fetching guessed names: {e}")
            return {}


    def _get_category_progress(self, user_id):
        """Fetches category-based levels and points for the user."""
        query = """
            SELECT category, level, points
            FROM user_category_progress
            WHERE user_id = %s;
        """
        result = self.connection_module.fetch_from_db(query, (user_id,), as_dict=True)

        if not result:
            return {}  # ✅ Return empty if no progress found

        # ✅ Convert to a dictionary format: { "actors": {"level": 1, "points": 90}, ... }
        return {row["category"]: {"level": row["level"], "points": row["points"]} for row in result}

    def _save_category_progress(self, user_id, category_progress):
        """Saves user points & levels per category in the database."""
        try:
            for category, progress in category_progress.items():
                points = progress.get("points", 0)
                level = progress.get("level", 1)

                insert_query = """
                INSERT INTO user_category_progress (user_id, category, points, level)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE points = VALUES(points), level = VALUES(level);
                """
                self.connection_module.execute_query(insert_query, (user_id, category, points, level))

            custom_log(f"✅ Category progress saved for user {user_id}: {category_progress}")

        except Exception as e:
            custom_log(f"❌ Error saving category progress: {e}")

    def register_user(self):
        """Handles user registration and saves category-based progress in the database."""
        try:
            data = request.get_json()
            username = data.get("username")
            email = data.get("email")
            password = data.get("password")
            category_progress = data.get("category_progress", {})  # ✅ Category-based points & levels
            guessed_names = data.get("guessed_names", {})  # ✅ Guessed names per category

            if not username or not email or not password:
                return jsonify({"error": "Missing required fields"}), 400

            # ✅ Check if email already exists
            query = "SELECT id FROM users WHERE email = %s;"
            existing_user = self.connection_module.fetch_from_db(query, (email,))
            if existing_user:
                return jsonify({"error": "Email is already registered"}), 400

            # ✅ Hash the password before saving
            hashed_password = self.hash_password(password)

            # ✅ Insert new user into the database
            insert_user_query = """
            INSERT INTO users (username, email, password) VALUES (%s, %s, %s);
            """
            self.connection_module.execute_query(insert_user_query, (username, email, hashed_password))

            # ✅ Retrieve the newly created user's ID
            user_id_query = "SELECT id FROM users WHERE email = %s;"
            user_result = self.connection_module.fetch_from_db(user_id_query, (email,))
            if not user_result:
                return jsonify({"error": "User registration failed"}), 500

            user_id = user_result[0]["id"]
            custom_log(f"✅ User registered successfully with ID: {user_id}")

            # ✅ Save category progress (points & levels)
            self._save_category_progress(user_id, category_progress)

            # ✅ Save guessed names to the database
            self._save_guessed_names(user_id, guessed_names)

            return jsonify({"message": "User registered successfully"}), 200

        except Exception as e:
            custom_log(f"❌ Error registering user: {e}")
            return jsonify({"error": f"Server error: {str(e)}"}), 500


    def login_user(self):
        """Handles user login and retrieves category-based levels and points."""
        try:
            data = request.get_json()
            email = data.get("email")
            password = data.get("password")

            if not email or not password:
                return jsonify({"error": "Missing email or password"}), 400

            # ✅ Fetch user details from database
            query = "SELECT id, username, password FROM users WHERE email = %s;"
            user = self.connection_module.fetch_from_db(query, (email,), as_dict=True)

            if not user or not self.check_password(password, user[0]['password']):
                return jsonify({"error": "Invalid credentials"}), 401

            user_id = user[0]['id']

            # ✅ Retrieve category-based levels and points
            category_progress = self._get_category_progress(user_id)

            # ✅ Retrieve guessed names from database
            guessed_names = self._get_guessed_names(user_id)

            # ✅ Generate JWT Token
            token = jwt.encode({
                "user_id": user_id,
                "exp": datetime.utcnow() + timedelta(hours=24)  # Token expires in 24 hours
            }, self.SECRET_KEY, algorithm="HS256")

            return jsonify({
                "message": "Login successful",
                "user": {
                    "id": user_id,
                    "username": user[0]["username"],
                    "category_progress": category_progress,  # ✅ Returns category-based levels and points
                    "guessed_names": guessed_names  # ✅ Include guessed names
                },
                "token": token
            }), 200

        except Exception as e:
            custom_log(f"❌ Error during login: {e}")
            return jsonify({"error": "Server error"}), 500


