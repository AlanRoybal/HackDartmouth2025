from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import time
from pathlib import Path
import google.generativeai as genai
import json
import re
from datetime import datetime
import boto3
from botocore.exceptions import NoCredentialsError
import shutil
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = '/tmp/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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
    """Process a single MRI scan and upload results to S3 with timestamp folder."""
    try:
        if not Path(image_path).exists():
            return {"error": f"Image file {image_path} not found."}

        image_file = upload_to_gemini(str(image_path), mime_type="image/jpeg")
        wait_for_files_active([image_file])

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

        cleaned_text = re.sub(r"^```(?:json)?\n", "", raw_text)
        cleaned_text = re.sub(r"\n```$", "", cleaned_text)

        try:
            analysis_json = json.loads(cleaned_text)

            # Timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = f"saved/{timestamp}/"  # S3 folder

            # Prepare filenames
            json_filename = f"{folder_name}context_{timestamp}.json"
            image_extension = Path(image_path).suffix
            image_filename = f"{folder_name}mri_{timestamp}{image_extension}"

            # Initialize boto3 S3 client
            s3 = boto3.client(
                's3',
                aws_access_key_id=os.environ['AWS_ACCESS_KEY'],
                aws_secret_access_key=os.environ['AWS_SECRET_KEY'],
                region_name=os.environ['AWS_REGION']
            )
            bucket_name = os.environ['S3_BUCKET_NAME']

            # Upload JSON
            s3.put_object(
                Bucket=bucket_name,
                Key=json_filename,
                Body=json.dumps(analysis_json, indent=4),
                ContentType='application/json'
            )
            print(f"Uploaded {json_filename} to S3.")

            # Upload MRI image
            with open(image_path, 'rb') as image_file_data:
                s3.put_object(
                    Bucket=bucket_name,
                    Key=image_filename,
                    Body=image_file_data,
                    ContentType='image/jpeg'
                )
            print(f"Uploaded {image_filename} to S3.")

            return {
                "message": "Files uploaded successfully",
                "json_file": json_filename,
                "image_file": image_filename
            }

        except json.JSONDecodeError:
            return {"error": "Failed to parse the model's response as JSON.", "raw_response": raw_text}

    except NoCredentialsError:
        return {"error": "AWS credentials not found."}

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

# API endpoints
@app.route('/analyze_mri', methods=['POST'])
def analyze_mri():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        try:
            analysis_result = process_mri_scan(filepath, model)
            
            # Clean up the temporary file
            os.remove(filepath)
            
            return jsonify(analysis_result)
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Failed to process file"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
