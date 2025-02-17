import yaml
from flask import jsonify
from tools.logger.custom_logging import custom_log
from core.managers.module_manager import ModuleManager
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # ✅ Gets the directory of the current script
CATEGORIES_FILE = os.path.join(BASE_DIR, "data", "categories.yml")  # ✅ Full path


class FunctionHelperModule:
    def __init__(self, app_manager=None):
        """Initialize FunctionHelperModule and register routes."""
        self.app_manager = app_manager
        self.connection_module = self.get_connection_module()

        if not self.connection_module:
            raise RuntimeError("FunctionHelperModule: Failed to retrieve ConnectionModule from ModuleManager.")

        custom_log("✅ FunctionHelperModule initialized.")
        self.register_routes()

    def get_connection_module(self):
        """Retrieve ConnectionModule from ModuleManager."""
        module_manager = self.app_manager.module_manager if self.app_manager else ModuleManager()
        return module_manager.get_module("connection_module")

    def register_routes(self):
        """Register categories route."""
        if not self.connection_module:
            raise RuntimeError("ConnectionModule is not available yet.")

        self.connection_module.register_route('/get-categories', self.get_categories, methods=['GET'])
        custom_log("🌐 FunctionHelperModule: `/get-categories` route registered.")

    def get_categories(self):
        """Returns a list of available categories and their respective levels."""
        try:
            # ✅ Load categories from YAML file
            with open(CATEGORIES_FILE, "r") as file:
                categories_data = yaml.safe_load(file)

            if not categories_data or "categories" not in categories_data:
                return jsonify({"error": "No categories found"}), 404

            # ✅ Extract categories and levels
            categories_response = {
                category: {"levels": int(data["levels"])}
                for category, data in categories_data["categories"].items()
            }

            custom_log(f"📜 Available categories: {categories_response}")

            return jsonify({"categories": categories_response}), 200

        except Exception as e:
            custom_log(f"❌ Error retrieving categories: {e}")
            return jsonify({"error": f"Server error: {str(e)}"}), 500
