from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import time
from pathlib import Path
import google.generativeai as genai
import json
import re

# Initialize Flask app
app = Flask(__name__)
CORS(app)

def load_env():
    """Load environment variables from .env.local"""
    env_path = Path(__file__).parent.parent / '.env.local'
    if not env_path.exists():
        raise FileNotFoundError(f"Environment file not found: {env_path}")

    with env_path.open() as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

# Load environment variables and configure Gemini
load_env()
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini."""
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Processing: {path}")
    return file

def wait_for_files_active(files):
    """Waits for the given files to be active."""
    print("Waiting for file processing...")
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(5)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            raise Exception(f"File {file.name} failed to process")
    print("...file ready")
    print()

def process_mri_scan(image_path, model):
    """Process a single MRI scan and return its analysis as JSON"""
    try:
        # Validate that the file exists
        if not Path(image_path).exists():
            return {"error": f"Image file {image_path} not found."}

        # Upload and process MRI image
        image_file = upload_to_gemini(str(image_path), mime_type="image/jpeg")
        wait_for_files_active([image_file])

        # Start chat and send single prompt
        chat = model.start_chat()
        prompt = """
        Please analyze this MRI brain scan image and provide:

        1. Detection of any visible brain tumors (location, size, characteristics) and what type they are (glioma, meningioma, pituitary). The image may not have a tumor at all. If there is a tumor, give me the predicted X Y Z coordinates of where it is located.
        2. Assessment of gray matter loss or abnormalities (regions affected, severity). There may not be any gray matter loss at all.
        3. Other notable abnormalities (if present)
        4. Recommended follow-up actions based on findings

        Be very brief in analysis but accurate. Output your analysis as a JSON object only, without extra text or code block formatting.
        """

        response = chat.send_message([image_file, prompt])
        raw_text = response.text.strip()

        # Remove ```json ... ``` or ``` ... ```
        cleaned_text = re.sub(r"^```(?:json)?\n", "", raw_text)
        cleaned_text = re.sub(r"\n```$", "", cleaned_text)

        # Try parsing the cleaned text
        try:
            analysis_json = json.loads(cleaned_text)
            return analysis_json
        except json.JSONDecodeError:
            return {"error": "Failed to parse the model's response as JSON.", "raw_response": raw_text}

    except Exception as e:
        return {"error": f"Error processing {Path(image_path).name}: {str(e)}"}

# Set up the model globally
generation_config = {
    "temperature": 0.4,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=generation_config,
)

# API endpoint
@app.route('/analyze_mri', methods=['POST'])
def analyze_mri():
    data = request.get_json()

    if not data or 'image_path' not in data:
        return jsonify({"error": "Missing 'image_path' in request"}), 400

    image_path = data['image_path']
    print(f"Received image path: {image_path}")

    analysis_result = process_mri_scan(image_path, model)

    return jsonify(analysis_result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
