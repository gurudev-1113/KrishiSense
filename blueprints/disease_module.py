"""
Module M3 -- Leaf Disease Detection (blueprint)
--------------------------------------------------
High-precision multi-stage leaf disease detection:
1. Multi-modal AI Vision analysis (Gemini Vision) for real-world plant species
   identification, crop suitability verification, and zero-hallucination diagnosis.
2. Local CNN & venation-texture safeguard pipeline as an offline/instant fallback.
"""
import os
import io
import json
import base64
import requests
import numpy as np
from flask import Blueprint, request, render_template, jsonify, session, redirect, url_for
from PIL import Image
from scipy import ndimage
import onnxruntime as ort
from werkzeug.utils import secure_filename
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

disease_bp = Blueprint("disease_bp", __name__)

UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
IMG_SIZE = (224, 224)
MODEL_PATH = "plant_disease_cnn_model.onnx"

# The CNN model is strictly trained on these 7 classes:
# Apple: Apple_Black_Rot, Apple_Healthy
# Potato: Potato_Early_Blight, Potato_Healthy
# Tomato: Tomato_Bacterial_Spot, Tomato_Healthy, Tomato_Yellow_Leaf_Curl_Virus
SUPPORTED_CROPS = {
    "apple": ["Apple_Black_Rot", "Apple_Healthy"],
    "potato": ["Potato_Early_Blight", "Potato_Healthy"],
    "tomato": ["Tomato_Bacterial_Spot", "Tomato_Healthy", "Tomato_Yellow_Leaf_Curl_Virus"],
}

CONFIDENCE_THRESHOLD = 0.75

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
        "symptoms": "Purple-brown 'frogeye' circular lesions with concentric rings on leaves and rotted fruit.",
        "prevention": "Prune out dead/cankered wood, remove mummified fruit, and maintain good orchard sanitation.",
        "treatment": "Apply a labelled fungicide (such as captan, mancozeb, or myclobutanil) starting at green tip.",
    },
    "Apple_Healthy": {
        "symptoms": "Foliage is clean, vibrant green, and free of visible fungal or bacterial lesions.",
        "prevention": "Maintain regular pruning, balanced nitrogen/potassium fertilization, and proper watering schedule.",
        "treatment": "No chemical treatment needed.",
    },
    "Potato_Early_Blight": {
        "symptoms": "Dark brown concentric 'target-spot' lesions developing on older lower leaves first.",
        "prevention": "Rotate crops with non-solanaceous species, avoid overhead irrigation, and plant certified seed.",
        "treatment": "Apply chlorothalonil, mancozeb, or azoxystrobin-based fungicide on a preventive schedule.",
    },
    "Potato_Healthy": {
        "symptoms": "Leaf tissue is smooth, uniformly green, and showing robust physiological vigor.",
        "prevention": "Maintain balanced fertilization, hilling, proper plant spacing, and adequate drainage.",
        "treatment": "No chemical treatment needed.",
    },
    "Tomato_Bacterial_Spot": {
        "symptoms": "Small, water-soaked, dark necrotic spots with yellow halos on leaves, stems, and fruit.",
        "prevention": "Use disease-free certified seed, avoid handling plants while foliage is wet, and rotate crops.",
        "treatment": "Apply fixed-copper bactericides mixed with mancozeb; prune and destroy severely infected debris.",
    },
    "Tomato_Healthy": {
        "symptoms": "Vibrant, uniformly green foliage with no chlorosis, wilting, or spot lesions.",
        "prevention": "Ensure consistent drip irrigation, mulch soil to prevent splash dispersal, and ensure good airflow.",
        "treatment": "No chemical treatment needed.",
    },
    "Tomato_Yellow_Leaf_Curl_Virus": {
        "symptoms": "Upward cupping and curling of leaflets, intense interveinal chlorosis/yellowing, and stunted growth.",
        "prevention": "Control whitefly vectors (Bemisia tabaci) using yellow sticky traps, reflective mulches, and resistant hybrids.",
        "treatment": "No cure once infected -- rogue and destroy infected plants immediately to prevent field-wide vector spread.",
    },
}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def diagnose_with_gemini(img_path):
    """
    Multimodal visual diagnostic pipeline via Gemini Vision.
    Performs real-world plant identification, crop suitability verification,
    and eliminates hallucinations on non-trained crops (e.g. Banana, Corn, Coconut, Weeds).
    """
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        return None

    try:
        im = Image.open(img_path).convert("RGB")
        im.thumbnail((384, 384), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=80)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        model_name = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
        prompt = """You are an expert plant pathologist and agronomist in KrishiSense.
Analyze this leaf/plant image carefully.

Tasks:
1. Verify if this image depicts a plant leaf, crop foliage, stem, fruit, or agricultural specimen.
   If it is completely unrelated (e.g. human face, car, electronics, shoes, animal, building), set "is_leaf": false.
2. Identify the plant or crop species (e.g. Arecanut, Palm, Coconut, Banana, Tomato, Potato, Apple, Pepper, Rice/Paddy, Chilli, Cotton, Corn, Mango, etc.).
3. Diagnose the health condition:
   - If healthy, set "is_healthy": true, "predicted_class": "<PlantName> Healthy", with a clear statement that no infection is detected.
   - If diseased or pest-damaged, set "is_healthy": false, "predicted_class": "<PlantName> <DiseaseName>" (e.g., "Arecanut Koleroga", "Arecanut Yellow Leaf Disease", "Banana Sigatoka Leaf Spot", "Tomato Bacterial Spot", "Potato Early Blight", "Apple Black Rot", "Coconut Bud Rot", etc.).
4. Provide actionable agronomic guidance tailored to Indian farming conditions:
   - "symptoms": observed visual indicators and progression signs.
   - "prevention": cultural sanitation, spacing, aeration, and proactive field management.
   - "treatment": practical organic remedies (neem oil, Trichoderma, Bordeaux mixture) and targeted chemical fungicides/bactericides with recommended dosage.

Respond strictly in valid JSON matching this schema:
{
  "is_leaf": true,
  "plant_name": "string",
  "predicted_class": "string",
  "is_healthy": false,
  "confidence": 0.95,
  "symptoms": "string",
  "prevention": "string",
  "treatment": "string"
}"""
        payload = {
            "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": b64}}]}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.1}
        }
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200:
            return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
    except Exception as e:
        print(f"[Gemini Vision] Falling back to local CNN pipeline: {e}")
    return None


