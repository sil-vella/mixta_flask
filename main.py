from flask import Flask
from flask_cors import CORS
from core.managers.app_manager import AppManager

# Initialize the AppManager
app_manager = AppManager()

# Initialize the Flask app
app = Flask(__name__)

# Enable Cross-Origin Resource Sharing (CORS)
CORS(app)

# Initialize the AppManager and pass the app for plugin registration
app_manager.initialize(app)

# Additional app-level configurations
app.config["DEBUG"] = True

if __name__ == "__main__":
    # Run the app
    app.run(debug=True, host="0.0.0.0", port=5000)
