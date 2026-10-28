"""
Module M3 -- Leaf Disease Detection (blueprint)
--------------------------------------------------
Ported from the standalone plant_disease_app: MobileNet-derived CNN
exported to ONNX, a true-green color pre-filter that gates the model
(so a non-leaf image is rejected before the CNN ever sees it), and
temperature-scaled confidence. Logic is unchanged from the original
app; only the Flask wiring (blueprint + shared login) changed.
"""
import os
import json
import numpy as np
from flask import Blueprint, request, render_template, jsonify, session, redirect, url_for
from PIL import Image
import onnxruntime as ort
from werkzeug.utils import secure_filename

disease_bp = Blueprint("disease_bp", __name__)

UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
IMG_SIZE = (224, 224)
MODEL_PATH = "plant_disease_cnn_model.onnx"

CONFIDENCE_THRESHOLD = 0.40
UNKNOWN_CONFIDENCE_CUTOFF = 0.25
CONFIDENCE_TEMPERATURE = 4.0
LEAF_COLOR_RATIO_THRESHOLD = 0.12
GREEN_ANCHOR_THRESHOLD = 0.05

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

_session = None
_input_name = None
_idx_to_class = None


def _load():
    global _session, _input_name, _idx_to_class
    if _session is None:
        _session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
        _input_name = _session.get_inputs()[0].name
        with open("class_indices.json") as f:
            class_indices = json.load(f)
        _idx_to_class = {v: k for k, v in class_indices.items()}
    return _session, _input_name, _idx_to_class


REMEDIES = {
    "Apple_Black_Rot": {
        "symptoms": "Purple-brown lesions on leaves and rotted, circular lesions on fruit.",
        "prevention": "Prune out dead/diseased wood and remove mummified fruit each season.",
        "treatment": "Apply a labelled fungicide (e.g. captan or myclobutanil) starting at green tip.",
    },
    "Apple_Healthy": {
        "symptoms": "No visible disease symptoms.",
        "prevention": "Maintain regular pruning, watering and nutrient schedule.",
        "treatment": "No treatment needed.",
    },
    "Potato_Early_Blight": {
        "symptoms": "Dark concentric 'target-spot' lesions on older leaves first.",
        "prevention": "Rotate crops, avoid overhead irrigation, use certified disease-free seed.",
        "treatment": "Apply chlorothalonil or mancozeb-based fungicide on a preventive schedule.",
    },
    "Potato_Healthy": {
        "symptoms": "No visible disease symptoms.",
        "prevention": "Maintain balanced fertilization and proper spacing.",
        "treatment": "No treatment needed.",
    },
    "Tomato_Bacterial_Spot": {
        "symptoms": "Small, water-soaked, dark spots on leaves, stems and fruit.",
        "prevention": "Use disease-free seed/transplants, avoid working in wet fields, rotate crops.",
        "treatment": "Apply copper-based bactericides; remove and destroy infected debris.",
    },
    "Tomato_Healthy": {
        "symptoms": "No visible disease symptoms.",
        "prevention": "Maintain consistent watering and good air circulation.",
        "treatment": "No treatment needed.",
    },
    "Tomato_Yellow_Leaf_Curl_Virus": {
        "symptoms": "Upward-curling, yellowing leaves and stunted plant growth.",
        "prevention": "Control whitefly vectors, use resistant varieties, use reflective mulches.",
        "treatment": "No cure once infected -- remove and destroy infected plants to limit spread; manage whiteflies with insecticide/sticky traps.",
    },
}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def is_leaf_like(img_path):
    img = Image.open(img_path).convert("RGB")
    rgb_arr = np.asarray(img).astype("float32")
    r, g, b = rgb_arr[..., 0], rgb_arr[..., 1], rgb_arr[..., 2]
    brightness = (r + g + b) / 3.0
    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    chroma = max_c - min_c

    not_too_dark_or_bright = (brightness > 15) & (brightness < 250)
    green_dominant = (g >= r + 4) & (g >= b + 4) & not_too_dark_or_bright
    yellow_olive = (g >= r - 8) & (g > b + 10) & not_too_dark_or_bright & (chroma > 8)
    necrotic = (
        (r >= g) & (r >= b) &
        (brightness > 15) & (brightness < 140) &
        (chroma > 5) & (chroma < 90)
    )

    green_anchor_ratio = float(green_dominant.sum()) / green_dominant.size
    plant_mask = green_dominant | yellow_olive | necrotic
    plant_ratio = float(plant_mask.sum()) / plant_mask.size

    leaf_like = (green_anchor_ratio >= GREEN_ANCHOR_THRESHOLD) and (plant_ratio >= LEAF_COLOR_RATIO_THRESHOLD)
    return leaf_like, plant_ratio


