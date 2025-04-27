from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
from datetime import datetime
from operator import itemgetter
import google.generativeai as genai
import boto3
import json
import os
import re
import shutil
import time
from werkzeug.utils import secure_filename
from botocore.exceptions import NoCredentialsError

# ----------- CONFIG ----------------------------------------------------------

UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def load_env():
    """Populate os.environ from .env.local (simple line-by-line parser)."""
    env_path = Path(__file__).parent.parent / ".env.local"
    if not env_path.exists():
        raise FileNotFoundError(f"Environment file not found: {env_path}")

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")


load_env()  # must run before we touch env vars

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

S3_BUCKET = os.environ["S3_BUCKET_NAME"]
AWS_REGION = os.environ["AWS_REGION"]

generation_config = dict(
    temperature=0.4,
    top_p=0.95,
    top_k=64,
    max_output_tokens=8192,
)

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=generation_config,
)


# ----------- FLASK APP -------------------------------------------------------

app = Flask(__name__)
CORS(app)


# ----------- HELPERS ---------------------------------------------------------

def s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY"],
        aws_secret_access_key=os.environ["AWS_SECRET_KEY"],
        region_name=AWS_REGION,
    )


def upload_to_gemini(path, mime_type=None):
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploading to Gemini: {path}")
    return file


def wait_for_files_active(files):
    print("Waiting for Gemini file processing…")
    for f in files:
        while (state := genai.get_file(f.name).state.name) == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(5)
        if state != "ACTIVE":
            raise RuntimeError(f"File {f.name} failed (state={state})")
    print(" ready")


def get_analysis_by_timestamp(ts: str):
    """Return context + MRI URL for a given timestamp folder."""
    cli = s3_client()
    ctx_key = f"saved/{ts}/context_{ts}.json"
    mri_key = f"saved/{ts}/mri_{ts}.jpg"

    ctx_obj = cli.get_object(Bucket=S3_BUCKET, Key=ctx_key)
    context = json.loads(ctx_obj["Body"].read())

    return {
        "context": context,
        "mri_url": f"https://{S3_BUCKET}.s3.amazonaws.com/{mri_key}",
        "timestamp": ts,
    }


def get_latest_analysis():
    """Fallback when no timestamp is provided."""
    cli = s3_client()
    objs = cli.list_objects_v2(Bucket=S3_BUCKET, Prefix="saved/")
    if "Contents" not in objs:
        return None

    ctx_files = [o for o in objs["Contents"] if "context_" in o["Key"]]
    if not ctx_files:
        return None

    latest_ctx = max(ctx_files, key=itemgetter("LastModified"))
    ts = latest_ctx["Key"].split("context_")[1].split(".json")[0]
    return get_analysis_by_timestamp(ts)


# ----------- CORE PROCESSING -------------------------------------------------

