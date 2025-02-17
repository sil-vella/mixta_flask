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
        self.connection_module.register_route('/get-question', self.get_question, methods=['POST'])
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
        """Returns a random question with a main celebrity and 3 distractor images."""
        try:
            custom_log("🔄 Starting get_question request...")

            # ✅ Extract request data from JSON body (Fix)
            data = request.get_json()
            level = str(data.get("level", 1))  # Ensure level is a string
            category = data.get("category", "").lower()  # Retrieve category and lowercase it
            guessed_list = data.get("guessed_names", [])  # ✅ Extract guessed names list from JSON

            # ✅ Ensure guessed_list is a list of lowercase names
            if not isinstance(guessed_list, list):
                guessed_list = []
            guessed_list = [name.lower() for name in guessed_list]  # Normalize guessed names

            custom_log(f"📥 Received request for category '{category}' at level {level}. Guessed list: {guessed_list}")

            # ✅ Load questions from YAML
            questions = self.load_questions()
            if not questions:
                custom_log("❌ Failed to load questions data.")
                return jsonify({"error": "Failed to load questions"}), 500

            # ✅ Validate level exists
            if level not in questions:
                custom_log(f"❌ No facts available for level {level}")
                return jsonify({"error": f"No facts available for level {level}"}), 404

            # ✅ Get all available actors at this level (ignoring guessed list)
            all_actors = {
                actor.lower(): data for actor, data in questions[level].items()
                if actor.lower() not in guessed_list  # ✅ Ensure guessed actors are removed
            }

            if not all_actors:
                custom_log(f"⚠️ No more actors left to guess at level {level}.")
                return jsonify({"error": f"No more actors left to guess at level {level}"}), 200

            # ✅ Ensure Randomness: Shuffle list before selecting actor
            actor = None
            if category == "mixed":
                actor_list = list(all_actors.keys())
                random.shuffle(actor_list)  # ✅ Ensure randomness
                actor = actor_list[0]  # ✅ Pick the first shuffled actor
            else:
                filtered_actors = {
                    actor: data for actor, data in all_actors.items()
                    if category in [c.lower() for c in data.get("categories", [])]
                }
                if not filtered_actors:
                    custom_log(f"⚠️ No more actors left to guess in category '{category}' at level {level}.")
                    return jsonify({"error": f"No more actors left to guess in category '{category}' at level {level}"}), 200
                filtered_actor_list = list(filtered_actors.keys())
                random.shuffle(filtered_actor_list)
                actor = filtered_actor_list[0]

            question_data = all_actors[actor]
            actor_category = question_data.get("categories", [])[0].lower()  # Pick the first category and lowercase it

            # ✅ Get distractor names (3 random actors from the same category)
            distractor_pool = [
                a for a, data in all_actors.items()
                if actor_category in [c.lower() for c in data.get("categories", [])] and a != actor
            ]
            random.shuffle(distractor_pool)  # ✅ Shuffle before selecting
            distractor_names = distractor_pool[:3]  # ✅ Get up to 3 distractors

            # ✅ Get distractor images
            distractor_images = []
            for name in distractor_names:
                formatted_name = self.normalize_name(name)
                distractor_image = None

                for filename in os.listdir(IMAGE_DIR):
                    if filename.lower().startswith(formatted_name.lower()):  # ✅ Case-insensitive file matching
                        distractor_image = f"{request.host_url.rstrip('/')}/images/{filename}"
                        break

                # ✅ If no image found, use a default image
                distractor_images.append(distractor_image or f"{request.host_url.rstrip('/')}/images/default.jpg")

            # ✅ Get correct actor's image
            formatted_actor_name = self.normalize_name(actor)
            image_url = None
            for filename in os.listdir(IMAGE_DIR):
                if filename.lower().startswith(formatted_actor_name.lower()):  # ✅ Case-insensitive file matching
                    image_url = f"{request.host_url.rstrip('/')}/images/{filename}"
                    break
            image_url = image_url or f"{request.host_url.rstrip('/')}/images/default.jpg"

            # ✅ Final response
            # ✅ Preserve "mixed" category if it was requested
            response = {
                "actor": actor,
                "category": "mixed" if category == "mixed" else actor_category,  # ✅ FIXED: Force "mixed" if playing mixed
                "facts": question_data["facts"],
                "level": level,
                "image_url": image_url,
                "distractor_images": distractor_images,
                "distractor_names": distractor_names
            }


            custom_log(f"✅ Sending response: {response}")
            return jsonify(response), 200

        except Exception as e:
            custom_log(f"❌ Unexpected error in get_question: {e}")
            return jsonify({"error": f"Server error: {str(e)}"}), 500