def predict_image(img_path):
    sess, input_name, idx_to_class = _load()
    img = Image.open(img_path).convert("RGB").resize(IMG_SIZE)
    arr = np.asarray(img).astype("float32") / 255.0
    arr = np.expand_dims(arr, axis=0)
    raw_preds = sess.run(None, {input_name: arr})[0][0].astype("float64")

    eps = 1e-12
    pseudo_logits = np.log(raw_preds + eps)
    scaled_logits = pseudo_logits / CONFIDENCE_TEMPERATURE
    scaled_logits -= scaled_logits.max()
    exp_scaled = np.exp(scaled_logits)
    calibrated_preds = exp_scaled / exp_scaled.sum()

    top_idx = int(np.argmax(calibrated_preds))
    predicted_class = idx_to_class[top_idx]
    confidence = float(calibrated_preds[top_idx])
    return predicted_class, confidence


NOT_A_LEAF_MESSAGE = (
    "No plant leaf was detected in this image. Please upload a clear photo "
    "of an Apple, Potato, or Tomato leaf."
)
UNKNOWN_IMAGE_MESSAGE = (
    "Unknown Image -- the model isn't confident this is one of the trained "
    "leaf types. Please upload another image."
)
LOW_CONFIDENCE_MESSAGE = (
    "A leaf was detected, but the model isn't confident enough to diagnose "
    "it. Try a clearer, well-lit, closer photo of a single Apple, Potato, "
    "or Tomato leaf."
)


@disease_bp.route("/disease", methods=["GET"])
def disease_index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    username = session.get("username", "User")
    return render_template("disease_scan.html", username=username)


@disease_bp.route("/disease/predict", methods=["POST"])
def disease_predict():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image was received. Please choose a file and try again."}), 400

    file = request.files["image"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Please upload a valid image file (png/jpg/jpeg)."}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)
    image_url = "/" + save_path.replace(os.sep, "/")

    leaf_like, green_ratio = is_leaf_like(save_path)
    if not leaf_like:
        return jsonify({
            "success": False,
            "error": NOT_A_LEAF_MESSAGE,
            "image_path": image_url,
            "green_ratio": f"{green_ratio * 100:.1f}%",
        })

    predicted_class, confidence = predict_image(save_path)

    if confidence < UNKNOWN_CONFIDENCE_CUTOFF:
        return jsonify({
            "success": False,
            "error": UNKNOWN_IMAGE_MESSAGE,
            "image_path": image_url,
            "green_ratio": f"{green_ratio * 100:.1f}%",
        })

    if predicted_class == "Other":
        return jsonify({
            "success": False,
            "error": NOT_A_LEAF_MESSAGE,
            "image_path": image_url,
            "green_ratio": f"{green_ratio * 100:.1f}%",
        })

    if confidence < CONFIDENCE_THRESHOLD:
        return jsonify({
            "success": False,
            "error": LOW_CONFIDENCE_MESSAGE,
            "image_path": image_url,
            "green_ratio": f"{green_ratio * 100:.1f}%",
            "confidence": f"{confidence * 100:.2f}%",
        })

    remedy = REMEDIES.get(predicted_class, {
        "symptoms": "Not available.",
        "prevention": "Not available.",
        "treatment": "Not available.",
    })

    display_name = predicted_class.replace("_", " ")
    is_healthy = predicted_class.endswith("_Healthy")

    # Log the scan into the shared telemetry DB (disease_scans table) so
    # it shows up alongside sensor data, per the synopsis data model (§9).
    try:
        from blueprints.telemetry_module import log_disease_scan
        log_disease_scan(save_path, predicted_class, confidence)
    except Exception as e:
        print(f"Could not log disease scan: {e}")

    # Log feature activity entry with user profile image
    try:
        from blueprints.assistant_module import log_activity
        from flask import session
        username = session.get("username", "guest")
        log_activity(
            username=username,
            action_type="leaf_scan",
            description=f"Leaf Scan Diagnosis: {display_name}",
            details=f"Confidence: {confidence * 100:.1f}%, Status: {'Healthy' if is_healthy else 'Infected'}",
            page="/disease",
            profile_image=session.get("profile_image")
        )
    except Exception as e:
        print(f"Could not log disease activity: {e}")

    return jsonify({
        "success": True,
        "image_path": image_url,
        "predicted_class": display_name,
        "is_healthy": is_healthy,
        "confidence": f"{confidence * 100:.2f}%",
        "green_ratio": f"{green_ratio * 100:.1f}%",
        "remedy": remedy,
    })
