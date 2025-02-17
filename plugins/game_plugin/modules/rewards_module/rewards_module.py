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
        """Handles updating user points, levels, and guessed names per category & level."""
        data = request.get_json()
        user_id = data.get("user_id")
        category = data.get("category")
        level = data.get("level")
        new_points = data.get("points")
        guessed_names = data.get("guessed_names", [])  # ✅ List of guessed names

        if not user_id or not category or level is None or new_points is None:
            return jsonify({"error": "Missing required fields"}), 400

        # ✅ Get FunctionHelperModule
        module_manager = self.app_manager.module_manager if self.app_manager else ModuleManager()
        function_helper_module = module_manager.get_module("function_helper_module")

        if not function_helper_module:
            return jsonify({"error": "FunctionHelperModule not available"}), 500

        # ✅ Load categories data (pure Python dictionary)
        category_data = function_helper_module._load_categories_data()

        # ✅ Get max level for the category
        max_level = category_data.get(category, {}).get("levels", 1)

        # ✅ Fetch current progress
        progress_query = """
        SELECT points FROM user_category_progress WHERE user_id = %s AND category = %s AND level = %s
        """
        progress_data = self.connection_module.fetch_from_db(progress_query, (user_id, category, level), as_dict=True)

        current_points = progress_data[0]["points"] if progress_data else 0

        # ✅ Only update if new points are greater
        if new_points > current_points:
            if progress_data:
                update_query = """
                UPDATE user_category_progress SET points = %s WHERE user_id = %s AND category = %s AND level = %s
                """
                self.connection_module.execute_query(update_query, (new_points, user_id, category, level))
                custom_log(f"🔄 Updated points for user {user_id} in {category} Level {level}: {new_points}")
            else:
                insert_query = """
                INSERT INTO user_category_progress (user_id, category, level, points) VALUES (%s, %s, %s, %s)
                """
                self.connection_module.execute_query(insert_query, (user_id, category, level, new_points))
                custom_log(f"✅ Inserted new progress for user {user_id} in {category} Level {level}: {new_points}")

        # ✅ Process guessed names
        if guessed_names:
            custom_log(f"📜 Received guessed names for user {user_id} in {category} Level {level}: {guessed_names}")

            for guessed_name in guessed_names:
                check_query = """
                SELECT id FROM guessed_names WHERE user_id = %s AND category = %s AND level = %s AND guessed_name = %s
                """
                existing_record = self.connection_module.fetch_from_db(check_query, (user_id, category, level, guessed_name))

                if not existing_record:
                    insert_query = """
                    INSERT INTO guessed_names (user_id, category, level, guessed_name) VALUES (%s, %s, %s, %s)
                    """
                    self.connection_module.execute_query(insert_query, (user_id, category, level, guessed_name))
                    custom_log(f"✅ Added guessed name '{guessed_name}' for user {user_id} in {category} Level {level}.")

        # ✅ Determine if we should level up or end the game
        level_up = False
        end_game = False

        if level < max_level:
            level_up = True  # ✅ Move to the next level
            custom_log(f"🎯 User {user_id} leveled up in {category} to Level {level + 1}")
        else:
            end_game = True  # ✅ No more levels available
            custom_log(f"🏆 User {user_id} reached max level in {category}. Game Over.")

        return jsonify({
            "message": "Rewards updated successfully",
            "updated_points": max(new_points, current_points),
            "levelUp": level_up,
            "endGame": end_game
        }), 200
