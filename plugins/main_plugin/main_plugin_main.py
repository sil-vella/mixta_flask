from plugins.main_plugin.modules.connection_mysql_module.connection_mysql_module import ConnectionMySqlModule
from plugins.main_plugin.modules.login_module.login_module import LoginModule

class MainPlugin:
    def initialize(self, app_manager):
        """
        Initialize the MainPlugin with AppManager.
        :param app_manager: AppManager - The main application manager.
        """
        print("Initializing MainPlugin...")

        try:
            # Ensure ConnectionMySqlModule is registered FIRST
            if not app_manager.module_manager.get_module("connection_module"):
                print("Registering ConnectionMySqlModule...")
                app_manager.module_manager.register_module(
                    "connection_module", 
                    ConnectionMySqlModule, 
                    app_manager=app_manager
                )

            # Retrieve the ConnectionMySqlModule
            connection_module = app_manager.module_manager.get_module("connection_module")
            if not connection_module:
                raise Exception("ConnectionMySqlModule is not registered in ModuleManager.")

            connection_module.initialize(app_manager.flask_app)

            # Ensure LoginModule is registered LAST
            if not app_manager.module_manager.get_module("login_module"):
                print("Registering LoginModule...")
                app_manager.module_manager.register_module(
                    "login_module", 
                    LoginModule, 
                    app_manager=app_manager
                )

            login_module = app_manager.module_manager.get_module("login_module")
            if login_module:
                login_module.register_routes() 

            print("MainPlugin initialized successfully.")

            # Register the `/` route with the correct view function
            connection_module.register_route("/", self.home, methods=["GET"])
            print("Route '/' registered successfully.")
        except Exception as e:
            print(f"Error initializing MainPlugin: {e}")
            raise

    def home(self):
        """Handle the root route."""
        return "Mixta app / route."
