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
        """Fetch all users, sort by points (descending), and return leaderboard with user rank (if provided)."""
        try:
            # ✅ Get email from query params
            user_email = request.args.get("email")
            
            # ✅ Fetch all users ordered by points DESC
            query = "SELECT username, email, points FROM users ORDER BY points DESC;"
            users = self.connection_module.fetch_from_db(query, as_dict=True)

            if users is None:
                return jsonify({"error": "Failed to retrieve leaderboard."}), 500

            leaderboard = []
            user_rank = None  # Store user rank if email is provided

            for idx, user in enumerate(users, start=1):
                leaderboard.append({
                    "rank": idx,
                    "username": user["username"],
                    "points": user["points"]
                })

                # ✅ If user email is provided, check and store the rank
                if user_email and user["email"] == user_email:
                    user_rank = {
                        "rank": idx,
                        "username": user["username"],
                        "points": user["points"]
                    }

            response_data = {"leaderboard": leaderboard}

            # ✅ Include user rank in response if found
            if user_email and user_rank:
                response_data["user_rank"] = user_rank

            return jsonify(response_data), 200

        except Exception as e:
            custom_log(f"❌ Error fetching leaderboard: {e}")
            return jsonify({"error": "An error occurred while retrieving leaderboard."}), 500