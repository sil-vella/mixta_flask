import yaml
import os
import re
import random
from flask import request, jsonify, send_from_directory
from tools.logger.custom_logging import custom_log
from core.managers.module_manager import ModuleManager

# ✅ Get the directory of the current file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ✅ Dynamically set IMAGE_DIR relative to this file's location
IMAGE_DIR = os.path.join(BASE_DIR, "celeb_data", "images")

class QuestionModule:
    def __init__(self, app_manager=None):
        """Initialize QuestionModule and register routes."""
        self.app_manager = app_manager
        self.connection_module = self.get_connection_module()

        if not self.connection_module:
            raise RuntimeError("QuestionModule: Failed to retrieve ConnectionModule from ModuleManager.")

        custom_log("✅ QuestionModule initialized.")

        # ✅ Ensure routes are registered upon module initialization
        self.register_routes()


    def get_connection_module(self):
        """Retrieve ConnectionModule from ModuleManager."""
        module_manager = self.app_manager.module_manager if self.app_manager else ModuleManager()
        return module_manager.get_module("connection_module")

    def register_routes(self):
        """Register question-related routes."""
        if not self.connection_module:
            raise RuntimeError("ConnectionModule is not available yet.")

        # ✅ Register the get-question route
        self.connection_module.register_route('/get-question', self.get_question, methods=['GET'])
        custom_log("🌐 QuestionModule: `/get-question` route registered.")

        # ✅ Register the static image serving route
        def serve_image(filename):
            """Serves images from the /images/ directory."""
            return send_from_directory(IMAGE_DIR, filename)

        self.connection_module.register_route('/images/<path:filename>', serve_image, methods=['GET'])
        custom_log("🖼️ QuestionModule: `/images/<filename>` route registered to serve static images.")

    def load_questions(self):
        """Load questions from YAML file in the celeb_data subdirectory."""
        try:
            # ✅ Get the directory where `question_module.py` is located
            base_dir = os.path.dirname(os.path.abspath(__file__))

            # ✅ Build the absolute path to `celeb_data.yml`
            yaml_path = os.path.join(base_dir, "celeb_data", "celeb_data.yml")

            # ✅ Open and load YAML data with UTF-8 encoding
            with open(yaml_path, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file)

            custom_log(f"✅ Questions loaded successfully from {yaml_path}.")
            return data
        except UnicodeDecodeError as e:
            custom_log(f"❌ Encoding error loading YAML: {e}")
            return None
        except yaml.YAMLError as e:
            custom_log(f"❌ YAML syntax error: {e}")
            return None
        except Exception as e:
            custom_log(f"❌ Unexpected error loading YAML from {yaml_path}: {e}")
            return None


    def normalize_name(self, name):
        """Normalize a celebrity name for consistent searching."""
        name = name.lower().strip()  # Convert to lowercase and trim spaces
        name = re.sub(r'[^\w\s]', '', name)  # Remove special characters except spaces
        name = name.replace(" ", "_")  # Replace spaces with underscores (for filename matching)
        return name

    def get_question(self):
        """Returns a question based on difficulty level, retrieves the actor's image, 3 distractor images, and tracks category-based progress."""
        try:
            custom_log("🔄 Starting get_question request...")

            level = str(request.args.get("level", default=1, type=int))  # ✅ Ensure level is string
            category = request.args.get("category", default=None, type=str)  # ✅ Retrieve category from request
            custom_log(f"📥 Received request for category '{category}' at level {level}.")

            # ✅ Load questions from YAML
            questions = self.load_questions()
            if not questions:
                custom_log("❌ Failed to load questions data.")
                return jsonify({"error": "Failed to load questions"}), 500

            # ✅ Validate level exists
            if level not in questions:
                custom_log(f"❌ No facts available for level {level}")
                return jsonify({"error": f"No facts available for level {level}"}), 404

            # ✅ Get all actors for this level & category
            if category == "mixed":
                all_actors = list(questions[level].keys())  # Use ALL actors from this level
            else:
                all_actors = [
                    actor for actor, data in questions[level].items()
                    if category in data.get("categories", [])
                ]

            if not all_actors:
                custom_log(f"⚠️ No more actors left to guess in category '{category}' at level {level}.")
                return jsonify({"error": f"No more actors left to guess in category '{category}' at level {level}"}), 404

            # ✅ Pick the correct actor randomly
            actor = random.choice(all_actors)
            question_data = questions[level][actor]

            # ✅ Get distractor names (3 random actors from the same level)
            distractor_names = random.sample(
                [a for a in all_actors if a != actor], min(3, len(all_actors) - 1)
            )

            # ✅ Get distractor images (matching distractor names)
            distractor_images = []
            for name in distractor_names:
                formatted_name = self.normalize_name(name)
                distractor_image = None

                for filename in os.listdir(IMAGE_DIR):
                    if filename.startswith(formatted_name):
                        distractor_image = f"{request.host_url.rstrip('/')}/images/{filename}"
                        break

                # ✅ If no image found, use a default image
                distractor_images.append(distractor_image or f"{request.host_url.rstrip('/')}/images/default.jpg")

            # ✅ Get correct actor's image
            formatted_actor_name = self.normalize_name(actor)
            image_url = None
            for filename in os.listdir(IMAGE_DIR):
                if filename.startswith(formatted_actor_name):
                    image_url = f"{request.host_url.rstrip('/')}/images/{filename}"
                    break
            image_url = image_url or f"{request.host_url.rstrip('/')}/images/default.jpg"

            # ✅ Final response with distractor names & images
            response = {
                "actor": actor,
                "category": category or "unknown",
                "facts": question_data["facts"],  # ✅ Retrieve facts safely
                "level": level,
                "image_url": image_url,  # ✅ Correct actor's image
                "distractor_images": distractor_images,  # ✅ Distractor images
                "distractor_names": distractor_names  # ✅ Distractor names from YAML
            }

            custom_log(f"✅ Sending response: {response}")
            return jsonify(response), 200

        except Exception as e:
            custom_log(f"❌ Unexpected error in get_question: {e}")
            return jsonify({"error": f"Server error: {str(e)}"}), 500
