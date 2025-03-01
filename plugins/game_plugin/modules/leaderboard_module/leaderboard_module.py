from flask import request, jsonify
from tools.logger.custom_logging import custom_log
from core.managers.module_manager import ModuleManager

class LeaderboardModule:
    def __init__(self, app_manager=None):
        """Initialize LeaderboardModule and register routes."""
        self.app_manager = app_manager
        self.connection_module = self.get_connection_module()

        if not self.connection_module:
            raise RuntimeError("LeaderboardModule: Failed to retrieve ConnectionModule from ModuleManager.")

        custom_log("✅ LeaderboardModule initialized.")
        self.register_routes()

    def get_connection_module(self):
        """Retrieve ConnectionModule from ModuleManager."""
        module_manager = self.app_manager.module_manager if self.app_manager else ModuleManager()
        return module_manager.get_module("connection_module")

    def register_routes(self):
        """Register leaderboard route."""
        if not self.connection_module:
            raise RuntimeError("ConnectionModule is not available yet.")

        self.connection_module.register_route('/get-leaderboard', self.get_leaderboard, methods=['GET'])
        custom_log("🌐 LeaderboardModule: `/get-leaderboard` route registered.")

    def get_leaderboard(self):
        """Retrieve the leaderboard with user rankings and return the current user's position if a username is provided."""
        try:
            connection = self.connection_module.get_connection()

            # ✅ Retrieve leaderboard (Top 10 users ordered by total points)
            leaderboard_query = """
            SELECT username, total_points AS points FROM users
            ORDER BY total_points DESC
            LIMIT 10;
            """
            leaderboard_data = self.connection_module.fetch_from_db(leaderboard_query, as_dict=True)

            # ✅ Get current user's rank if username is provided
            username = request.args.get("username")
            user_rank = None

            if username:
                user_rank_query = """
                SELECT username, total_points AS points,
                    (SELECT COUNT(*) + 1 FROM users WHERE total_points > u.total_points) AS rank
                FROM users u
                WHERE username = %s;
                """
                user_rank_data = self.connection_module.fetch_from_db(user_rank_query, (username,), as_dict=True)

                if user_rank_data:
                    user_rank = user_rank_data[0]

            response = {
                "leaderboard": leaderboard_data,
                "user_rank": user_rank  # ✅ Include user rank if available
            }

            return jsonify(response), 200

        except Exception as e:
            custom_log(f"❌ Error retrieving leaderboard: {e}")
            return jsonify({"error": "Server error retrieving leaderboard"}), 500
