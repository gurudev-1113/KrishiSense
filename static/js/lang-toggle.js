/*
 * KrishiSense language toggle (EN / ಕನ್ನಡ)
 * ------------------------------------------
 * Replaces the old Google Translate widget with a simple in-house
 * toggle. Mark any text you want translated with a data-i18n="key"
 * attribute (or data-i18n-placeholder="key" for input placeholders),
 * and add the English/Kannada pair to the DICT object below.
 *
 * The chosen language is remembered (localStorage) and re-applied on
 * every page automatically -- no per-page wiring needed beyond
 * including this script and dropping in a `.lang-toggle` button pair:
 *
 *   <div class="lang-toggle" id="langToggle">
 *     <button type="button" class="lang-btn active" data-lang="en">EN</button>
 *     <button type="button" class="lang-btn" data-lang="kn">ಕನ</button>
 *   </div>
 *
 * NOTE ON COVERAGE: this dictionary currently covers the shared
 * navigation, landing page and auth-form copy. Page-specific dashboard
 * text (e.g. deep inside the price/model-comparison tables) still
 * displays in English until keys + translations are added for it --
 * ask and it's easy to extend, this file is the single place to edit.
 */
(function () {
    const STORAGE_KEY = "krishisense_lang";

    const DICT = {
        // Shared nav / footer
        "nav.modules": { en: "Modules", kn: "ಮಾಡ್ಯೂಲ್‌ಗಳು" },
        "nav.hardware": { en: "Hardware", kn: "ಹಾರ್ಡ್‌ವೇರ್" },
        "nav.dashboard": { en: "Open Dashboard", kn: "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್ ತೆರೆಯಿರಿ" },
        "nav.login": { en: "Login", kn: "ಲಾಗಿನ್" },
        "nav.getstarted": { en: "Get Started", kn: "ಪ್ರಾರಂಭಿಸಿ" },
        "nav.logout": { en: "Logout", kn: "ಲಾಗ್ ಔಟ್" },
        "nav.pricedss": { en: "Price DSS", kn: "ಬೆಲೆ ಸಲಹೆ" },
        "nav.cropadvisor": { en: "Crop Advisor", kn: "ಬೆಳೆ ಸಲಹೆಗಾರ" },
        "nav.leafscan": { en: "Leaf Scan", kn: "ಎಲೆ ಸ್ಕ್ಯಾನ್" },
        "nav.sensornode": { en: "Sensor Node", kn: "ಸೆನ್ಸಾರ್ ನೋಡ್" },
        "nav.insights": { en: "Insights", kn: "ಒಳನೋಟಗಳು" },

        // Landing page hero
        "hero.badge": { en: "POT-SCALE SMART FARMING KIT · IOT + MACHINE LEARNING", kn: "ಪಾಟ್-ಪ್ರಮಾಣದ ಸ್ಮಾರ್ಟ್ ಕೃಷಿ ಕಿಟ್ · IOT + ಯಂತ್ರ ಕಲಿಕೆ" },
        "hero.title": { en: "One plant pot. Four decisions, no longer made blind.", kn: "ಒಂದು ಸಸ್ಯದ ಪಾಟ್. ನಾಲ್ಕು ನಿರ್ಧಾರಗಳು, ಇನ್ನು ಕುರುಡಾಗಿ ಅಲ್ಲ." },
        "hero.desc": {
            en: "KrishiSense closes the loop on what to sow, when to water, whether a leaf spot matters, and when to sell -- with a live sensor node, a crop recommender, a leaf disease detector and a mandi price forecaster in one integrated system.",
            kn: "ಏನನ್ನು ಬಿತ್ತಬೇಕು, ಯಾವಾಗ ನೀರು ಹಾಕಬೇಕು, ಎಲೆ ಚುಕ್ಕೆ ಮುಖ್ಯವೇ, ಮತ್ತು ಯಾವಾಗ ಮಾರಬೇಕು ಎಂಬುದನ್ನು KrishiSense ಒಂದೇ ವ್ಯವಸ್ಥೆಯಲ್ಲಿ ನಿರ್ಧರಿಸುತ್ತದೆ -- ಲೈವ್ ಸೆನ್ಸಾರ್ ನೋಡ್, ಬೆಳೆ ಸಲಹೆಗಾರ, ಎಲೆ ರೋಗ ಪತ್ತೆ ಮತ್ತು ಮಂಡಿ ಬೆಲೆ ಮುನ್ಸೂಚಕದೊಂದಿಗೆ."
        },

        // Auth forms
        "auth.login": { en: "Login", kn: "ಲಾಗಿನ್" },
        "auth.register": { en: "Register", kn: "ನೋಂದಣಿ" },
        "auth.username": { en: "Username", kn: "ಬಳಕೆದಾರ ಹೆಸರು" },
        "auth.password": { en: "Password", kn: "ಪಾಸ್‌ವರ್ಡ್" },
        "auth.submit": { en: "Submit", kn: "ಸಲ್ಲಿಸಿ" },

        // Crop Advisor page
        "crop.title": { en: "Crop Advisor", kn: "ಬೆಳೆ ಸಲಹೆಗಾರ" },
        "crop.subtitle": {
            en: "Two ways to get a recommendation: the standard 7-feature scientific model, or the Regional Advisor trained on real Karnataka-region farm data.",
            kn: "ಶಿಫಾರಸು ಪಡೆಯಲು ಎರಡು ವಿಧಾನಗಳು: ಪ್ರಮಾಣಿತ 7-ಅಂಶಗಳ ವೈಜ್ಞಾನಿಕ ಮಾದರಿ, ಅಥವಾ ನಿಜವಾದ ಕರ್ನಾಟಕ-ಪ್ರದೇಶದ ಕೃಷಿ ದತ್ತಾಂಶದಿಂದ ತರಬೇತಿ ಪಡೆದ ಪ್ರಾದೇಶಿಕ ಸಲಹೆಗಾರ."
        },
        "crop.tabScientific": { en: "Scientific (N-P-K)", kn: "ವೈಜ್ಞಾನಿಕ (N-P-K)" },
        "crop.tabRegional": { en: "Regional (Karnataka data)", kn: "ಪ್ರಾದೇಶಿಕ (ಕರ್ನಾಟಕ ದತ್ತಾಂಶ)" },
        "crop.soilInputsHeading": { en: "Soil & climate inputs", kn: "ಮಣ್ಣು ಮತ್ತು ಹವಾಮಾನ ಇನ್‌ಪುಟ್‌ಗಳು" },
        "crop.labelN": { en: "Nitrogen -- N (kg/ha)", kn: "ನೈಟ್ರೋಜನ್ -- N (kg/ha)" },
        "crop.labelP": { en: "Phosphorus -- P (kg/ha)", kn: "ಫಾಸ್ಫರಸ್ -- P (kg/ha)" },
        "crop.labelK": { en: "Potassium -- K (kg/ha)", kn: "ಪೊಟ್ಯಾಸಿಯಮ್ -- K (kg/ha)" },
        "crop.labelTemp": { en: "Temperature (°C)", kn: "ತಾಪಮಾನ (°C)" },
        "crop.labelHumidity": { en: "Humidity (%)", kn: "ತೇವಾಂಶ (%)" },
        "crop.labelPh": { en: "Soil pH", kn: "ಮಣ್ಣಿನ pH" },
        "crop.labelRainfall": { en: "Rainfall (mm)", kn: "ಮಳೆ (mm)" },
        "crop.sensorHint": { en: "Pre-fill this from the live sensor node's latest reading when available.", kn: "ಲಭ್ಯವಿರುವಾಗ ಲೈವ್ ಸೆನ್ಸಾರ್ ನೋಡ್‌ನ ಇತ್ತೀಚಿನ ರೀಡಿಂಗ್‌ನಿಂದ ಇದನ್ನು ಮುಂಚಿತವಾಗಿ ಭರ್ತಿ ಮಾಡಿ." },
        "crop.recommendBtn": { en: "Recommend Crops", kn: "ಬೆಳೆ ಶಿಫಾರಸು ಮಾಡಿ" },
        "crop.gapNote": {
            en: "Input gap, as documented in the synopsis: the agreed sensor kit measures pH, temperature and humidity live, but not N, P, K or rainfall. Those four values are entered manually here (from a soil-health card / weather API) until the optional NPK probe add-on is fitted.",
            kn: "ಸೆನ್ಸಾರ್ ಕಿಟ್ pH, ತಾಪಮಾನ ಮತ್ತು ತೇವಾಂಶವನ್ನು ಲೈವ್ ಆಗಿ ಅಳೆಯುತ್ತದೆ, ಆದರೆ N, P, K ಅಥವಾ ಮಳೆಯನ್ನು ಅಲ್ಲ. NPK ಪ್ರೋಬ್ ಸೇರಿಸುವವರೆಗೆ ಈ ನಾಲ್ಕು ಮೌಲ್ಯಗಳನ್ನು ಇಲ್ಲಿ ಕೈಯಾರೆ ನಮೂದಿಸಲಾಗುತ್ತದೆ."
        },
        "crop.top3Heading": { en: "Top 3 recommended crops", kn: "ಟಾಪ್ 3 ಶಿಫಾರಸು ಮಾಡಿದ ಬೆಳೆಗಳು" },
        "crop.placeholder": { en: "Fill in the readings and click Recommend to see results.", kn: "ರೀಡಿಂಗ್‌ಗಳನ್ನು ಭರ್ತಿ ಮಾಡಿ ಮತ್ತು ಫಲಿತಾಂಶಗಳನ್ನು ನೋಡಲು ಶಿಫಾರಸು ಕ್ಲಿಕ್ ಮಾಡಿ." },
        "crop.scoring": { en: "Scoring 22 crops…", kn: "22 ಬೆಳೆಗಳನ್ನು ಮೌಲ್ಯಮಾಪನ ಮಾಡಲಾಗುತ್ತಿದೆ…" },
        "crop.modelComparisonHeading": { en: "Model comparison", kn: "ಮಾದರಿ ಹೋಲಿಕೆ" },
        "crop.thAlgorithm": { en: "Algorithm", kn: "ಅಲ್ಗಾರಿದಮ್" },
        "crop.thAccuracy": { en: "Hold-out accuracy", kn: "ಹೋಲ್ಡ್-ಔಟ್ ನಿಖರತೆ" },
        "crop.thPrediction": { en: "Prediction for these inputs", kn: "ಈ ಇನ್‌ಪುಟ್‌ಗಳಿಗೆ ಮುನ್ಸೂಚನೆ" },
        "crop.runToCompare": { en: "Run a recommendation to compare all 5 models.", kn: "ಎಲ್ಲಾ 5 ಮಾದರಿಗಳನ್ನು ಹೋಲಿಸಲು ಶಿಫಾರಸು ಚಲಾಯಿಸಿ." },
        "crop.locationHeading": { en: "Location & field conditions", kn: "ಸ್ಥಳ ಮತ್ತು ಹೊಲದ ಪರಿಸ್ಥಿತಿಗಳು" },
        "crop.labelLocation": { en: "Location", kn: "ಸ್ಥಳ" },
        "crop.labelSoilType": { en: "Soil type", kn: "ಮಣ್ಣಿನ ಪ್ರಕಾರ" },
        "crop.labelIrrigation": { en: "Irrigation", kn: "ನೀರಾವರಿ" },
        "crop.labelRainfallYr": { en: "Rainfall (mm/yr)", kn: "ಮಳೆ (mm/ವರ್ಷ)" },
        "crop.regionalPlaceholder": { en: "Select your location and field conditions, then click Recommend.", kn: "ನಿಮ್ಮ ಸ್ಥಳ ಮತ್ತು ಹೊಲದ ಪರಿಸ್ಥಿತಿಗಳನ್ನು ಆಯ್ಕೆಮಾಡಿ, ನಂತರ ಶಿಫಾರಸು ಕ್ಲಿಕ್ ಮಾಡಿ." },
        "crop.regionalMatching": { en: "Matching against real Karnataka farm records…", kn: "ನಿಜವಾದ ಕರ್ನಾಟಕ ಕೃಷಿ ದಾಖಲೆಗಳ ವಿರುದ್ಧ ಹೊಂದಾಣಿಕೆ ಮಾಡಲಾಗುತ್ತಿದೆ…" },
        "crop.regionalUnavailable": {
            en: "Regional advisor model not found. Run train_regional_advisor.py to build it from data/karnataka_crop_data.csv.",
            kn: "ಪ್ರಾದೇಶಿಕ ಸಲಹೆಗಾರ ಮಾದರಿ ಕಂಡುಬಂದಿಲ್ಲ. data/karnataka_crop_data.csv ಇಂದ ಅದನ್ನು ನಿರ್ಮಿಸಲು train_regional_advisor.py ಚಲಾಯಿಸಿ."
        },
        "crop.serverUnreachable": { en: "Could not reach the server.", kn: "ಸರ್ವರ್ ಅನ್ನು ತಲುಪಲಾಗಲಿಲ್ಲ." },

        // Leaf Disease Scan page
        "disease.tagline": { en: "Module M3 · AI-Powered Plant Disease Detection", kn: "ಮಾಡ್ಯೂಲ್ M3 · AI-ಆಧಾರಿತ ಸಸ್ಯ ರೋಗ ಪತ್ತೆ" },
        "disease.badge": { en: "Apple · Potato · Tomato", kn: "ಸೇಬು · ಆಲೂಗಡ್ಡೆ · ಟೊಮೇಟೊ" },
        "disease.title": { en: "Diagnose your plant in seconds", kn: "ನಿಮ್ಮ ಸಸ್ಯವನ್ನು ಸೆಕೆಂಡುಗಳಲ್ಲಿ ಪತ್ತೆ ಮಾಡಿ" },
        "disease.desc": {
            en: "Upload a clear photo of a leaf and get an instant AI-based diagnosis, complete with prevention and treatment guidance -- right beside your photo, on this same page.",
            kn: "ಎಲೆಯ ಸ್ಪಷ್ಟ ಫೋಟೋ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ ಮತ್ತು ತಡೆಗಟ್ಟುವಿಕೆ ಮತ್ತು ಚಿಕಿತ್ಸೆಯ ಮಾರ್ಗದರ್ಶನದೊಂದಿಗೆ ತ್ವರಿತ AI-ಆಧಾರಿತ ರೋಗನಿರ್ಣಯವನ್ನು ಪಡೆಯಿರಿ -- ಈ ಪುಟದಲ್ಲಿಯೇ ನಿಮ್ಮ ಫೋಟೋದ ಪಕ್ಕದಲ್ಲಿ."
        },
        "disease.step1": { en: "1. Choose your image", kn: "1. ನಿಮ್ಮ ಚಿತ್ರವನ್ನು ಆಯ್ಕೆಮಾಡಿ" },
        "disease.dragdrop": { en: "Drag & drop a leaf image here", kn: "ಎಲೆಯ ಚಿತ್ರವನ್ನು ಇಲ್ಲಿ ಎಳೆದು ಬಿಡಿ" },
        "disease.or": { en: "or", kn: "ಅಥವಾ" },
        "disease.choose": { en: "Choose Image", kn: "ಚಿತ್ರ ಆಯ್ಕೆಮಾಡಿ" },
        "disease.change": { en: "Change image", kn: "ಚಿತ್ರ ಬದಲಿಸಿ" },
        "disease.predict": { en: "Predict Diagnosis", kn: "ಪತ್ತೆ ಮಾಡಿ" },
        "disease.step2": { en: "2. Diagnosis", kn: "2. ರೋಗನಿರ್ಣಯ" },
        "disease.placeholder": { en: "Your diagnosis will appear here after you choose an image and click Predict.", kn: "ಚಿತ್ರ ಆಯ್ಕೆ ಮಾಡಿ ಮತ್ತು ಪತ್ತೆ ಮಾಡಿ ಕ್ಲಿಕ್ ಮಾಡಿದ ನಂತರ ರೋಗನಿರ್ಣಯ ಇಲ್ಲಿ ಕಾಣಿಸುತ್ತದೆ." },
        "disease.analyzing": { en: "Analyzing image…", kn: "ಚಿತ್ರ ವಿಶ್ಲೇಷಿಸಲಾಗುತ್ತಿದೆ…" },
        "disease.confidence": { en: "Model Confidence", kn: "ಮಾದರಿ ವಿಶ್ವಾಸ" },
        "disease.symptoms": { en: "Symptoms", kn: "ಲಕ್ಷಣಗಳು" },
        "disease.prevention": { en: "Prevention", kn: "ತಡೆಗಟ್ಟುವಿಕೆ" },
        "disease.treatment": { en: "Treatment", kn: "ಚಿಕಿತ್ಸೆ" },
        "disease.scanAnother": { en: "Scan Another Leaf", kn: "ಇನ್ನೊಂದು ಎಲೆ ಸ್ಕ್ಯಾನ್ ಮಾಡಿ" },
        "disease.feat1": { en: "Instant results", kn: "ತ್ವರಿತ ಫಲಿತಾಂಶಗಳು" },
        "disease.feat2": { en: "7 disease classes", kn: "7 ರೋಗ ವರ್ಗಗಳು" },
        "disease.feat3": { en: "CNN-based model", kn: "CNN-ಆಧಾರಿತ ಮಾದರಿ" },
        "disease.footer": { en: "KrishiSense Module M3 · Not a substitute for professional agronomic advice", kn: "KrishiSense ಮಾಡ್ಯೂಲ್ M3 · ವೃತ್ತಿಪರ ಕೃಷಿ ಸಲಹೆಗೆ ಪರ್ಯಾಯವಲ್ಲ" },
        "disease.healthyBadge": { en: "Healthy Leaf", kn: "ಆರೋಗ್ಯಕರ" },
        "disease.diseasedBadge": { en: "Disease Detected", kn: "ರೋಗ ಪತ್ತೆಯಾಗಿದೆ" },

        // Sensor Node page
        "sensor.title": { en: "Sensor Node", kn: "ಸೆನ್ಸಾರ್ ನೋಡ್" },
        "sensor.badgeSimulated": { en: "DEMO DATA -- not real hardware", kn: "ಡೆಮೊ ಡೇಟಾ -- ನೈಜ ಹಾರ್ಡ್‌ವೇರ್ ಅಲ್ಲ" },
        "sensor.badgeWaiting": { en: "WAITING FOR HARDWARE", kn: "ಹಾರ್ಡ್‌ವೇರ್‌ಗಾಗಿ ಕಾಯಲಾಗುತ್ತಿದೆ" },
        "sensor.badgeConnected": { en: "ARDUINO CONNECTED", kn: "ಆರ್ಡುಯಿನೋ ಸಂಪರ್ಕಗೊಂಡಿದೆ" },
        "sensor.subtitle": { en: "Modules M1 (live monitoring) + M5 (advisory rule engine)", kn: "ಮಾಡ್ಯೂಲ್ M1 (ಲೈವ್ ಮಾನಿಟರಿಂಗ್) + M5 (ಸಲಹಾ ನಿಯಮ ಎಂಜಿನ್)" },
        "sensor.checking": { en: "Checking node status…", kn: "ನೋಡ್ ಸ್ಥಿತಿ ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ…" },
        "sensor.waitingHardware": { en: "Waiting for the sensor node to connect…", kn: "ಸೆನ್ಸಾರ್ ನೋಡ್ ಸಂಪರ್ಕಗೊಳ್ಳಲು ಕಾಯಲಾಗುತ್ತಿದೆ…" },
        "sensor.nodeOnline": { en: "Node online · last reading", kn: "ನೋಡ್ ಆನ್‌ಲೈನ್ · ಕೊನೆಯ ರೀಡಿಂಗ್" },
        "sensor.nodeUnreachable": { en: "Node unreachable · last seen", kn: "ನೋಡ್ ತಲುಪಲಾಗುತ್ತಿಲ್ಲ · ಕೊನೆಯ ಬಾರಿ ಕಂಡದ್ದು" },
        "sensor.moisture": { en: "Soil Moisture", kn: "ಮಣ್ಣಿನ ತೇವಾಂಶ" },
        "sensor.airtemp": { en: "Air Temp", kn: "ಗಾಳಿಯ ತಾಪಮಾನ" },
        "sensor.humidity": { en: "Humidity", kn: "ತೇವಾಂಶ" },
        "sensor.ph": { en: "Soil pH", kn: "ಮಣ್ಣಿನ pH" },
        "sensor.trend": { en: "24-hour trend", kn: "24-ಗಂಟೆಗಳ ಟ್ರೆಂಡ್" },
        "sensor.alertfeed": { en: "Alert feed", kn: "ಎಚ್ಚರಿಕೆ ಫೀಡ್" },
        "sensor.noAlerts": { en: "No active alerts.", kn: "ಯಾವುದೇ ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆಗಳಿಲ್ಲ." },
        "sensor.healthHeading": { en: "Plant health (10-reading average vs. trained model)", kn: "ಸಸ್ಯ ಆರೋಗ್ಯ (10-ರೀಡಿಂಗ್ ಸರಾಸರಿ vs ತರಬೇತಿ ಪಡೆದ ಮಾದರಿ)" },
        "sensor.warmingUp": { en: "Warming up...", kn: "ಬೆಚ್ಚಗಾಗುತ್ತಿದೆ..." },
        "sensor.waitingReadings": { en: "Waiting for the first 10 hardware readings.", kn: "ಮೊದಲ 10 ಹಾರ್ಡ್‌ವೇರ್ ರೀಡಿಂಗ್‌ಗಳಿಗಾಗಿ ಕಾಯಲಾಗುತ್ತಿದೆ." },

        // Model Insights page
        "insights.pageTitle": { en: "Model Insights", kn: "ಮಾದರಿ ಒಳನೋಟಗಳು" },
        "insights.pageSubtitle": { en: "Measured accuracy and trained-model graphs for every KrishiSense module in one place.", kn: "ಪ್ರತಿ ಕೃಷಿಸೆನ್ಸ್ ಮಾಡ್ಯೂಲ್‌ನ ಅಳೆದ ನಿಖರತೆ ಮತ್ತು ತರಬೇತಿ ಪಡೆದ ಮಾದರಿ ಗ್ರಾಫ್‌ಗಳು ಒಂದೇ ಸ್ಥಳದಲ್ಲಿ." },

        // Summary
        "insights.summaryHeading": { en: "Best Accuracy per Module", kn: "ಪ್ರತಿ ಮಾಡ್ಯೂಲ್‌ನ ಅತ್ಯುತ್ತಮ ನಿಖರತೆ" },
        "insights.summaryNote": { en: "Best score reached by each module: the strongest of the five price models, the strongest of the four crop algorithms, and the hold-out test accuracy for the regional advisor and the leaf-disease CNN.", kn: "ಪ್ರತಿ ಮಾಡ್ಯೂಲ್ ತಲುಪಿದ ಅತ್ಯುತ್ತಮ ಅಂಕ: ಐದು ಬೆಲೆ ಮಾದರಿಗಳಲ್ಲಿ ಅತ್ಯುತ್ತಮ, ನಾಲ್ಕು ಬೆಳೆ ಅಲ್ಗಾರಿದಮ್‌ಗಳಲ್ಲಿ ಅತ್ಯುತ್ತಮ, ಮತ್ತು ಪ್ರಾದೇಶಿಕ ಸಲಹೆಗಾರ ಹಾಗೂ ಎಲೆ-ರೋಗ CNN ಗಳ ಪರೀಕ್ಷಾ ನಿಖರತೆ." },

        // Shared table headers / labels
        "insights.thModel": { en: "Model", kn: "ಮಾದರಿ" },
        "insights.thAlgorithm": { en: "Algorithm", kn: "ಅಲ್ಗಾರಿದಮ್" },
        "insights.thAccuracy": { en: "Accuracy (%)", kn: "ನಿಖರತೆ (%)" },
        "insights.thHoldout": { en: "Hold-out Accuracy (%)", kn: "ಹೋಲ್ಡ್-ಔಟ್ ನಿಖರತೆ (%)" },
        "insights.thRmse": { en: "RMSE (Rs.)", kn: "RMSE (ರೂ.)" },
        "insights.thMae": { en: "MAE (Rs.)", kn: "MAE (ರೂ.)" },
        "insights.thMetric": { en: "Metric", kn: "ಮಾಪನ" },
        "insights.thValue": { en: "Value", kn: "ಮೌಲ್ಯ" },
        "insights.badgeBest": { en: "BEST", kn: "ಅತ್ಯುತ್ತಮ" },
        "insights.samples": { en: "Samples", kn: "ಮಾದರಿಗಳು" },
        "insights.features": { en: "Features", kn: "ಲಕ್ಷಣಗಳು" },
        "insights.engineeredFeatures": { en: "Engineered features", kn: "ರಚಿಸಿದ ಲಕ್ಷಣಗಳು" },
        "insights.cropClasses": { en: "Crop classes", kn: "ಬೆಳೆ ವರ್ಗಗಳು" },
        "insights.classes": { en: "Classes", kn: "ವರ್ಗಗಳು" },
        "insights.epochs": { en: "Epochs", kn: "ಎಪೋಕ್‌ಗಳು" },
        "insights.runtime": { en: "Runtime", kn: "ರನ್‌ಟೈಮ್" },
        "insights.bestAccuracy": { en: "Best accuracy", kn: "ಅತ್ಯುತ್ತಮ ನಿಖರತೆ" },
        "insights.trainingSamples": { en: "Training samples", kn: "ತರಬೇತಿ ಮಾದರಿಗಳು" },
        "insights.trainAccuracy": { en: "Train accuracy", kn: "ತರಬೇತಿ ನಿಖರತೆ" },
        "insights.testAccuracy": { en: "Test accuracy", kn: "ಪರೀಕ್ಷಾ ನಿಖರತೆ" },
        "insights.testF1": { en: "Test macro-F1", kn: "ಪರೀಕ್ಷಾ ಮ್ಯಾಕ್ರೋ-F1" },
        "insights.noMetricsFound": { en: "No saved metrics found.", kn: "ಯಾವುದೇ ಉಳಿಸಿದ ಮಾಪನಗಳು ಕಂಡುಬಂದಿಲ್ಲ." },

        // Module A - Mandi Price Prediction DSS
        "insights.priceHeading": { en: "Module A \u2014 Mandi Price Prediction DSS", kn: "ಮಾಡ್ಯೂಲ್ A \u2014 ಮಂಡಿ ಬೆಲೆ ಮುನ್ಸೂಚನೆ DSS" },
        "insights.priceDesc": { en: "This module predicts the modal (typical) market price for a chosen commodity and market in a given month, using five independently trained models: Linear Regression, Random Forest, XGBoost, ARIMA (a classical time-series model), and an LSTM neural network. All five run in parallel on the Model Comparison page so a user can see how much the models agree.", kn: "ಈ ಮಾಡ್ಯೂಲ್ ಆಯ್ದ ಸರಕು ಮತ್ತು ಮಾರುಕಟ್ಟೆಗೆ ನಿರ್ದಿಷ್ಟ ತಿಂಗಳಿನ ಮೋಡಲ್ (ಸಾಮಾನ್ಯ) ಮಾರುಕಟ್ಟೆ ಬೆಲೆಯನ್ನು ಐದು ಸ್ವತಂತ್ರವಾಗಿ ತರಬೇತಿ ಪಡೆದ ಮಾದರಿಗಳಿಂದ ಮುನ್ಸೂಚಿಸುತ್ತದೆ: ಲೀನಿಯರ್ ರಿಗ್ರೆಶನ್, ರ್ಯಾಂಡಮ್ ಫಾರೆಸ್ಟ್, XGBoost, ARIMA ಮತ್ತು LSTM ನ್ಯೂರಲ್ ನೆಟ್‌ವರ್ಕ್. ಎಲ್ಲಾ ಐದೂ ಮಾಡೆಲ್ ಕಂಪ್ಯಾರಿಸನ್ ಪುಟದಲ್ಲಿ ಏಕಕಾಲದಲ್ಲಿ ಚಲಿಸುತ್ತವೆ." },
        "insights.priceTableHeading": { en: "Measured accuracy", kn: "ಅಳೆದ ನಿಖರತೆ" },
        "insights.accuracyByModel": { en: "Accuracy by model", kn: "ಮಾದರಿಯ ಪ್ರಕಾರ ನಿಖರತೆ" },
        "insights.rmseMaeHeading": { en: "RMSE & MAE by model", kn: "ಮಾದರಿಯ ಪ್ರಕಾರ RMSE ಮತ್ತು MAE" },
        "insights.rmseMaeNote": { en: "Lower is better. ARIMA has the smallest error in rupees but the weakest R-squared, because it models each commodity-market series on its own without the shared features the other models use.", kn: "ಕಡಿಮೆ ಇದ್ದಷ್ಟು ಉತ್ತಮ. ARIMA ರೂಪಾಯಿಯಲ್ಲಿ ಅತಿ ಕಡಿಮೆ ದೋಷ ಹೊಂದಿದೆ ಆದರೆ ದುರ್ಬಲ R-ವರ್ಗ ಹೊಂದಿದೆ." },
        "insights.actualVsPredicted": { en: "Actual vs. predicted price", kn: "ನಿಜವಾದ vs ಅಂದಾಜು ಬೆಲೆ" },
        "insights.noRegressionSample": { en: "No regression sample saved yet -- retrain from the admin dashboard to populate this chart.", kn: "ಇನ್ನೂ ಯಾವುದೇ ರಿಗ್ರೆಶನ್ ಮಾದರಿ ಉಳಿಸಲಾಗಿಲ್ಲ." },
        "insights.noConfusionMatrix": { en: "A confusion matrix doesn't apply here -- price prediction is a regression task, not classification.", kn: "ಇಲ್ಲಿ ಗೊಂದಲ ಮ್ಯಾಟ್ರಿಕ್ಸ್ ಅನ್ವಯಿಸುವುದಿಲ್ಲ -- ಬೆಲೆ ಮುನ್ಸೂಚನೆ ರಿಗ್ರೆಶನ್ ಕೆಲಸ, ವರ್ಗೀಕರಣವಲ್ಲ." },
        "insights.noPriceMetrics": { en: "No saved metrics found (saved_models/model_metrics.json).", kn: "ಯಾವುದೇ ಉಳಿಸಿದ ಮಾಪನಗಳು ಕಂಡುಬಂದಿಲ್ಲ." },

        // Module B - Crop Recommendation Engine
        "insights.cropHeading": { en: "Module B \u2014 Crop Recommendation Engine", kn: "ಮಾಡ್ಯೂಲ್ B \u2014 ಬೆಳೆ ಶಿಫಾರಸು ಎಂಜಿನ್" },
        "insights.cropDesc": { en: "Four classifiers were trained on the updated 2,200-sample dataset (7 soil and weather features, 22 crop classes) and compared on a held-out split. Polynomial Logistic Regression is the strongest of the four.", kn: "ನವೀಕರಿಸಿದ 2,200-ಮಾದರಿ ದತ್ತಾಂಶದ ಮೇಲೆ (7 ಲಕ್ಷಣಗಳು, 22 ಬೆಳೆ ವರ್ಗಗಳು) ನಾಲ್ಕು ವರ್ಗೀಕರಣಕಾರರನ್ನು ತರಬೇತಿ ನೀಡಿ ಹೋಲಿಸಲಾಗಿದೆ. ಪಾಲಿನೋಮಿಯಲ್ ಲಾಜಿಸ್ಟಿಕ್ ರಿಗ್ರೆಶನ್ ಅತ್ಯುತ್ತಮವಾಗಿದೆ." },
        "insights.holdoutAccuracy": { en: "Hold-out accuracy by algorithm", kn: "ಅಲ್ಗಾರಿದಮ್ ಪ್ರಕಾರ ಹೋಲ್ಡ್-ಔಟ್ ನಿಖರತೆ" },
        "insights.cropTableHeading": { en: "Measured accuracy", kn: "ಅಳೆದ ನಿಖರತೆ" },

        // Module C - Regional Crop Advisor
        "insights.regionalHeading": { en: "Module C \u2014 Regional Crop Advisor (Karnataka data)", kn: "ಮಾಡ್ಯೂಲ್ C \u2014 ಪ್ರಾದೇಶಿಕ ಬೆಳೆ ಸಲಹೆಗಾರ (ಕರ್ನಾಟಕ ದತ್ತಾಂಶ)" },
        "insights.regionalDesc": { en: "A Random Forest trained on real Karnataka district-level crop records, using engineered soil, season and location features to suggest crops suited to a specific region.", kn: "ನಿಜವಾದ ಕರ್ನಾಟಕ ಜಿಲ್ಲಾ ಮಟ್ಟದ ಬೆಳೆ ದಾಖಲೆಗಳ ಮೇಲೆ ತರಬೇತಿ ಪಡೆದ ರ್ಯಾಂಡಮ್ ಫಾರೆಸ್ಟ್, ಪ್ರದೇಶಕ್ಕೆ ಸೂಕ್ತ ಬೆಳೆಗಳನ್ನು ಸೂಚಿಸುತ್ತದೆ." },
        "insights.trainVsTest": { en: "Train accuracy, test accuracy and macro-F1", kn: "ತರಬೇತಿ ನಿಖರತೆ, ಪರೀಕ್ಷಾ ನಿಖರತೆ ಮತ್ತು ಮ್ಯಾಕ್ರೋ-F1" },
        "insights.regionalTableHeading": { en: "Measured metrics", kn: "ಅಳೆದ ಮಾಪನಗಳು" },
        "insights.noRegionalMetrics": { en: "No saved metrics found -- run train_regional_advisor.py.", kn: "ಯಾವುದೇ ಉಳಿಸಿದ ಮಾಪನಗಳು ಕಂಡುಬಂದಿಲ್ಲ." },
        "insights.noConfusionRegional": { en: "The gap between train and test accuracy is the usual sign of some overfitting on the rarer crop classes, which is also why macro-F1 sits below plain accuracy.", kn: "ತರಬೇತಿ ಮತ್ತು ಪರೀಕ್ಷಾ ನಿಖರತೆಯ ನಡುವಿನ ಅಂತರವು ಅಪರೂಪದ ಬೆಳೆ ವರ್ಗಗಳಲ್ಲಿ ಸ್ವಲ್ಪ ಓವರ್‌ಫಿಟಿಂಗ್‌ನ ಸೂಚನೆ." },

        // Module D - Leaf Disease Detection
        "insights.diseaseHeading": { en: "Module D \u2014 Leaf Disease Detection", kn: "ಮಾಡ್ಯೂಲ್ D \u2014 ಎಲೆ ರೋಗ ಪತ್ತೆ" },
        "insights.diseaseDesc": { en: "This module accepts a photograph of a plant leaf and classifies it into one of seven classes across three crops using a Convolutional Neural Network exported to the ONNX runtime format for fast, framework-independent inference.", kn: "ಈ ಮಾಡ್ಯೂಲ್ ಎಲೆಯ ಚಿತ್ರವನ್ನು ಸ್ವೀಕರಿಸಿ, ONNX ರನ್‌ಟೈಮ್‌ಗೆ ರಫ್ತು ಮಾಡಿದ CNN ಬಳಸಿ ಮೂರು ಬೆಳೆಗಳ ಏಳು ವರ್ಗಗಳಲ್ಲಿ ಒಂದಾಗಿ ವರ್ಗೀಕರಿಸುತ್ತದೆ." },
        "insights.diseaseClassesHeading": { en: "Classes", kn: "ವರ್ಗಗಳು" },
        "insights.cnnAccuracyHeading": { en: "CNN training and validation accuracy", kn: "CNN ತರಬೇತಿ ಮತ್ತು ಮೌಲ್ಯಮಾಪನ ನಿಖರತೆ" },
        "insights.cnnLossHeading": { en: "CNN training and validation loss", kn: "CNN ತರಬೇತಿ ಮತ್ತು ಮೌಲ್ಯಮಾಪನ ನಷ್ಟ" },
        "insights.cnnNote": { en: "Validation loss spikes around epochs 3-6 while training loss keeps falling -- a transient divergence that settles from epoch 10 onward, where both curves converge near zero.", kn: "ಎಪೋಕ್ 3-6 ರ ಸುಮಾರಿಗೆ ಮೌಲ್ಯಮಾಪನ ನಷ್ಟ ಏರುತ್ತದೆ, ಆದರೆ ಎಪೋಕ್ 10 ರಿಂದ ಎರಡೂ ಕರ್ವ್‌ಗಳು ಶೂನ್ಯದ ಸಮೀಪ ಒಂದಾಗುತ್ತವೆ." },
        "insights.noDiseaseMetrics": { en: "No saved metrics found (saved_models/disease_model_metrics.json).", kn: "ಯಾವುದೇ ಉಳಿಸಿದ ಮಾಪನಗಳು ಕಂಡುಬಂದಿಲ್ಲ." },
    };

    function currentLang() {
        return localStorage.getItem(STORAGE_KEY) || "en";
    }

    function applyLang(lang) {
        // If this page already ships its own richer setLanguage(lang)
        // function (index.html / price dashboard does), defer to it --
        // it covers far more than the shared dictionary below.
        if (typeof window.setLanguage === "function") {
            window.setLanguage(lang);
        }
        document.querySelectorAll("[data-i18n]").forEach((el) => {
            const entry = DICT[el.getAttribute("data-i18n")];
            if (entry && entry[lang]) el.textContent = entry[lang];
        });
        document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
            const entry = DICT[el.getAttribute("data-i18n-placeholder")];
            if (entry && entry[lang]) el.setAttribute("placeholder", entry[lang]);
        });
        document.querySelectorAll(".lang-btn").forEach((btn) => {
            btn.classList.toggle("active", btn.getAttribute("data-lang") === lang);
        });
        document.documentElement.setAttribute("lang", lang === "kn" ? "kn" : "en");
        window.dispatchEvent(new CustomEvent("krishisense:langchange", { detail: { lang } }));
    }

    // Exposed so page-specific scripts can look up a shared string
    // (used by crop_recommend.html for its JS-generated result text).
    window.KrishiI18n = {
        t: function (key) {
            const entry = DICT[key];
            if (!entry) return key;
            return entry[currentLang()] || entry.en || key;
        },
        lang: currentLang,
    };

    function injectStyles() {
        if (document.getElementById("lang-toggle-styles")) return;
        const style = document.createElement("style");
        style.id = "lang-toggle-styles";
        style.textContent = `
            .lang-toggle { display:inline-flex; align-items:center; background:rgba(255,255,255,0.12);
                border-radius:30px; padding:3px; margin-right:6px; }
            .lang-toggle .lang-btn { border:none; background:transparent; color:#f0e6d2; font-weight:700;
                font-size:0.72rem; padding:5px 11px; border-radius:24px; cursor:pointer; transition:all .15s; }
            .lang-toggle .lang-btn.active { background:#b9822a; color:#fff; }
        `;
        document.head.appendChild(style);
    }

    function wireButtons() {
        document.querySelectorAll(".lang-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                const lang = btn.getAttribute("data-lang");
                localStorage.setItem(STORAGE_KEY, lang);
                applyLang(lang);
            });
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        injectStyles();
        wireButtons();
        applyLang(currentLang());
    });
})();
