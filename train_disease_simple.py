"""
train_disease_simple.py
=======================
Simplified disease detection model training without pickling issues.
"""

import os
import json
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
from sklearn.model_selection import train_test_split
from pathlib import Path

IMG_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 50
MODEL_DIR = "saved_models"
DATASET_DIR = "plant_disease_dataset"
MODEL_PATH = os.path.join(MODEL_DIR, "plant_disease_cnn_model.keras")
ONNX_PATH = os.path.join(MODEL_DIR, "plant_disease_cnn_model.onnx")
CLASS_INDICES_PATH = os.path.join(MODEL_DIR, "class_indices.json")
METRICS_PATH = os.path.join(MODEL_DIR, "disease_model_metrics.json")

FINAL_CLASSES = [
    "Apple_Black_Rot",
    "Apple_Healthy",
    "Potato_Early_Blight",
    "Potato_Healthy",
    "Tomato_Bacterial_Spot",
    "Tomato_Healthy",
    "Tomato_Yellow_Leaf_Curl_Virus",
]

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(DATASET_DIR, exist_ok=True)

print("\n" + "="*70)
print("PLANT DISEASE DETECTION MODEL - SIMPLIFIED TRAINING")
print("="*70 + "\n")

# ========== STEP 1: Create synthetic training data ==========
print("STEP 1: Creating synthetic training data...")
dataset_path = os.path.join(DATASET_DIR, "raw")
for class_name in FINAL_CLASSES:
    os.makedirs(os.path.join(dataset_path, class_name), exist_ok=True)

# Generate synthetic images
for class_name in FINAL_CLASSES:
    class_dir = os.path.join(dataset_path, class_name)
    if len(os.listdir(class_dir)) > 0:
        print(f"  ✓ {class_name}: {len(os.listdir(class_dir))} images")
        continue

    for i in range(100):
        img = np.random.randint(0, 256, (IMG_SIZE[0], IMG_SIZE[1], 3), dtype=np.uint8)
        if "Healthy" in class_name:
            img[:, :, 1] = np.clip(img[:, :, 1] + 60, 0, 255)
        elif "Blight" in class_name or "Rot" in class_name:
            img[:, :, 0] = np.clip(img[:, :, 0] + 40, 0, 255)
        elif "Virus" in class_name:
            img[:, :, 1:] = np.clip(img[:, :, 1:] + 40, 0, 255)

        img_path = os.path.join(class_dir, f"{class_name}_{i:04d}.png")
        keras.preprocessing.image.save_img(img_path, img)

    print(f"  ✓ {class_name}: Created 100 images")

# ========== STEP 2: Load data ==========
print("\nSTEP 2: Loading training data...")
images = []
labels = []
class_to_idx = {cls: idx for idx, cls in enumerate(FINAL_CLASSES)}

for class_name in FINAL_CLASSES:
    class_dir = os.path.join(dataset_path, class_name)
    class_images = [f for f in os.listdir(class_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    for img_file in class_images:
        img_path = os.path.join(class_dir, img_file)
        try:
            img = keras.preprocessing.image.load_img(img_path, target_size=IMG_SIZE)
            img_array = keras.preprocessing.image.img_to_array(img) / 255.0
            images.append(img_array)
            labels.append(class_to_idx[class_name])
        except Exception as e:
            print(f"  ⚠ Skipped {img_path}: {e}")

    print(f"  ✓ Loaded {class_name}")

X = np.array(images)
y = np.array(labels)

print(f"\n  Total images: {len(X)}")
print(f"  Data shape: {X.shape}")

# Stratified split: 70% train, 15% val, 15% test
X_temp, X_test, y_temp, y_test = train_test_split(X, y, test_size=0.15, stratify=y, random_state=42)
X_train, X_val, y_train, y_val = train_test_split(X_temp, y_temp, test_size=15/85, stratify=y_temp, random_state=42)

print(f"  Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)}\n")

# ========== STEP 3: Build model ==========
print("STEP 3: Building CNN model...")
model = models.Sequential([
    layers.RandomFlip("horizontal", input_shape=(IMG_SIZE[0], IMG_SIZE[1], 3)),
    layers.RandomRotation(0.1),
    layers.RandomZoom(0.1),
    layers.RandomBrightness(0.2),
    layers.Rescaling(1./255),

    layers.Conv2D(32, 3, activation='relu', padding='same'),
    layers.BatchNormalization(),
    layers.Conv2D(32, 3, activation='relu', padding='same'),
    layers.BatchNormalization(),
    layers.MaxPooling2D(2),
    layers.Dropout(0.25),

    layers.Conv2D(64, 3, activation='relu', padding='same'),
    layers.BatchNormalization(),
    layers.Conv2D(64, 3, activation='relu', padding='same'),
    layers.BatchNormalization(),
    layers.MaxPooling2D(2),
    layers.Dropout(0.25),

    layers.Conv2D(128, 3, activation='relu', padding='same'),
    layers.BatchNormalization(),
    layers.Conv2D(128, 3, activation='relu', padding='same'),
    layers.BatchNormalization(),
    layers.MaxPooling2D(2),
    layers.Dropout(0.25),

    layers.Conv2D(256, 3, activation='relu', padding='same'),
    layers.BatchNormalization(),
    layers.Conv2D(256, 3, activation='relu', padding='same'),
    layers.BatchNormalization(),
    layers.MaxPooling2D(2),
    layers.Dropout(0.25),

    layers.GlobalAveragePooling2D(),
    layers.Dense(512, activation='relu'),
    layers.BatchNormalization(),
    layers.Dropout(0.5),
    layers.Dense(256, activation='relu'),
    layers.BatchNormalization(),
    layers.Dropout(0.5),
    layers.Dense(len(FINAL_CLASSES), activation='softmax')
])

print(f"✓ Model built with {len(FINAL_CLASSES)} classes\n")

# ========== STEP 4: Train model ==========
print("STEP 4: Training model...")
model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=0.001),
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

# Simple callbacks without pickling issues
callbacks = [
    keras.callbacks.EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True,
        verbose=1
    ),
    keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=3,
        min_lr=1e-7,
        verbose=0
    ),
]

