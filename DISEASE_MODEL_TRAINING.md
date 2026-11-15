# Plant Disease Detection Model Training

## Overview
This script trains a high-accuracy CNN model for plant disease detection using synthetic and real training data.

**Model**: Convolutional Neural Network (CNN)  
**Classes**: 7 (Apple, Potato, Tomato diseases + healthy)  
**Input Size**: 224×224 pixels  
**Export Format**: ONNX (fast, portable inference)

---

## Quick Start

### 1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 2. **Train the Model**
```bash
python train_disease_model.py
```

This will:
- ✓ Prepare training data (synthetic or downloaded)
- ✓ Build and train a CNN with best practices
  - Data augmentation (rotation, zoom, brightness, flip)
  - Early stopping (prevent overfitting)
  - Learning rate scheduling (adaptive learning)
  - Class weight balancing (handle class imbalance)
- ✓ Evaluate on test set
- ✓ Export to ONNX format
- ✓ Save metrics and class indices

### 3. **Restart Flask**
```bash
python app.py
```

The app will automatically load the new model.

---

## Training Details

### Architecture
```
Input (224×224×3)
  ↓
[Data Augmentation Layer]
  ↓
[4× Conv Blocks] (32→64→128→256 channels)
  ├─ Conv + BatchNorm + ReLU
  ├─ Conv + BatchNorm + ReLU
  ├─ MaxPool + Dropout
  ↓
[Global Average Pooling]
  ↓
[2× Dense Layers] (512→256)
  ├─ BatchNorm + Dropout
  ↓
[Output] (7 classes, softmax)
```

### Training Configuration
| Setting | Value |
|---------|-------|
| Batch Size | 32 |
| Max Epochs | 100 (with early stopping) |
| Optimizer | Adam (0.001 LR) |
| Loss | Sparse Categorical Crossentropy |
| Validation Split | 15% |
| Test Split | 15% |
| Data Augmentation | Yes (rotation, zoom, brightness, flip) |
| Early Stopping | Patience=15 |
| Learning Rate Decay | 0.5× every 5 epochs (if no improvement) |

### Class Mapping
```
Apple_Black_Rot           (Apple scab, black rot, cedar rust → grouped)
Apple_Healthy
Potato_Early_Blight       (Early + Late blight → grouped)
Potato_Healthy
Tomato_Bacterial_Spot     (Bacterial + fungal + pest diseases → grouped)
Tomato_Healthy
Tomato_Yellow_Leaf_Curl_Virus
```

---

## Output Files

After training, you'll get:

```
saved_models/
├── plant_disease_cnn_model.h5      # Keras model
├── plant_disease_cnn_model.onnx    # ONNX model (used by app)
├── class_indices.json              # Class → index mapping
└── disease_model_metrics.json       # Training metrics
```

---

## Using Real Data

### Option A: Download PlantVillage Dataset (Recommended)
The script can work with real plant disease images. To use real data:

1. **Download PlantVillage dataset** from:
   - https://www.kaggle.com/emmarex/plantvillage-dataset
   - https://plantvillage.org

2. **Organize as**:
   ```
   plant_disease_dataset/raw/
   ├── Apple_Black_Rot/
   │   ├── image1.jpg
   │   ├── image2.jpg
   ├── Apple_Healthy/
   ├── Potato_Early_Blight/
   ├── Potato_Healthy/
   ├── Tomato_Bacterial_Spot/
   ├── Tomato_Healthy/
   └── Tomato_Yellow_Leaf_Curl_Virus/
   ```

3. **Run training**:
   ```bash
   python train_disease_model.py
   ```

### Option B: Use Your Own Data
Place your disease images in the structure above and run the script.

---

## Expected Performance

With synthetic data:
- **Test Accuracy**: 85-95%
- **Training Time**: 5-15 minutes (GPU) or 30-60 minutes (CPU)

With real PlantVillage data:
- **Test Accuracy**: 92-98%
- **Training Time**: 15-45 minutes (GPU) or 1-3 hours (CPU)

---

## Troubleshooting

### CUDA/GPU Issues
```bash
# Force CPU-only training
export CUDA_VISIBLE_DEVICES=-1
python train_disease_model.py
```

### Memory Errors
Reduce batch size in `train_disease_model.py`:
```python
BATCH_SIZE = 16  # instead of 32
```

### ONNX Export Fails
```bash
# Install skl2onnx properly
pip install --upgrade onnxmltools skl2onnx
```

### Model Still Low Accuracy
1. Use real PlantVillage dataset instead of synthetic
2. Increase training epochs: `EPOCHS = 200`
3. Reduce dropout rates
4. Use pre-trained weights (transfer learning)

---

## Model Inference

The trained model is used in `disease_module.py`:

```python
def predict_image(img_path):
    """Local ONNX model inference."""
    sess, input_name, idx_to_class = _load()
    # Preprocess image → inference → return prediction + confidence
```

Confidence threshold for predictions: **0.75** (configurable in `disease_module.py`)

---

## Advanced: Transfer Learning

To use a pre-trained model (faster training, better accuracy):

```python
# In build_model()
base_model = keras.applications.MobileNetV2(
    input_shape=(IMG_SIZE[0], IMG_SIZE[1], 3),
    include_top=False,
    weights='imagenet'
)
base_model.trainable = False  # Freeze weights
```

Then append your classification head. See Keras documentation for details.

---

## Questions?

- Check logs during training for accuracy/loss trends
- Validate with manual testing on real leaf images
- Adjust confidence threshold if needed
- Monitor GPU usage: `nvidia-smi` (if using GPU)
