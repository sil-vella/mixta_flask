import bcrypt
import hashlib
from flask import request, jsonify
from tools.logger.custom_logging import custom_log
from core.managers.module_manager import ModuleManager
import jwt
import yaml
import os
from datetime import datetime, timedelta
class LoginModule:
    def __init__(self, app_manager=None):
        """Initialize the LoginModule."""
        self.app_manager = app_manager
        self.connection_module = self.get_connection_module()
        self.SECRET_KEY = "your_secret_key"

        if not self.connection_module:
            raise RuntimeError("LoginModule: Failed to retrieve ConnectionModule from ModuleManager.")

        custom_log("✅ LoginModule initialized.")

    def get_connection_module(self):
        """Retrieve ConnectionModule from ModuleManager."""
        module_manager = self.app_manager.module_manager if self.app_manager else ModuleManager()
        connection_module = module_manager.get_module("connection_module")

        if not connection_module:
            custom_log("❌ ConnectionModule not found in ModuleManager.")
        
        return connection_module


    def register_routes(self):
        """Register authentication routes."""
        if not self.connection_module:
            raise RuntimeError("ConnectionModule is not available yet.")

        self.connection_module.register_route('/register', self.register_user, methods=['POST'])
        self.connection_module.register_route('/login', self.login_user, methods=['POST'])
        self.connection_module.register_route('/delete-user', self.delete_user_request, methods=['POST'])  # ✅ Register route

        custom_log("🌐 LoginModule: Authentication routes registered successfully.")

    def delete_user_request(self):
        """API Endpoint to delete a user and their data."""
        try:
            data = request.get_json()
            user_id = data.get("user_id")

            if not user_id:
                return jsonify({"error": "User ID is required"}), 400

            # ✅ Call the proper delete method
            response, status_code = self.delete_user_data(user_id)
            return jsonify(response), status_code

        except Exception as e:
            custom_log(f"❌ Error in delete-user API: {e}")
            return jsonify({"error": "Server error"}), 500



    def hash_password(self, password):
        """Hash the password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

    def check_password(self, password, hashed_password):
        """Check if a given password matches the stored hash."""
        return bcrypt.checkpw(password.encode(), hashed_password.encode())

    def _save_guessed_names(self, user_id, guessed_names):
        """Saves guessed names per category & level."""
        try:
            insert_query = """
            INSERT INTO guessed_names (user_id, category, level, guessed_name) 
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE guessed_name = guessed_name;
            """

            for category, levels in guessed_names.items():
                for level, names in levels.items():
                    for name in names:
                        self.connection_module.execute_query(insert_query, (user_id, category, level, name))

            custom_log(f"✅ Guessed names saved for user {user_id}: {guessed_names}")

        except Exception as e:
            custom_log(f"❌ Error saving guessed names: {e}")

    def _save_guessed_names(self, user_id, guessed_names):
        """Stores guessed names per category & level."""
        try:
            insert_query = """
            INSERT INTO guessed_names (user_id, category, level, guessed_name) 
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE guessed_name = guessed_name;
            """

            for category, levels in guessed_names.items():
                for level_str, names in levels.items():
                    level = int(level_str.replace("level_", ""))  # ✅ Convert "level_1" -> 1

                    for name in names:
                        self.connection_module.execute_query(insert_query, (user_id, category, level, name))

            custom_log(f"✅ Guessed names saved for user {user_id}: {guessed_names}")

        except Exception as e:
            custom_log(f"❌ Error saving guessed names: {e}")


    def _get_category_progress(self, user_id):
        """Fetches category-based levels & points."""
        query = """
        SELECT category, level, points FROM user_category_progress WHERE user_id = %s;
        """
        result = self.connection_module.fetch_from_db(query, (user_id,), as_dict=True)

        return {row["category"]: {"level": row["level"], "points": row["points"]} for row in result} if result else {}

    def _save_category_progress(self, user_id, category_progress):
        """Saves user points & levels per category."""
        try:
            for category, progress in category_progress.items():
                points = progress.get("points", 0)
                level = int(progress.get("level", 1))  # ✅ Ensure level is an integer

                insert_query = """
                INSERT INTO user_category_progress (user_id, category, level, points)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE points = VALUES(points), level = VALUES(level);
                """
                self.connection_module.execute_query(insert_query, (user_id, category, level, points))

            custom_log(f"✅ Category progress saved for user {user_id}: {category_progress}")

        except Exception as e:
            custom_log(f"❌ Error saving category progress: {e}")


    def register_user(self):
        """Handles user registration with category-based progress & guessed names."""
        try:
            data = request.get_json()
            username = data.get("username")
            email = data.get("email")
            password = data.get("password")
            category_progress = data.get("category_progress", {})
            guessed_names = data.get("guessed_names", {})

            if not username or not email or not password:
                return jsonify({"error": "Missing required fields"}), 400

            # ✅ Check if email already exists
            query = "SELECT id FROM users WHERE email = %s;"
            existing_user = self.connection_module.fetch_from_db(query, (email,))
            if existing_user:
                return jsonify({"error": "Email is already registered"}), 400

            # ✅ Insert new user
            hashed_password = self.hash_password(password)
            insert_user_query = "INSERT INTO users (username, email, password) VALUES (%s, %s, %s);"
            self.connection_module.execute_query(insert_user_query, (username, email, hashed_password))

            user_id_query = "SELECT id FROM users WHERE email = %s;"
            user_result = self.connection_module.fetch_from_db(user_id_query, (email,))

            if not user_result:
                return jsonify({"error": "User registration failed. No user found after insert."}), 500

            # ✅ Fix: Use index instead of dictionary key if needed
            user_id = user_result[0][0] if isinstance(user_result[0], tuple) else user_result[0]["id"]


            # ✅ Save category progress & guessed names
            self._save_category_progress(user_id, category_progress)
            self._save_guessed_names(user_id, guessed_names)

            return jsonify({"message": "User registered successfully"}), 200

        except Exception as e:
            custom_log(f"❌ Error registering user: {e}")
            return jsonify({"error": f"Server error: {str(e)}"}), 500

    def login_user(self):
        """Handles user login and retrieves category-based progress & guessed names."""
        try:
            data = request.get_json()
            email = data.get("email")
            password = data.get("password")

            query = "SELECT id, username, password FROM users WHERE email = %s;"
            user = self.connection_module.fetch_from_db(query, (email,), as_dict=True)

            if not user or not self.check_password(password, user[0]['password']):
                return jsonify({"error": "Invalid credentials"}), 401

            user_id = user[0]['id']
            category_progress = self._get_category_progress(user_id)
            guessed_names = self._get_guessed_names(user_id)

            custom_log(f"❌ category prog {category_progress}")


            token = jwt.encode({"user_id": user_id, "exp": datetime.utcnow() + timedelta(hours=24)}, self.SECRET_KEY, algorithm="HS256")

            return jsonify({"message": "Login successful", "user": {"id": user_id, "username": user[0]["username"], "category_progress": category_progress, "guessed_names": guessed_names}, "token": token}), 200

        except Exception as e:
            custom_log(f"❌ Error during login: {e}")
            return jsonify({"error": "Server error"}), 500

    def _get_guessed_names(self, user_id):
        """Retrieves guessed names grouped by category & level."""
        try:
            query = """
            SELECT category, level, guessed_name 
            FROM guessed_names WHERE user_id = %s;
            """
            results = self.connection_module.fetch_from_db(query, (user_id,), as_dict=True)

            guessed_names = {}

            for row in results:
                category = row["category"]
                level = f"level_{row['level']}"  # ✅ Convert 1 -> "level_1"
                name = row["guessed_name"]

                if category not in guessed_names:
                    guessed_names[category] = {}

                if level not in guessed_names[category]:
                    guessed_names[category][level] = []

                guessed_names[category][level].append(name)

            custom_log(f"📜 Retrieved guessed names for user {user_id}: {guessed_names}")
            return guessed_names

        except Exception as e:
            custom_log(f"❌ Error fetching guessed names: {e}")
            return {}

    def delete_user_data(self, user_id):
        """Delete all data associated with a user before removing them from the database."""
        try:
            if not self.connection_module:
                return {"error": "Database connection is unavailable"}, 500

            # ✅ Delete guessed names
            custom_log(f"🗑️ Deleting guessed names for User ID {user_id}...")
            self.connection_module.execute_query("DELETE FROM guessed_names WHERE user_id = %s", (user_id,))

            # ✅ Delete user progress
            custom_log(f"🗑️ Deleting category progress for User ID {user_id}...")
            self.connection_module.execute_query("DELETE FROM user_category_progress WHERE user_id = %s", (user_id,))

            # ✅ Finally, delete the user
            custom_log(f"🗑️ Deleting User ID {user_id} from users table...")
            self.connection_module.execute_query("DELETE FROM users WHERE id = %s", (user_id,))

            custom_log(f"✅ Successfully deleted all data for User ID {user_id}.")
            return {"message": f"User ID {user_id} and all associated data deleted successfully"}, 200

        except Exception as e:
            custom_log(f"❌ Error deleting user data: {e}")
            return {"error": f"Failed to delete user data: {str(e)}"}, 500