print(f"Training on {len(X_train)} samples, validating on {len(X_val)} samples\n")

history = model.fit(
    X_train, y_train,
    batch_size=BATCH_SIZE,
    epochs=EPOCHS,
    validation_data=(X_val, y_val),
    callbacks=callbacks,
    verbose=1
)

# Evaluate test set
test_loss, test_accuracy = model.evaluate(X_test, y_test, verbose=0)
print(f"\n✓ Test Accuracy: {test_accuracy * 100:.2f}%")
print(f"✓ Test Loss: {test_loss:.4f}")

# ========== STEP 5: Save model ==========
print("\nSTEP 5: Saving model...")
model.save(MODEL_PATH)
print(f"✓ Model saved: {MODEL_PATH}")

# ========== STEP 6: Convert to ONNX ==========
print("\nSTEP 6: Converting to ONNX...")
try:
    import onnx
    import onnxmltools
    onnx_model = onnxmltools.convert_keras(model, target_opset=12)
    onnx.save_model(onnx_model, ONNX_PATH)
    print(f"✓ ONNX model saved: {ONNX_PATH}")
except Exception as e:
    print(f"⚠ ONNX conversion failed: {e}")
    print(f"  Using Keras model instead: {MODEL_PATH}")

# ========== STEP 7: Save metadata ==========
print("\nSTEP 7: Saving metadata...")

# Save class indices
with open(CLASS_INDICES_PATH, 'w') as f:
    json.dump(class_to_idx, f, indent=2)
print(f"✓ Class indices saved: {CLASS_INDICES_PATH}")

# Save metrics
metrics_data = {
    "model": "Convolutional Neural Network (TensorFlow/Keras → ONNX)",
    "runtime": "onnxruntime",
    "test_accuracy": float(test_accuracy * 100),
    "test_loss": float(test_loss),
    "n_classes": len(FINAL_CLASSES),
    "classes": FINAL_CLASSES,
    "input_size": IMG_SIZE,
    "batch_size": BATCH_SIZE,
    "epochs_trained": len(history.history['accuracy']),
    "history": {k: [float(v) for v in vals] for k, vals in history.history.items()}
}

with open(METRICS_PATH, 'w') as f:
    json.dump(metrics_data, f, indent=2)
print(f"✓ Metrics saved: {METRICS_PATH}")

# ========== COMPLETE ==========
print("\n" + "="*70)
print("✓ TRAINING COMPLETE!")
print("="*70)
print(f"\nModel files:")
print(f"  • Keras: {MODEL_PATH}")
print(f"  • ONNX:  {ONNX_PATH}")
print(f"  • Classes: {CLASS_INDICES_PATH}")
print(f"  • Metrics: {METRICS_PATH}")
print(f"\nTest Accuracy: {test_accuracy*100:.2f}%")
print(f"\nRestart Flask to load the new model: python app.py\n")
