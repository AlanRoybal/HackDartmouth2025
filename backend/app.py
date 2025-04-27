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
import subprocess
import sys
from threading import Thread

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
        analysis_prompt = """
        Please analyze this MRI brain scan image and provide:

        1. Detection of any visible brain tumors (location, size, characteristics) and what type they are (glioma, meningioma, pituitary). The image may not have a tumor at all. If there is a tumor, give me the predicted X Y Z coordinates of where it is located. The dimensions of the scan are x=401, y=200, z=300.
        2. Assessment of gray matter loss or abnormalities (regions affected, severity). There may not be any gray matter loss at all.
        3. Other notable abnormalities (if present)
        4. Recommended follow-up actions based on findings

        Be very brief in analysis but accurate. Output your analysis as a JSON object only, without extra text or code block formatting.
        """
        response = chat.send_message([image_file, analysis_prompt])
        raw_text = response.text.strip()

        cleaned_text = re.sub(r"^```(?:json)?\n", "", raw_text)
        cleaned_text = re.sub(r"\n```$", "", cleaned_text)

        try:
            analysis_json = json.loads(cleaned_text)

            # Timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = f"saved/{timestamp}/"

            json_filename = f"{folder_name}context_{timestamp}.json"
            image_extension = Path(image_path).suffix
            image_filename = f"{folder_name}mri_{timestamp}{image_extension}"

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

            # Upload MRI Image
            with open(image_path, 'rb') as image_file_data:
                s3.put_object(
                    Bucket=bucket_name,
                    Key=image_filename,
                    Body=image_file_data,
                    ContentType='image/jpeg'
                )
            print(f"Uploaded {image_filename} to S3.")

            # --- Generate and Upload Summary ---
            chat_summary = model.start_chat()
            summary_prompt = f"""Summarize this MRI scan analysis into 2-3 sentences.
            Focus on important findings, any tumors, and major abnormalities.
            JSON content:
            {json.dumps(analysis_json, indent=2)}
            """
            summary_response = chat_summary.send_message(summary_prompt)
            summary_text = summary_response.text.strip()

            summary_filename = f"{folder_name}summary_{timestamp}.txt"
            s3.put_object(
                Bucket=bucket_name,
                Key=summary_filename,
                Body=summary_text,
                ContentType='text/plain'
            )
            print(f"Uploaded {summary_filename} to S3.")

            return {
                "message": "Files uploaded successfully",
                "json_file": json_filename,
                "image_file": image_filename,
                "summary_file": summary_filename
            }

        except json.JSONDecodeError:
            return {"error": "Failed to parse the model's response as JSON.", "raw_response": raw_text}

    except NoCredentialsError:
        return {"error": "AWS credentials not found."}
    except Exception as e:
        return {"error": f"Error processing {Path(image_path).name}: {str(e)}"}

