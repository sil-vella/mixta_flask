from flask import request, jsonify
from tools.logger.custom_logging import custom_log
from core.managers.module_manager import ModuleManager

class RewardsModule:
    def __init__(self, app_manager=None):
        """Initialize RewardsModule and register routes."""
        self.app_manager = app_manager
        self.connection_module = self.get_connection_module()

        if not self.connection_module:
            raise RuntimeError("RewardsModule: Failed to retrieve ConnectionModule from ModuleManager.")

        custom_log("✅ RewardsModule initialized.")
        self.register_routes()

    def get_connection_module(self):
        """Retrieve ConnectionModule from ModuleManager."""
        module_manager = self.app_manager.module_manager if self.app_manager else ModuleManager()
        return module_manager.get_module("connection_module")

    def register_routes(self):
        """Register rewards route."""
        if not self.connection_module:
            raise RuntimeError("ConnectionModule is not available yet.")

        self.connection_module.register_route('/update-rewards', self.update_rewards, methods=['GET'])
        custom_log("🌐 RewardsModule: `/update-rewards` route registered.")

from flask import request, jsonify
from tools.logger.custom_logging import custom_log
from core.managers.module_manager import ModuleManager

class RewardsModule:
    def __init__(self, app_manager=None):
        """Initialize RewardsModule and register routes."""
        self.app_manager = app_manager
        self.connection_module = self.get_connection_module()

        if not self.connection_module:
            raise RuntimeError("RewardsModule: Failed to retrieve ConnectionModule from ModuleManager.")

        custom_log("✅ RewardsModule initialized.")
        self.register_routes()

    def get_connection_module(self):
        """Retrieve ConnectionModule from ModuleManager."""
        module_manager = self.app_manager.module_manager if self.app_manager else ModuleManager()
        return module_manager.get_module("connection_module")

    def register_routes(self):
        """Register rewards route."""
        if not self.connection_module:
            raise RuntimeError("ConnectionModule is not available yet.")

        self.connection_module.register_route('/update-rewards', self.update_rewards, methods=['POST'])
        custom_log("🌐 RewardsModule: `/update-rewards` route registered.")

    def update_rewards(self):
        """Handles updating user points, level, and guessed names in the database."""
        data = request.get_json()
        user_id = data.get("user_id")
        username = data.get("username")
        email = data.get("email")
        new_points = data.get("points")
        new_level = data.get("level")
        guessed_names = data.get("guessed_names", {})  # ✅ Extract guessed names

        if not user_id or not username or not email or new_points is None or new_level is None:
            return jsonify({"error": "Missing required fields"}), 400

        # ✅ Fetch user from the database using user_id
        query = "SELECT username, email, points, level FROM users WHERE id = %s;"
        user = self.connection_module.fetch_from_db(query, (user_id,), as_dict=True)

        if not user:
            return jsonify({"error": "User not found"}), 404

        # ✅ Validate if the provided username and email match the user in the database
        db_user = user[0]
        if db_user["username"] != username or db_user["email"] != email:
            return jsonify({"error": "User details do not match"}), 401

        current_points = db_user["points"]
        current_level = db_user["level"]

        # ✅ Update only if values are higher than the current stored values
        updated_points = max(current_points, new_points)
        updated_level = max(current_level, new_level)

        if updated_points != current_points or updated_level != current_level:
            update_query = "UPDATE users SET points = %s, level = %s WHERE id = %s;"
            self.connection_module.execute_query(update_query, (updated_points, updated_level, user_id))
            custom_log(f"🔄 Updated user {user_id}: Points={updated_points}, Level={updated_level}")

        # ✅ Update guessed names in the database
        if guessed_names:
            custom_log(f"📜 Received guessed names for user {user_id}: {guessed_names}")

            for category, names in guessed_names.items():
                for guessed_name in names:
                    # ✅ Check if the guessed name already exists in the DB
                    check_query = """
                    SELECT id FROM guessed_names WHERE user_id = %s AND category = %s AND guessed_name = %s;
                    """
                    existing_record = self.connection_module.fetch_from_db(check_query, (user_id, category, guessed_name))

                    if not existing_record:
                        # ✅ Insert new guessed name into the DB
                        insert_query = """
                        INSERT INTO guessed_names (user_id, category, guessed_name) VALUES (%s, %s, %s);
                        """
                        self.connection_module.execute_query(insert_query, (user_id, category, guessed_name))
                        custom_log(f"✅ Added guessed name '{guessed_name}' for user {user_id} in category '{category}'.")

        return jsonify({
            "message": "Rewards updated successfully",
            "updated_points": updated_points,
            "updated_level": updated_level
        }), 200