def process_mri_scan(image_path: Path):
    """Analyze scan, upload JSON/image/summary. Returns dict to frontend."""
    if not image_path.exists():
        return {"error": f"File not found: {image_path}"}

    # ── Upload to Gemini & run analysis ──────────────────────────────────────
    img_file = upload_to_gemini(str(image_path), mime_type="image/jpeg")
    wait_for_files_active([img_file])

    chat = model.start_chat()
    analysis_prompt = """
    Please analyze this MRI brain scan image and provide:

        1. Detection of any visible brain tumors (location, size, characteristics) and what type they are (glioma, meningioma, pituitary). The image may not have a tumor at all. If there is a tumor, give me the predicted X Y Z coordinates of where it is located. The dimensions of the scan are x=401, y=200, z=300.
        2. Assessment of gray matter loss or abnormalities (regions affected, severity). There may not be any gray matter loss at all.
        3. Other notable abnormalities (if present)
        4. Recommended follow-up actions based on findings

        Be very brief in analysis but accurate. Output your analysis as a JSON object only, without extra text or code block formatting.
    """
    raw = chat.send_message([img_file, analysis_prompt]).text.strip()
    clean = re.sub(r"^```(?:json)?\n|\n```$", "", raw)

    try:
        analysis_json = json.loads(clean)
    except json.JSONDecodeError:
        return {"error": "Gemini response is not valid JSON", "raw_response": raw}

    # ── Timestamped folder name ─────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = f"saved/{ts}/"
    json_name = f"context_{ts}.json"
    img_ext = image_path.suffix or ".jpg"
    img_name = f"mri_{ts}{img_ext}"
    sum_name = f"summary_{ts}.txt"

    cli = s3_client()

    # JSON
    cli.put_object(
        Bucket=S3_BUCKET,
        Key=folder + json_name,
        Body=json.dumps(analysis_json, indent=4),
        ContentType="application/json",
    )

    # Image
    with open(image_path, "rb") as f:
        cli.put_object(
            Bucket=S3_BUCKET,
            Key=folder + img_name,
            Body=f,
            ContentType="image/jpeg",
        )

    # Summary
    chat_sum = model.start_chat()
    sum_prompt = (
        "Summarize this analysis (2–3 sentences):\n"
        + json.dumps(analysis_json, indent=2)
    )
    summary = chat_sum.send_message(sum_prompt).text.strip()
    cli.put_object(
        Bucket=S3_BUCKET,
        Key=folder + sum_name,
        Body=summary,
        ContentType="text/plain",
    )

    return {
        "message": "Files uploaded successfully",
        "timestamp": ts,
        "json_file": folder + json_name,
        "image_file": folder + img_name,
        "image_url": f"https://{S3_BUCKET}.s3.amazonaws.com/{folder + img_name}",
        "summary_file": folder + sum_name,
    }


# ----------- ROUTES ----------------------------------------------------------

@app.route("/analyze_mri", methods=["POST"])
def analyze_mri():
    if "file" not in request.files or not request.files["file"].filename:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    filename = secure_filename(file.filename)
    tmp_path = Path(UPLOAD_FOLDER) / filename
    file.save(tmp_path)

    try:
        result = process_mri_scan(tmp_path)
    finally:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass

    status = 200 if "error" not in result else 500
    return jsonify(result), status


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    prompt = data.get("prompt", "").strip()
    ts = data.get("timestamp")  # may be None

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    analysis = get_analysis_by_timestamp(ts) if ts else get_latest_analysis()
    if not analysis:
        return jsonify({"error": "No analysis context found"}), 404

    context = analysis["context"]
    system_prompt = (
        "You are a medical AI assistant.\n"
        + json.dumps(context, indent=2)
        + f"\nUser Question: {prompt}\n"
        "Answer clearly and concisely, no markdown."
    )

    resp = model.start_chat().send_message(system_prompt)
    return jsonify({"response": resp.text})


@app.route("/history", methods=["GET"])
def history():
    try:
        cli = s3_client()
        objs = cli.list_objects_v2(Bucket=S3_BUCKET, Prefix="saved/")
        if "Contents" not in objs:
            return jsonify([])

        ctx_files = [o for o in objs["Contents"] if "context_" in o["Key"]]
        all_files = objs["Contents"]

        history = []
        for ctx in ctx_files:
            ts = ctx["Key"].split("context_")[1].split(".json")[0]
            img = next(
                (f for f in all_files if f"saved/{ts}/mri_{ts}" in f["Key"]), None
            )
            summ = next(
                (f for f in all_files if f"saved/{ts}/summary_{ts}" in f["Key"]), None
            )
            if not (img and summ):
                continue

            img_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{img['Key']}"
            ctx_obj = cli.get_object(Bucket=S3_BUCKET, Key=ctx["Key"])
            ctx_json = json.loads(ctx_obj["Body"].read())

            summ_obj = cli.get_object(Bucket=S3_BUCKET, Key=summ["Key"])
            summ_txt = summ_obj["Body"].read().decode()

            history.append(
                {
                    "timestamp": ts,
                    "mri_url": img_url,
                    "context": ctx_json,
                    "summary": summ_txt,
                }
            )

        history.sort(key=lambda x: x["timestamp"], reverse=True)
        return jsonify(history)
    except Exception as e:
        print("History error:", e)
        return jsonify({"error": str(e)}), 500


# ----------- MAIN ------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