def get_latest_analysis():
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=os.environ['AWS_ACCESS_KEY'],
            aws_secret_access_key=os.environ['AWS_SECRET_KEY'],
            region_name=os.environ['AWS_REGION']
        )
        bucket_name = os.environ['S3_BUCKET_NAME']

        # List all objects in the saved/ prefix
        objects = s3.list_objects_v2(Bucket=bucket_name, Prefix='saved/')
        if 'Contents' not in objects:
            return None

        # Filter for context files and sort by last modified
        context_files = [obj for obj in objects['Contents'] 
                        if 'context_' in obj['Key']]
        if not context_files:
            return None

        latest_context = max(context_files, key=itemgetter('LastModified'))
        
        # Get the corresponding MRI file
        timestamp = latest_context['Key'].split('context_')[1].split('.json')[0]
        mri_key = f"saved/{timestamp}/mri_{timestamp}.jpg"

        # Get the context JSON content
        context_response = s3.get_object(Bucket=bucket_name, Key=latest_context['Key'])
        context_data = json.loads(context_response['Body'].read().decode('utf-8'))

        return {
            "context": context_data,
            "mri_url": f"https://{bucket_name}.s3.amazonaws.com/{mri_key}",
            "timestamp": timestamp
        }

    except Exception as e:
        print(f"Error fetching latest analysis: {e}")
        return None

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

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    if not data or 'prompt' not in data:
        return jsonify({"error": "No prompt provided"}), 400

    try:
        # Get latest analysis context
        analysis = get_latest_analysis()
        if not analysis:
            return jsonify({"error": "No analysis context found"}), 404

        context = analysis['context']
        
        # Construct prompt with context
        system_prompt = f"""You are a medical AI assistant. Use the following analysis context and also infer from it to answer questions:
        
        {json.dumps(context, indent=2)}
        
        User Question: {data['prompt']}

        Make the answers slightly detailed but not too verbose. Get rid of any markdown formatting and code blocks.
        """

        chat = model.start_chat()
        response = chat.send_message(system_prompt)

        return jsonify({"response": response.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/history', methods=['GET'])
def history():
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=os.environ['AWS_ACCESS_KEY'],
            aws_secret_access_key=os.environ['AWS_SECRET_KEY'],
            region_name=os.environ['AWS_REGION']
        )
        bucket_name = os.environ['S3_BUCKET_NAME']

        objects = s3.list_objects_v2(Bucket=bucket_name, Prefix='saved/')
        if 'Contents' not in objects:
            return jsonify([])

        context_files = [obj for obj in objects['Contents'] if 'context_' in obj['Key']]
        all_files = objects['Contents']

        history_items = []

        for ctx_obj in context_files:
            timestamp = ctx_obj['Key'].split('context_')[1].split('.json')[0]
            mri_file = next(
                (file for file in all_files if f"saved/{timestamp}/mri_{timestamp}" in file['Key']),
                None
            )
            summary_file = next(
                (file for file in all_files if f"saved/{timestamp}/summary_{timestamp}" in file['Key']),
                None
            )

            if not mri_file or not summary_file:
                continue

            mri_url = f"https://{bucket_name}.s3.amazonaws.com/{mri_file['Key']}"

            # Get the context JSON
            context_response = s3.get_object(Bucket=bucket_name, Key=ctx_obj['Key'])
            context_data = json.loads(context_response['Body'].read().decode('utf-8'))

            # Get the pre-uploaded summary
            summary_response = s3.get_object(Bucket=bucket_name, Key=summary_file['Key'])
            summary_text = summary_response['Body'].read().decode('utf-8')

            history_items.append({
                "timestamp": timestamp,
                "mri_url": mri_url,
                "context": context_data,
                "summary": summary_text
            })

        history_items.sort(key=lambda x: x['timestamp'], reverse=True)

        return jsonify(history_items)

    except Exception as e:
        print(f"Error fetching history: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/run-viewer', methods=['POST'])
def run_viewer():
    print("hello")
    data = request.json
    scan_dir = data.get('scanDir', 'scan')  # Default to 'scan' if not provided
    
    # Convert to absolute path if it's a relative path
    if not os.path.isabs(scan_dir):
        # Define your scans directory relative to your Flask app
        scan_dir = os.path.join(os.path.dirname(__file__), 'scans', scan_dir)
    
    def run_script_async():
        try:
            # Make sure the script path is correct
            script_path = os.path.join(os.path.dirname(__file__), 'viewer.py')
            # 🔥 FIX HERE: use sys.executable instead of "python"
            cmd = [sys.executable, script_path, scan_dir]
            print(f"Executing command: {' '.join(cmd)}")
            process = subprocess.Popen(cmd)
            # Not waiting for the process to complete
        except Exception as e:
            print(f"Error running viewer: {str(e)}")
    
    # Check if directory exists
    if not os.path.isdir(scan_dir):
        return jsonify({"success": False, "error": f"Scan directory not found: {scan_dir}"}), 404
    
    # Run in a separate thread
    thread = Thread(target=run_script_async)
    thread.daemon = True  # This ensures the thread will die when the main process exits
    thread.start()
    
    return jsonify({"success": True, "message": f"Viewer launched for scan directory: {scan_dir}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
