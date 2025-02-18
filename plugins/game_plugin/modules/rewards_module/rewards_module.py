from flask import request, jsonify
from tools.logger.custom_logging import custom_log
from core.managers.module_manager import ModuleManager
from plugins.game_plugin.modules.question_module.question_module import NAMES_YAML_PATH  # ✅ Import it directly

class RewardsModule:
    def __init__(self, app_manager=None):
        """Initialize RewardsModule and retrieve necessary modules."""
        self.app_manager = app_manager
        self.connection_module = self.get_connection_module()
        self.question_module = self.get_question_module()  # ✅ Get QuestionModule

        if not self.connection_module:
            raise RuntimeError("RewardsModule: Failed to retrieve ConnectionModule from ModuleManager.")
        if not self.question_module:
            raise RuntimeError("RewardsModule: Failed to retrieve QuestionModule from ModuleManager.")

        self.register_routes()
        custom_log("✅ RewardsModule initialized.")

    def get_connection_module(self):
        """Retrieve ConnectionModule from ModuleManager."""
        module_manager = self.app_manager.module_manager if self.app_manager else ModuleManager()
        return module_manager.get_module("connection_module")

    def get_question_module(self):
        """Retrieve QuestionModule from ModuleManager."""
        module_manager = self.app_manager.module_manager if self.app_manager else ModuleManager()
        return module_manager.get_module("question_module")  # ✅ Ensure module name matches

    def _get_names_from_yaml(self, category, level):
        """Retrieve all names for a category and level from YAML using QuestionModule."""
        if not self.question_module:
            custom_log("❌ QuestionModule is not available.")
            return []

        # ✅ Ensure the path exists inside QuestionModule
        if not hasattr(self.question_module, "NAMES_YAML_PATH"):
            custom_log("❌ QuestionModule does not have NAMES_YAML_PATH defined.")
            return []

        questions = self.question_module.load_yaml(self.question_module.NAMES_YAML_PATH)

        if not questions or str(level) not in questions:
            return []

        all_names = [
            actor.lower() for actor, data in questions[str(level)].items()
            if category in [c.lower() for c in data.get("categories", [])]
        ]

        return all_names


    def register_routes(self):
        """Register rewards route."""
        if not self.connection_module:
            raise RuntimeError("ConnectionModule is not available yet.")

        self.connection_module.register_route('/update-rewards', self.update_rewards, methods=['POST'])
        custom_log("🌐 RewardsModule: `/update-rewards` route registered.")

    def update_rewards(self):
        """Handles updating user points, levels, and guessed names per category & level."""
        custom_log(f"📢 [update_rewards] Request received: {request.get_json()}")

        data = request.get_json()
        user_id = data.get("user_id")
        category = data.get("category")
        level = data.get("level")
        new_points = data.get("points")
        guessed_names = data.get("guessed_names", [])  # ✅ List of guessed names

        if not user_id or not category or level is None or new_points is None:
            custom_log("❌ [update_rewards] Missing required fields.")
            return jsonify({"error": "Missing required fields"}), 400

        # ✅ Get FunctionHelperModule
        custom_log("🔍 Fetching FunctionHelperModule...")
        module_manager = self.app_manager.module_manager if self.app_manager else ModuleManager()
        function_helper_module = module_manager.get_module("function_helper_module")

        if not function_helper_module:
            custom_log("❌ [update_rewards] FunctionHelperModule not available.")
            return jsonify({"error": "FunctionHelperModule not available"}), 500

        # ✅ Load categories data and log the max level
        category_data = function_helper_module._load_categories_data()
        max_level = int(category_data.get(category, {}).get("levels", 1))

        custom_log(f"📊 Loaded category data for '{category}': {category_data.get(category)} | Max Level: {max_level}")

        # ✅ Fetch all available names for this level from YAML
        all_names_at_level = self._get_names_from_yaml(category, level)
        custom_log(f"📜 All possible names for '{category}' Level {level}: {all_names_at_level}")

        # ✅ Fetch already guessed names from database
        db_guessed_names_query = """
        SELECT guessed_name FROM guessed_names WHERE user_id = %s AND category = %s AND level = %s
        """
        custom_log(f"📡 Fetching guessed names from DB for User {user_id} in Category '{category}' Level {level}...")
        db_guessed_names = self.connection_module.fetch_from_db(db_guessed_names_query, (user_id, category, level))
        db_guessed_names = [row[0] for row in db_guessed_names] if db_guessed_names else []


        # ✅ Merge new guessed names with existing ones
        all_guessed = set(db_guessed_names + guessed_names)
        custom_log(f"📌 User {user_id} guessed so far in {category} Level {level}: {all_guessed}")

        # ✅ Fetch current progress
        progress_query = """
        SELECT points FROM user_category_progress WHERE user_id = %s AND category = %s AND level = %s
        """
        custom_log(f"📡 Fetching current progress from DB for User {user_id} in Category '{category}' Level {level}...")
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
            custom_log(f"📜 New guessed names for user {user_id} in {category} Level {level}: {guessed_names}")

            for guessed_name in guessed_names:
                if guessed_name not in db_guessed_names:
                    insert_query = """
                    INSERT INTO guessed_names (user_id, category, level, guessed_name) VALUES (%s, %s, %s, %s)
                    """
                    self.connection_module.execute_query(insert_query, (user_id, category, level, guessed_name))
                    custom_log(f"✅ Added guessed name '{guessed_name}' for user {user_id} in {category} Level {level}.")

        # ✅ Determine if we should level up or end the game
        level_up = False
        end_game = False

        if len(all_guessed) >= len(all_names_at_level):  # ✅ Level up only if all names are guessed
            if level < max_level:
                level_up = True
                custom_log(f"🎯 User {user_id} leveled up in {category} to Level {level + 1}")
            else:
                end_game = True
                custom_log(f"🏆 User {user_id} reached max level in {category}. Game Over.")

        response = {
            "message": "Rewards updated successfully",
            "updated_points": max(new_points, current_points),
            "levelUp": level_up,
            "endGame": end_game
        }

        custom_log(f"✅ [update_rewards] Response Sent: {response}")
        return jsonify(response), 200