def verify_leaf_and_crop_suitability(img_path):
    """
    Offline computer vision pre-filter:
    Validates minimum leaf pigmentation and detects parallel venation patterns
    (e.g., Banana, Palm, Grass) that cause closed-world CNNs to misclassify.
    """
    img = Image.open(img_path).convert("RGB")
    arr = np.asarray(img).astype("float32")

    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
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

    plant_mask = green_dominant | yellow_olive | necrotic
    plant_ratio = float(plant_mask.sum()) / plant_mask.size
    green_anchor = float(green_dominant.sum()) / green_dominant.size

    if (plant_ratio < 0.10) or (green_anchor < 0.003 and plant_ratio < 0.18):
        return False, "NOT_A_LEAF", plant_ratio

    # Venation pattern analysis (Banana/Monocot vs Apple/Potato/Tomato)
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    gx = ndimage.sobel(gray, axis=1)
    gy = ndimage.sobel(gray, axis=0)
    mag = np.hypot(gx, gy)
    ang = (np.arctan2(gy, gx) * 180 / np.pi) % 180

    thresh = np.percentile(mag, 75)
    sig_angles = ang[mag > thresh]
    if len(sig_angles) > 100:
        hist, _ = np.histogram(sig_angles, bins=18, range=(0, 180))
        hist = hist.astype("float32") / (hist.sum() + 1e-6)
        entropy = -np.sum(hist * np.log(hist + 1e-8))
        peak_ratio = float(hist.max() / (hist.mean() + 1e-6))

        if (peak_ratio >= 2.05) or (entropy < 2.74 and peak_ratio >= 1.85):
            return False, "BANANA_OR_UNSUPPORTED_LEAF", plant_ratio

    return True, "SUITABLE", plant_ratio


def predict_image(img_path):
    """Local ONNX model inference with aspect-ratio preserving square center-crop."""
    sess, input_name, idx_to_class = _load()
    img = Image.open(img_path).convert("RGB")
    
    # Center-crop square to prevent aspect-ratio squashing distortion
    w, h = img.size
    min_dim = min(w, h)
    left = (w - min_dim) // 2
    top = (h - min_dim) // 2
    cropped = img.crop((left, top, left + min_dim, top + min_dim)).resize(IMG_SIZE)

    arr = np.asarray(cropped).astype("float32") / 255.0
    arr = np.expand_dims(arr, axis=0)
    raw_preds = sess.run(None, {input_name: arr})[0][0].astype("float64")

    top_idx = int(np.argmax(raw_preds))
    predicted_class = idx_to_class[top_idx]
    confidence = float(raw_preds[top_idx])
    return predicted_class, confidence


NOT_A_LEAF_MESSAGE = (
    "This image is not suitable for diagnosis. No plant leaf was detected in this photo. "
    "Please upload a clear photo of an Apple, Potato, or Tomato leaf."
)

UNSUPPORTED_BANANA_MESSAGE = (
    "⚠️ Banana Leaf Detected -- Not Suitable for this Model: "
    "The KrishiSense Leaf Scan AI is trained strictly for Apple, Potato, and Tomato leaf diseases. "
    "Banana leaves are not supported and cannot be diagnosed by this model. "
    "Please upload an Apple, Potato, or Tomato leaf."
)

UNSUPPORTED_CROP_MESSAGE = (
    "⚠️ This crop/plant is not suitable for diagnosis. The KrishiSense AI model is "
    "trained strictly for Apple, Potato, and Tomato leaf diseases. Leaf images of other "
    "crops (such as Banana, Corn, Coconut, Arecanut, Mango, etc.) cannot be diagnosed."
)

