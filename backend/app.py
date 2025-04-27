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
from operator import itemgetter

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

@app.route('/get_history', methods=['GET'])
def get_history():
    try:
        # Initialize boto3 S3 client
        s3 = boto3.client(
            's3',
            aws_access_key_id=os.environ['AWS_ACCESS_KEY'],
            aws_secret_access_key=os.environ['AWS_SECRET_KEY'],
            region_name=os.environ['AWS_REGION']
        )
        bucket_name = os.environ['S3_BUCKET_NAME']
        
        # List objects in the saved/ prefix
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix='saved/')
        
        if 'Contents' not in response:
            return jsonify({"message": "No history found", "items": []})
        
        # Group files by timestamp folder
        folders = {}
        for item in response['Contents']:
            key = item['Key']
            # Skip the saved/ directory itself
            if key == 'saved/':
                continue
                
            # Extract timestamp folder (e.g., saved/20230101_120000/)
            folder_path = '/'.join(key.split('/')[:2]) + '/'
            
            if folder_path not in folders:
                folders[folder_path] = {'json': None, 'image': None, 'timestamp': None}
            
            # Check if it's JSON or image
            if key.endswith('.json'):
                folders[folder_path]['json'] = key
                # Extract timestamp from filename (context_YYYYMMDD_HHMMSS.json)
                timestamp_str = key.split('_')[-1].replace('.json', '')
                folders[folder_path]['timestamp'] = timestamp_str
            elif any(key.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
                folders[folder_path]['image'] = key
        
        # Process each folder with both JSON and image
        history_items = []
        for folder_data in folders.values():
            if folder_data['json'] and folder_data['image']:
                # Get JSON content
                json_obj = s3.get_object(Bucket=bucket_name, Key=folder_data['json'])
                json_content = json.loads(json_obj['Body'].read().decode('utf-8'))
                
                # Get image URL (generate a presigned URL)
                image_url = s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket_name, 'Key': folder_data['image']},
                    ExpiresIn=3600  # URL expires in 1 hour
                )
                
                # Get summary using Gemini
                summary = generate_summary(json_content)
                
                # Format timestamp from YYYYMMDD_HHMMSS to human-readable format
                timestamp_str = folder_data.get('timestamp')
                if timestamp_str:
                    try:
                        # Extract timestamp from the folder name if available
                        folder_timestamp = folder_data['json'].split('/')[1]
                        timestamp = datetime.strptime(folder_timestamp, "%Y%m%d_%H%M%S")
                        formatted_time = timestamp.strftime("%B %d, %Y at %I:%M %p")
                    except (ValueError, IndexError):
                        formatted_time = "Unknown date"
                else:
                    formatted_time = "Unknown date"
                
                history_items.append({
                    'id': folder_data['json'].split('/')[1],  # Use timestamp as ID
                    'image_url': image_url,
                    'summary': summary,
                    'timestamp': formatted_time,
                    'json_url': s3.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': bucket_name, 'Key': folder_data['json']},
                        ExpiresIn=3600
                    ),
                    'full_data': json_content
                })
        
        # Sort by timestamp (newest first)
        history_items.sort(key=itemgetter('id'), reverse=True)
        
        return jsonify({
            "message": f"Found {len(history_items)} history items",
            "items": history_items
        })
        
    except NoCredentialsError:
        return jsonify({"error": "AWS credentials not found."}), 401
    except Exception as e:
        return jsonify({"error": f"Error fetching history: {str(e)}"}), 500

def generate_summary(analysis_json):
    """Generate a summarized version of the analysis using Gemini."""
    try:
        # Create a prompt for Gemini to summarize the analysis
        prompt = f"""
        Summarize this MRI analysis in 2-3 concise sentences highlighting the key findings:
        {json.dumps(analysis_json)}
        
        Be direct and straightforward about any tumors, abnormalities, or other significant findings.
        If no issues were found, mention that the scan appears normal.
        """
        
        chat = model.start_chat()
        response = chat.send_message(prompt)
        summary = response.text.strip()
        
        # Ensure we're not returning anything too long
        if len(summary) > 500:
            summary = summary[:497] + "..."
            
        return summary
        
    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        return "Unable to generate summary for this analysis."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