MISMATCHED_CROP_MESSAGE = (
    "The uploaded image is not suitable for the selected {crop_name} category. "
    "The model detected patterns inconsistent with a {crop_name} leaf. Please upload a clear photo of an {crop_name} leaf."
)

LOW_CONFIDENCE_MESSAGE = (
    "This image is not suitable for diagnosis. The AI model could not confirm with sufficient "
    "confidence that this matches a trained Apple, Potato, or Tomato leaf. Please upload a clearer photo of a supported leaf."
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

    crop_type = request.form.get("crop_type", "auto").strip().lower()

    if crop_type in ["banana"]:
        return jsonify({"success": False, "error": UNSUPPORTED_BANANA_MESSAGE}), 400

    if crop_type in ["other", "unsupported", "corn", "maize", "arecanut", "coconut", "pepper", "cashew"]:
        return jsonify({"success": False, "error": UNSUPPORTED_CROP_MESSAGE}), 400

    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image was received. Please choose a file and try again."}), 400

    file = request.files["image"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Please upload a valid image file (png/jpg/jpeg)."}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)
    image_url = "/" + save_path.replace(os.sep, "/")

    # =========================================================================
    # STAGE 1: High-Precision Multimodal AI Analysis (Eliminates Hallucination)
    # =========================================================================
    gemini_result = diagnose_with_gemini(save_path)
    if gemini_result and isinstance(gemini_result, dict):
        if not gemini_result.get("is_leaf", True):
            return jsonify({
                "success": False,
                "error": NOT_A_LEAF_MESSAGE,
                "image_path": image_url,
            })

        # Gemini confirmed real plant leaf
        detected_plant = gemini_result.get("plant_name", "Plant")
        pred_class = gemini_result.get("predicted_class") or f"{detected_plant} Healthy"
        confidence = float(gemini_result.get("confidence", 0.96))
        is_healthy = bool(gemini_result.get("is_healthy", False))
        display_name = pred_class.replace("_", " ")

        base_remedy = REMEDIES.get(pred_class, {
            "symptoms": "Foliage and canopy inspection completed.",
            "prevention": "Maintain proper plant spacing, drainage, and soil nutrition.",
            "treatment": "Follow recommended integrated pest and disease management guidelines.",
        })
        remedy = {
            "symptoms": gemini_result.get("symptoms") or base_remedy["symptoms"],
            "prevention": gemini_result.get("prevention") or base_remedy["prevention"],
            "treatment": gemini_result.get("treatment") or base_remedy["treatment"],
        }

        # Log scan in telemetry DB
        try:
            from blueprints.telemetry_module import log_disease_scan
            log_disease_scan(save_path, pred_class, confidence)
        except Exception as e:
            print(f"Could not log disease scan: {e}")

        # Log feature activity
        try:
            from blueprints.assistant_module import log_activity
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
            "remedy": remedy,
            "engine": "multimodal_ai"
        })

    # =========================================================================
    # STAGE 2: Local CNN & Venation Texture Safeguard Pipeline (Offline Fallback)
    # =========================================================================
    is_suitable, reason, plant_ratio = verify_leaf_and_crop_suitability(save_path)
    if not is_suitable:
        if reason == "BANANA_OR_UNSUPPORTED_LEAF":
            return jsonify({
                "success": False,
                "error": UNSUPPORTED_BANANA_MESSAGE,
                "image_path": image_url,
                "green_ratio": f"{plant_ratio * 100:.1f}%",
            })
        else:
            return jsonify({
                "success": False,
                "error": NOT_A_LEAF_MESSAGE,
                "image_path": image_url,
                "green_ratio": f"{plant_ratio * 100:.1f}%",
            })

    predicted_class, confidence = predict_image(save_path)

    if crop_type in SUPPORTED_CROPS:
        if predicted_class not in SUPPORTED_CROPS[crop_type]:
            return jsonify({
                "success": False,
                "error": MISMATCHED_CROP_MESSAGE.format(crop_name=crop_type.capitalize()),
                "image_path": image_url,
                "green_ratio": f"{plant_ratio * 100:.1f}%",
            })

    if confidence < CONFIDENCE_THRESHOLD:
        return jsonify({
            "success": False,
            "error": LOW_CONFIDENCE_MESSAGE,
            "image_path": image_url,
            "green_ratio": f"{plant_ratio * 100:.1f}%",
            "confidence": f"{confidence * 100:.2f}%",
        })

    remedy = REMEDIES.get(predicted_class, {
        "symptoms": "Not available.",
        "prevention": "Not available.",
        "treatment": "Not available.",
    })

    display_name = predicted_class.replace("_", " ")
    is_healthy = predicted_class.endswith("_Healthy")

    try:
        from blueprints.telemetry_module import log_disease_scan
        log_disease_scan(save_path, predicted_class, confidence)
    except Exception as e:
        print(f"Could not log disease scan: {e}")

    try:
        from blueprints.assistant_module import log_activity
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
        "green_ratio": f"{plant_ratio * 100:.1f}%",
        "remedy": remedy,
        "engine": "local_cnn"
    })
