// ============================================================
// DASHBOARD JAVASCRIPT - COMPLETE FIXED VERSION
// ALL 10 YEARS (2015-2024) DISPLAYED IN MONTHLY CHART
// X-AXIS SHOWS FULL DATES WITH YEAR
// KANNADA LANGUAGE SUPPORT
// MODEL COMPARISON TABLE REMOVED (Moved to separate page)
// ============================================================

// ============================================================
// LANGUAGE TRANSLATIONS
// ============================================================
const translations = {
    'en': {
        'logoSub': 'Agricultural Price Prediction',
        'logout': 'Logout',
        'compareNav': 'Compare',
        'adminNav': 'Admin',
        'pageTitle': 'Price Prediction Dashboard',
        'pageSubtitle': 'Select a commodity, market, and month to get instant price predictions and historical trends',
        'selectionLabel': 'Select Crop, Market & Month',
        'commodityLabel': 'Commodity',
        'marketLabel': 'Market',
        'monthLabel': 'Month',
        'predictLabel': 'Get Prediction',
        'selectCommodity': 'Select commodity first',
        'loadingMarkets': 'Loading...',
        'noMarkets': 'No markets found',
        'currentPrice': 'Current Price',
        'predictedPrice': 'Predicted Price',
        'expectedChange': 'Expected Change',
        'confidence': 'Confidence',
        'insightBestModel': 'Best Model',
        'insightLowestRMSE': 'Lowest RMSE',
        'insightLowestMAE': 'Lowest MAE',
        'insightModelsWorking': 'Models Working',
        'viewModelsLabel': 'View Full Model Comparison',
        'dataPointsLabel': 'days of historical data',
        'seasonalAvgLabel': 'seasonal average',
        'modelsWorkingLabel': 'models working',
        'recordsLabel': 'records in this month',
        'chart365Label': '365-Day Price Trend',
        'chartYearlyLabel': 'Yearly Comparison for',
        'refreshLabel': 'Refresh',
        'selectMonth': 'Select Month',
        'noHistoricalData': 'No historical data available for this month',
        'loadingYearlyData': 'Loading yearly data...',
        'runPredictionFirst': 'Run a prediction first to see yearly data',
        'monthlyAvg': 'Monthly Avg',
        'lastUpdated': 'Last updated',
        'monthlyAvgPrice': 'Monthly Avg Price',
        'predicted': 'Predicted price',
        'current': 'Current',
        'on': 'on',
        'for': 'for',
        'runningModels': 'Running models…',
        'requestFailed': 'Request failed. Is the Flask server running?',
        'sell': 'SELL',
        'store': 'STORE',
        'wait': 'WAIT',
        'recSell': 'SELL',
        'recStore': 'STORE',
        'recWait': 'WAIT',
        'recPriceHigh': 'Price is near its yearly high and expected to rise',
        'recPriceHighMax': 'Price is at its yearly high. Sell now for maximum profit!',
        'recPriceLow': 'Price is near yearly low and expected to rise. Store your crop for better prices!',
        'recRiseSignificant': 'Price expected to rise significantly. Store your crop and sell later for higher profit!',
        'recRiseModerate': 'Price expected to rise. Better to store the crop a little longer.',
        'recDropSignificant': 'Price expected to drop. Sell now to avoid losses!',
        'recDropModerate': 'Price expected to decrease slightly. Consider selling now.',
        'recVolatile': 'Market is volatile. Wait for stability before making a decision.',
        'recModerateVolatile': 'Market is moderately volatile. Monitor prices for a few days.',
        'recStableHigh': 'Prices are stable but near yearly high. Consider selling now.',
        'recStableLow': 'Prices are stable but near yearly low. Store and wait for price recovery.',
        'recStable': 'Prices are stable. Wait for a better opportunity.',
        'recReasonable': 'Price expected to change. Selling now is a reasonable choice.',
        'recInsufficient': 'Insufficient data for a recommendation. Please check your selection.',
        'seasonalAbove': 'Above average for this season — good time to sell!',
        'seasonalBelow': 'Below average for this season — consider storing for better prices.',
        'seasonalAverage': 'Prices are at seasonal average — wait for the right moment.',
        'basedOnMonthlyAvg': 'Based on monthly average of ₹{price} from {count} records in {years} years',
        'forecastTableTitle': 'Next 5 Months Forecast',
        'forecastMonthHeader': 'Month',
        'forecastPriceHeader': 'Predicted Value'
    },
    'kn': {
        'logoSub': 'ಕೃಷಿ ಬೆಲೆ ಮುನ್ಸೂಚನೆ',
        'logout': 'ನಿರ್ಗಮಿಸಿ',
        'compareNav': 'ಹೋಲಿಕೆ',
        'adminNav': 'ನಿರ್ವಾಹಕ',
        'pageTitle': 'ಬೆಲೆ ಮುನ್ಸೂಚನೆ ಡ್ಯಾಶ್ಬೋರ್ಡ್',
        'pageSubtitle': 'ಬೆಳೆ, ಮಾರುಕಟ್ಟೆ ಮತ್ತು ತಿಂಗಳು ಆಯ್ಕೆಮಾಡಿ - ತಕ್ಷಣದ ಬೆಲೆ ಮುನ್ಸೂಚನೆ ಮತ್ತು ಐತಿಹಾಸಿಕ ಪ್ರವೃತ್ತಿಗಳನ್ನು ಪಡೆಯಿರಿ',
        'selectionLabel': 'ಬೆಳೆ, ಮಾರುಕಟ್ಟೆ ಮತ್ತು ತಿಂಗಳು ಆಯ್ಕೆಮಾಡಿ',
        'commodityLabel': 'ಬೆಳೆ',
        'marketLabel': 'ಮಾರುಕಟ್ಟೆ',
        'monthLabel': 'ತಿಂಗಳು',
        'predictLabel': 'ಮುನ್ಸೂಚನೆ ಪಡೆಯಿರಿ',
        'selectCommodity': 'ಮೊದಲು ಬೆಳೆ ಆಯ್ಕೆಮಾಡಿ',
        'loadingMarkets': 'ಲೋಡ್ ಆಗುತ್ತಿದೆ...',
        'noMarkets': 'ಮಾರುಕಟ್ಟೆಗಳು ಕಂಡುಬಂದಿಲ್ಲ',
        'currentPrice': 'ಪ್ರಸ್ತುತ ಬೆಲೆ',
        'predictedPrice': 'ಮುನ್ಸೂಚಿತ ಬೆಲೆ',
        'expectedChange': 'ನಿರೀಕ್ಷಿತ ಬದಲಾವಣೆ',
        'confidence': 'ವಿಶ್ವಾಸಾರ್ಹತೆ',
        'insightBestModel': 'ಉತ್ತಮ ಮಾದರಿ',
        'insightLowestRMSE': 'ಕಡಿಮೆ RMSE',
        'insightLowestMAE': 'ಕಡಿಮೆ MAE',
        'insightModelsWorking': 'ಕಾರ್ಯನಿರ್ವಹಿಸುವ ಮಾದರಿಗಳು',
        'viewModelsLabel': 'ಪೂರ್ಣ ಮಾದರಿ ಹೋಲಿಕೆ ನೋಡಿ',
        'dataPointsLabel': 'ದಿನಗಳ ಐತಿಹಾಸಿಕ ಡೇಟಾ',
        'seasonalAvgLabel': 'ಋತುಮಾನದ ಸರಾಸರಿ',
        'modelsWorkingLabel': 'ಮಾದರಿಗಳು ಕಾರ್ಯನಿರ್ವಹಿಸುತ್ತಿವೆ',
        'recordsLabel': 'ಈ ತಿಂಗಳ ದಾಖಲೆಗಳು',
        'chart365Label': '೩೬೫ ದಿನಗಳ ಬೆಲೆ ಪ್ರವೃತ್ತಿ',
        'chartYearlyLabel': 'ವಾರ್ಷಿಕ ಹೋಲಿಕೆ',
        'refreshLabel': 'ರಿಫ್ರೆಶ್',
        'selectMonth': 'ತಿಂಗಳು ಆಯ್ಕೆಮಾಡಿ',
        'noHistoricalData': 'ಈ ತಿಂಗಳಿಗೆ ಐತಿಹಾಸಿಕ ಡೇಟಾ ಲಭ್ಯವಿಲ್ಲ',
        'loadingYearlyData': 'ವಾರ್ಷಿಕ ಡೇಟಾ ಲೋಡ್ ಆಗುತ್ತಿದೆ...',
        'runPredictionFirst': 'ವಾರ್ಷಿಕ ಡೇಟಾ ನೋಡಲು ಮೊದಲು ಮುನ್ಸೂಚನೆ ರನ್ ಮಾಡಿ',
        'monthlyAvg': 'ಮಾಸಿಕ ಸರಾಸರಿ',
        'lastUpdated': 'ಕೊನೆಯ ನವೀಕರಣ',
        'monthlyAvgPrice': 'ಮಾಸಿಕ ಸರಾಸರಿ ಬೆಲೆ',
        'predicted': 'ಮುನ್ಸೂಚಿತ ಬೆಲೆ',
        'current': 'ಪ್ರಸ್ತುತ',
        'on': 'ರಂದು',
        'for': 'ಕ್ಕೆ',
        'runningModels': 'ಮಾದರಿಗಳನ್ನು ರನ್ ಮಾಡಲಾಗುತ್ತಿದೆ…',
        'requestFailed': 'ವಿನಂತಿ ವಿಫಲವಾಗಿದೆ. Flask ಸರ್ವರ್ ಚಾಲನೆಯಲ್ಲಿದೆಯೇ?',
        'sell': 'ಮಾರಾಟ ಮಾಡಿ',
        'store': 'ಸಂಗ್ರಹಿಸಿ',
        'wait': 'ನಿರೀಕ್ಷಿಸಿ',
        'recSell': 'ಮಾರಾಟ ಮಾಡಿ',
        'recStore': 'ಸಂಗ್ರಹಿಸಿ',
        'recWait': 'ನಿರೀಕ್ಷಿಸಿ',
        'recPriceHigh': 'ಬೆಲೆ ವಾರ್ಷಿಕ ಗರಿಷ್ಠ ಮಟ್ಟದಲ್ಲಿದೆ ಮತ್ತು ಏರಿಕೆಯ ನಿರೀಕ್ಷೆಯಿದೆ',
        'recPriceHighMax': 'ಬೆಲೆ ವಾರ್ಷಿಕ ಗರಿಷ್ಠ ಮಟ್ಟದಲ್ಲಿದೆ. ಗರಿಷ್ಠ ಲಾಭಕ್ಕಾಗಿ ಈಗ ಮಾರಾಟ ಮಾಡಿ!',
        'recPriceLow': 'ಬೆಲೆ ವಾರ್ಷಿಕ ಕನಿಷ್ಠ ಮಟ್ಟದಲ್ಲಿದೆ ಮತ್ತು ಏರಿಕೆಯ ನಿರೀಕ್ಷೆಯಿದೆ. ಉತ್ತಮ ಬೆಲೆಗೆ ನಿಮ್ಮ ಬೆಳೆಯನ್ನು ಸಂಗ್ರಹಿಸಿ!',
        'recRiseSignificant': 'ಬೆಲೆ ಗಣನೀಯವಾಗಿ ಏರುವ ನಿರೀಕ್ಷೆಯಿದೆ. ಹೆಚ್ಚಿನ ಲಾಭಕ್ಕಾಗಿ ಬೆಳೆಯನ್ನು ಸಂಗ್ರಹಿಸಿ ಮತ್ತು ನಂತರ ಮಾರಾಟ ಮಾಡಿ!',
        'recRiseModerate': 'ಬೆಲೆ ಏರುವ ನಿರೀಕ್ಷೆಯಿದೆ. ಸ್ವಲ್ಪ ಸಮಯ ಬೆಳೆಯನ್ನು ಸಂಗ್ರಹಿಸುವುದು ಉತ್ತಮ.',
        'recDropSignificant': 'ಬೆಲೆ ಕುಸಿಯುವ ನಿರೀಕ್ಷೆಯಿದೆ. ನಷ್ಟವನ್ನು ತಪ್ಪಿಸಲು ಈಗ ಮಾರಾಟ ಮಾಡಿ!',
        'recDropModerate': 'ಬೆಲೆ ಸ್ವಲ್ಪ ಕುಸಿಯುವ ನಿರೀಕ್ಷೆಯಿದೆ. ಈಗ ಮಾರಾಟ ಮಾಡುವುದನ್ನು ಪರಿಗಣಿಸಿ.',
        'recVolatile': 'ಮಾರುಕಟ್ಟೆಯಲ್ಲಿ ಏರಿಳಿತವಿದೆ. ನಿರ್ಧಾರ ತೆಗೆದುಕೊಳ್ಳುವ ಮೊದಲು ಸ್ಥಿರತೆಗಾಗಿ ನಿರೀಕ್ಷಿಸಿ.',
        'recModerateVolatile': 'ಮಾರುಕಟ್ಟೆಯಲ್ಲಿ ಮಧ್ಯಮ ಏರಿಳಿತವಿದೆ. ಕೆಲವು ದಿನಗಳವರೆಗೆ ಬೆಲೆಗಳನ್ನು ಮೇಲ್ವಿಚಾರಣೆ ಮಾಡಿ.',
        'recStableHigh': 'ಬೆಲೆಗಳು ಸ್ಥಿರವಾಗಿವೆ ಆದರೆ ವಾರ್ಷಿಕ ಗರಿಷ್ಠ ಮಟ್ಟದಲ್ಲಿವೆ. ಈಗ ಮಾರಾಟ ಮಾಡುವುದನ್ನು ಪರಿಗಣಿಸಿ.',
        'recStableLow': 'ಬೆಲೆಗಳು ಸ್ಥಿರವಾಗಿವೆ ಆದರೆ ವಾರ್ಷಿಕ ಕನಿಷ್ಠ ಮಟ್ಟದಲ್ಲಿವೆ. ಸಂಗ್ರಹಿಸಿ ಮತ್ತು ಬೆಲೆ ಚೇತರಿಕೆಗಾಗಿ ನಿರೀಕ್ಷಿಸಿ.',
        'recStable': 'ಬೆಲೆಗಳು ಸ್ಥಿರವಾಗಿವೆ. ಉತ್ತಮ ಅವಕಾಶಕ್ಕಾಗಿ ನಿರೀಕ್ಷಿಸಿ.',
        'recReasonable': 'ಬೆಲೆ ಬದಲಾಗುವ ನಿರೀಕ್ಷೆಯಿದೆ. ಈಗ ಮಾರಾಟ ಮಾಡುವುದು ಸಮಂಜಸವಾದ ಆಯ್ಕೆಯಾಗಿದೆ.',
        'recInsufficient': 'ಶಿಫಾರಸಿಗೆ ಸಾಕಷ್ಟು ಡೇಟಾ ಇಲ್ಲ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ಆಯ್ಕೆಯನ್ನು ಪರಿಶೀಲಿಸಿ.',
        'seasonalAbove': 'ಈ ಋತುವಿನ ಸರಾಸರಿಗಿಂತ ಹೆಚ್ಚು — ಮಾರಾಟ ಮಾಡಲು ಉತ್ತಮ ಸಮಯ!',
        'seasonalBelow': 'ಈ ಋತುವಿನ ಸರಾಸರಿಗಿಂತ ಕಡಿಮೆ — ಉತ್ತಮ ಬೆಲೆಗೆ ಸಂಗ್ರಹಿಸುವುದನ್ನು ಪರಿಗಣಿಸಿ.',
        'seasonalAverage': 'ಬೆಲೆಗಳು ಋತುಮಾನದ ಸರಾಸರಿಯಲ್ಲಿವೆ — ಸರಿಯಾದ ಕ್ಷಣಕ್ಕಾಗಿ ನಿರೀಕ್ಷಿಸಿ.',
        'basedOnMonthlyAvg': '₹{price} ರ ಮಾಸಿಕ ಸರಾಸರಿ ಆಧಾರದಲ್ಲಿ {count} ದಾಖಲೆಗಳು {years} ವರ್ಷಗಳಲ್ಲಿ',
        'forecastTableTitle': 'ಮುಂದಿನ 5 ತಿಂಗಳ ಮುನ್ಸೂಚನೆ',
        'forecastMonthHeader': 'ತಿಂಗಳು',
        'forecastPriceHeader': 'ಮುನ್ಸೂಚಿತ ಬೆಲೆ'
    }
};

// ============================================================
// GLOBAL VARIABLES
// ============================================================
let currentLang = 'en';
let priceChart = null;
let monthlyChartInstance = null;
let currentPredictionData = null;
let currentForecastData = null;
let statusMsg = document.getElementById('statusMsg');

const monthNamesKn = {
    '01': 'ಜನವರಿ', '02': 'ಫೆಬ್ರವರಿ', '03': 'ಮಾರ್ಚ್', '04': 'ಏಪ್ರಿಲ್',
    '05': 'ಮೇ', '06': 'ಜೂನ್', '07': 'ಜುಲೈ', '08': 'ಆಗಸ್ಟ್',
    '09': 'ಸೆಪ್ಟೆಂಬರ್', '10': 'ಅಕ್ಟೋಬರ್', '11': 'ನವೆಂಬರ್', '12': 'ಡಿಸೆಂಬರ್'
};

const monthNames = {
    '01': 'January', '02': 'February', '03': 'March', '04': 'April',
    '05': 'May', '06': 'June', '07': 'July', '08': 'August',
    '09': 'September', '10': 'October', '11': 'November', '12': 'December'
};

const shortMonthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

// ============================================================
// DOM REFERENCES
// ============================================================
const commoditySelect = document.getElementById('commodity');
const marketSelect = document.getElementById('market');
const monthSelect = document.getElementById('monthSelect');
const predictBtn = document.getElementById('predictBtn');
const resultBox = document.getElementById('resultBox');
const errorMsg = document.getElementById('errorMsg');
const refreshMonthlyBtn = document.getElementById('refreshMonthlyBtn');

// ============================================================
// HELPER FUNCTIONS
// ============================================================
function getMonthName(month) {
    if (currentLang === 'kn') {
        return monthNamesKn[month] || month;
    }
    return monthNames[month] || month;
}

function getBarColor(price, avgPrice) {
    if (price > avgPrice * 1.1) return 'rgba(44,122,90,0.85)';
    if (price < avgPrice * 0.9) return 'rgba(217,83,79,0.85)';
    return 'rgba(185,130,42,0.85)';
}

function formatDateForChart(dateStr) {
    try {
        var parts = dateStr.split('-');
        var year = parts[0];
        var month = parseInt(parts[1]) - 1;
        var day = parseInt(parts[2]);
        return shortMonthNames[month] + ' ' + day + ', ' + year;
    } catch (e) {
        return dateStr;
    }
}

// ============================================================
// TRANSLATE RECOMMENDATION REASON
// ============================================================
function translateRecommendation(reason, data) {
    var t = translations[currentLang];
    if (!reason) return '';
    
    if (reason.includes('Above average for this season')) return t.seasonalAbove;
    if (reason.includes('Below average for this season')) return t.seasonalBelow;
    if (reason.includes('Prices are at seasonal average')) return t.seasonalAverage;
    
    var monthlyMatch = reason.match(/Based on monthly average of ₹([\d,]+\.?\d*) from (\d+) records in (\d+) years/);
    if (monthlyMatch) {
        var price = monthlyMatch[1];
        var count = monthlyMatch[2];
        var years = monthlyMatch[3];
        return t.basedOnMonthlyAvg.replace('{price}', price).replace('{count}', count).replace('{years}', years);
    }
    
    if (reason.includes('Price is near its yearly high and expected to rise')) {
        return t.recPriceHigh + ' ' + reason.replace(/Price is near its yearly high and expected to rise[^.]*\./, '').trim();
    }
    if (reason.includes('Price is at its yearly high')) return t.recPriceHighMax;
    if (reason.includes('Price is near yearly low and expected to rise')) return t.recPriceLow;
    if (reason.includes('Price expected to rise significantly')) return t.recRiseSignificant;
    if (reason.includes('Price expected to rise by')) return t.recRiseModerate;
    if (reason.includes('Price expected to drop significantly') || reason.includes('Price expected to drop by')) return t.recDropSignificant;
    if (reason.includes('Price expected to decrease slightly')) return t.recDropModerate;
    if (reason.includes('Market is volatile') && reason.includes('swing')) return t.recVolatile;
    if (reason.includes('Market is moderately volatile')) return t.recModerateVolatile;
    if (reason.includes('stable but near yearly high')) return t.recStableHigh;
    if (reason.includes('stable but near yearly low')) return t.recStableLow;
    if (reason.includes('Prices are stable')) return t.recStable;
    if (reason.includes('reasonable choice')) return t.recReasonable;
    if (reason.includes('Insufficient data')) return t.recInsufficient;
    
    return reason;
}

// ============================================================
// UPDATE MODEL INSIGHTS (Dashboard summary)
// ============================================================
function updateModelInsights(data) {
    var t = translations[currentLang];
    
    if (!data || !data.model_predictions) {
        document.getElementById('insightBestModelValue').textContent = '—';
        document.getElementById('insightLowestRMSEValue').textContent = '—';
        document.getElementById('insightLowestMAEValue').textContent = '—';
        document.getElementById('insightModelsWorkingValue').textContent = '—';
        return;
    }

    var modelKeys = ['linear_regression', 'random_forest', 'xgboost', 'lstm', 'arima'];
    var modelLabels = {
        'linear_regression': 'LR',
        'random_forest': 'RF',
        'xgboost': 'XGB',
        'lstm': 'LSTM',
        'arima': 'ARIMA'
    };
    
    var bestRMSE = Infinity;
    var bestMAE = Infinity;
    var bestModel = '';
    var modelsWorking = 0;

    modelKeys.forEach(function(key) {
        var price = data.model_predictions[key];
        var metrics = data.model_metrics ? data.model_metrics[key] : null;
        var isValid = price !== null && price !== undefined && !isNaN(price) && price > 0;
        
        if (isValid) modelsWorking++;
        
        if (metrics && metrics.rmse && metrics.rmse > 0 && metrics.rmse < bestRMSE) {
            bestRMSE = metrics.rmse;
            bestModel = modelLabels[key] || key;
        }
        if (metrics && metrics.mae && metrics.mae > 0 && metrics.mae < bestMAE) {
            bestMAE = metrics.mae;
        }
    });

    document.getElementById('insightBestModelValue').textContent = bestModel || '—';
    document.getElementById('insightLowestRMSEValue').textContent = bestRMSE !== Infinity ? '₹' + Number(bestRMSE).toFixed(0) : '—';
    document.getElementById('insightLowestMAEValue').textContent = bestMAE !== Infinity ? '₹' + Number(bestMAE).toFixed(0) : '—';
    document.getElementById('insightModelsWorkingValue').textContent = modelsWorking + ' of 5';
}

// ============================================================
// RENDER 5-MONTH FORECAST TABLE - 2 COLUMNS ONLY
// ============================================================
function renderForecastTable(forecastData) {
    var wrapper = document.getElementById('forecastTableWrapper');
    var tbody = document.getElementById('forecastTableBody');
    if (!wrapper || !tbody) return;

    if (!forecastData || !forecastData.months || !forecastData.months.length) {
        wrapper.style.display = 'none';
        return;
    }

    tbody.innerHTML = '';

    forecastData.months.forEach(function(row, idx) {
        var tr = document.createElement('tr');
        if (idx === 0) tr.className = 'current-month';

        var monthTd = document.createElement('td');
        monthTd.className = 'month-cell';
        var monthLabel = getMonthName(row.month) || row.month_name;
        monthTd.textContent = monthLabel + ' ' + row.year;
        tr.appendChild(monthTd);

        var priceTd = document.createElement('td');
        priceTd.className = 'price-cell';
        priceTd.textContent = row.predicted_price ? '₹' + Number(row.predicted_price).toFixed(2) : '—';
        tr.appendChild(priceTd);

        tbody.appendChild(tr);
    });

    wrapper.style.display = 'block';
}

// ============================================================
// SET LANGUAGE FUNCTION
// ============================================================
function setLanguage(lang) {
    currentLang = lang;
    
    var enBtn = document.getElementById('langEn');
    var knBtn = document.getElementById('langKn');
    if (enBtn) enBtn.className = lang === 'en' ? 'active' : '';
    if (knBtn) knBtn.className = lang === 'kn' ? 'active' : '';
    
    var t = translations[lang];
    if (!t) return;
    
    var elements = {
        'logoSub': t.logoSub,
        'logoutBtn': t.logout,
        'compareNavLabel': t.compareNav,
        'adminNavLabel': t.adminNav,
        'pageTitle': t.pageTitle,
        'pageSubtitle': t.pageSubtitle,
        'selectionLabel': t.selectionLabel,
        'commodityLabel': t.commodityLabel,
        'marketLabel': t.marketLabel,
        'monthLabel': t.monthLabel,
        'predictLabel': t.predictLabel,
        'priceLabel': t.currentPrice,
        'predLabel': t.predictedPrice,
        'changeLabel': t.expectedChange,
        'confLabel': t.confidence,
        'insightBestModel': t.insightBestModel,
        'insightLowestRMSE': t.insightLowestRMSE,
        'insightLowestMAE': t.insightLowestMAE,
        'insightModelsWorking': t.insightModelsWorking,
        'viewModelsLabel': t.viewModelsLabel,
        'dataPointsLabel': t.dataPointsLabel,
        'seasonalAvgLabel': t.seasonalAvgLabel,
        'modelsWorkingLabel': t.modelsWorkingLabel,
        'recordCountLabel': t.recordsLabel,
        'chart365Label': t.chart365Label,
        'chartYearlyLabel': t.chartYearlyLabel,
        'refreshLabel': t.refreshLabel,
        'forecastTableTitle': t.forecastTableTitle,
        'forecastMonthHeader': t.forecastMonthHeader,
        'forecastPriceHeader': t.forecastPriceHeader
    };
    
    for (var id in elements) {
        if (elements.hasOwnProperty(id)) {
            var el = document.getElementById(id);
            if (el) {
                if (id === 'pageTitle') {
                    el.innerHTML = elements[id];
                } else if (id === 'logoutBtn' || id === 'compareNavLabel' || id === 'adminNavLabel') {
                    el.textContent = elements[id];
                } else {
                    el.textContent = elements[id];
                }
            }
        }
    }
    
    if (!commoditySelect.value) {
        var marketEl = document.getElementById('market');
        if (marketEl) {
            marketEl.innerHTML = '<option value="">' + t.selectCommodity + '</option>';
        }
    }

    localStorage.setItem('smartDssLang', lang);
    
    if (monthSelect.value) {
        var monthBadge = document.getElementById('monthBadge');
        if (monthBadge) {
            monthBadge.textContent = getMonthName(monthSelect.value);
        }
    }
    
    if (resultBox.classList.contains('visible') && currentPredictionData) {
        updateDynamicContent(currentPredictionData);
        updateModelInsights(currentPredictionData);
    }

    if (currentForecastData) {
        renderForecastTable(currentForecastData);
    }
}

// ============================================================
// UPDATE DYNAMIC CONTENT
// ============================================================
function updateDynamicContent(data) {
    var t = translations[currentLang];
    if (!data) return;
    
    var priceLabel = document.getElementById('priceLabel');
    if (priceLabel) {
        if (data.is_monthly) {
            priceLabel.textContent = t.monthlyAvgPrice;
        } else {
            priceLabel.textContent = t.currentPrice;
        }
    }
    
    var badge = document.getElementById('recommendationBadge');
    if (badge) {
        var rec = (data.recommendation || '').toLowerCase();
        if (rec === 'sell') badge.textContent = t.sell;
        else if (rec === 'store') badge.textContent = t.store;
        else if (rec === 'wait') badge.textContent = t.wait;
        else badge.textContent = data.recommendation || '—';
    }
    
    var resultDate = document.getElementById('resultDate');
    if (resultDate && data) {
        if (data.is_monthly) {
            var monthName = getMonthName(data.selected_month) || data.selected_month;
            resultDate.textContent = t.monthlyAvg + ' (' + monthName + ')';
        } else {
            resultDate.textContent = t.lastUpdated + ': ' + data.last_date;
        }
    }
    
    var reasonBox = document.getElementById('reasonText');
    if (reasonBox && data.reason) {
        var translatedReason = translateRecommendation(data.reason, data);
        var finalReason = translatedReason;
        if (data.seasonal_insight) {
            var seasonalTranslated = translateRecommendation(data.seasonal_insight, data);
            finalReason = translatedReason + ' <span class="seasonal-tip">' + seasonalTranslated + '</span>';
        }
        reasonBox.innerHTML = finalReason;
    }
}

// ============================================================
// LOAD MARKETS WHEN COMMODITY CHANGES
// ============================================================
commoditySelect.addEventListener('change', function() {
    var commodity = this.value;
    var t = translations[currentLang];
    
    marketSelect.disabled = true;
    marketSelect.innerHTML = '<option value="">' + t.loadingMarkets + '</option>';
    predictBtn.disabled = true;
    resultBox.classList.remove('visible');
    errorMsg.classList.remove('visible');
    if (statusMsg) statusMsg.textContent = '';
    currentPredictionData = null;
    currentForecastData = null;
    var forecastWrapperReset = document.getElementById('forecastTableWrapper');
    if (forecastWrapperReset) forecastWrapperReset.style.display = 'none';

    if (!commodity) {
        marketSelect.innerHTML = '<option value="">' + t.selectCommodity + '</option>';
        return;
    }

    fetch('/api/markets/' + encodeURIComponent(commodity))
        .then(function(res) { return res.json(); })
        .then(function(data) {
            marketSelect.innerHTML = '<option value="">— Select —</option>';
            if (Array.isArray(data) && data.length) {
                data.forEach(function(m) {
                    var opt = document.createElement('option');
                    opt.value = m;
                    opt.textContent = m;
                    marketSelect.appendChild(opt);
                });
                marketSelect.disabled = false;
            } else {
                marketSelect.innerHTML = '<option value="">' + t.noMarkets + '</option>';
            }
        })
        .catch(function() {
            marketSelect.innerHTML = '<option value="">Error loading markets</option>';
        });
});

// ============================================================
// ENABLE PREDICT BUTTON
// ============================================================
function checkSelections() {
    predictBtn.disabled = !(commoditySelect.value && marketSelect.value && monthSelect.value);
}

marketSelect.addEventListener('change', checkSelections);
monthSelect.addEventListener('change', checkSelections);

// ============================================================
// MONTH CHANGE
// ============================================================
monthSelect.addEventListener('change', function() {
    var month = this.value;
    var monthName = getMonthName(month) || (currentLang === 'kn' ? 'ತಿಂಗಳು ಆಯ್ಕೆಮಾಡಿ' : 'Select Month');
    document.getElementById('monthBadge').textContent = monthName;
    
    if (resultBox.classList.contains('visible') && commoditySelect.value && marketSelect.value) {
        loadMonthlyOnly();
    }
    checkSelections();
});

// ============================================================
// LOAD MONTHLY DATA ONLY
// ============================================================
function loadMonthlyOnly() {
    var commodity = commoditySelect.value;
    var market = marketSelect.value;
    var month = monthSelect.value;
    var t = translations[currentLang];

    if (!commodity || !market || !month) return;

    var statsEl = document.getElementById('monthlyStats');
    statsEl.innerHTML = '⏳ ' + t.loadingYearlyData;
    statsEl.style.color = 'var(--text-muted)';

    var cacheBuster = new Date().getTime();
    fetch('/api/historical-price?commodity=' + encodeURIComponent(commodity) + 
          '&market=' + encodeURIComponent(market) + 
          '&month=' + encodeURIComponent(month) + 
          '&_=' + cacheBuster)
        .then(function(res) {
            if (!res.ok) {
                return res.json().then(function(data) {
                    throw new Error(data.error || 'Failed to fetch data');
                });
            }
            return res.json();
        })
        .then(function(monthlyData) {
            renderMonthlyChart(monthlyData, month);
        })
        .catch(function(err) {
            var statsEl = document.getElementById('monthlyStats');
            statsEl.innerHTML = '<i class="fa-solid fa-triangle-exclamation" style="margin-right:6px;"></i>' + err.message;
            statsEl.style.color = '#c0392b';
            renderMonthlyChart(null, month);
        });
}

// ============================================================
// FULL PREDICTION
// ============================================================
function loadFullPrediction() {
    var commodity = commoditySelect.value;
    var market = marketSelect.value;
    var month = monthSelect.value;
    var t = translations[currentLang];

    if (!commodity || !market || !month) return;

    predictBtn.disabled = true;
    predictBtn.innerHTML = '<span class="spinner"></span> ' + t.runningModels;
    resultBox.classList.remove('visible');
    errorMsg.classList.remove('visible');
    if (statusMsg) statusMsg.textContent = '';

    var cacheBuster = new Date().getTime();

    Promise.all([
        fetch('/api/predict?commodity=' + encodeURIComponent(commodity) + 
              '&market=' + encodeURIComponent(market) + 
              '&month=' + encodeURIComponent(month)).then(function(r) { 
                if (!r.ok) return r.json().then(function(d) { throw new Error(d.error || 'Prediction failed'); });
                return r.json(); 
              }),
        fetch('/api/historical-price?commodity=' + encodeURIComponent(commodity) + 
              '&market=' + encodeURIComponent(market) + 
              '&month=' + encodeURIComponent(month) + 
              '&_=' + cacheBuster).then(function(r) { 
                if (!r.ok) return r.json().then(function(d) { throw new Error(d.error || 'Monthly data failed'); });
                return r.json(); 
              }),
        fetch('/api/predict-months?commodity=' + encodeURIComponent(commodity) + 
              '&market=' + encodeURIComponent(market) + 
              '&month=' + encodeURIComponent(month)).then(function(r) { 
                if (!r.ok) return null;
                return r.json(); 
              }).catch(function() { return null; })
    ])
    .then(function(responses) {
        var data = responses[0];
        var monthlyData = responses[1];
        var forecastData = responses[2];
        
        currentPredictionData = data;
        
        displayPredictionResult(data);
        renderMonthlyChart(monthlyData, month);
        resultBox.classList.add('visible');
        updateDynamicContent(data);
        updateModelInsights(data);

        if (forecastData && forecastData.months) {
            currentForecastData = forecastData;
            renderForecastTable(forecastData);
        } else {
            currentForecastData = null;
            var forecastWrapper = document.getElementById('forecastTableWrapper');
            if (forecastWrapper) forecastWrapper.style.display = 'none';
        }
    })
    .catch(function(err) {
        errorMsg.innerHTML = '<i class="fa-solid fa-triangle-exclamation" style="margin-right:6px;"></i>' + err.message;
        errorMsg.classList.add('visible');
        resultBox.classList.remove('visible');
    })
    .finally(function() {
        predictBtn.disabled = false;
        predictBtn.innerHTML = '<i class="fas fa-rocket"></i> ' + t.predictLabel;
    });
}

// ============================================================
// DISPLAY PREDICTION RESULT
// ============================================================
function displayPredictionResult(data) {
    var t = translations[currentLang];
    
    document.getElementById('resultTitle').textContent = data.commodity + ' @ ' + data.market;
    
    var isMonthly = data.is_monthly || false;
    
    if (isMonthly) {
        var monthName = getMonthName(data.selected_month) || data.selected_month;
        document.getElementById('resultDate').textContent = t.monthlyAvg + ' (' + monthName + ')';
        document.getElementById('priceLabel').textContent = t.monthlyAvgPrice;
        
        if (data.monthly_stats && data.monthly_stats.count) {
            document.getElementById('recordCount').textContent = data.monthly_stats.count;
            document.getElementById('monthlyRecordInfo').style.display = 'inline';
        }
    } else {
        document.getElementById('resultDate').textContent = t.lastUpdated + ': ' + data.last_date;
        document.getElementById('priceLabel').textContent = t.currentPrice;
        document.getElementById('monthlyRecordInfo').style.display = 'none';
    }

    document.getElementById('lastPrice').textContent = data.last_price ? '₹' + Number(data.last_price).toFixed(2) : '—';
    
    var predictedPrice = data.predicted_price;
    if (predictedPrice && !isNaN(predictedPrice)) {
        document.getElementById('predictedPrice').textContent = '₹' + Number(predictedPrice).toFixed(2);
    } else {
        document.getElementById('predictedPrice').textContent = '—';
    }
    
    var change = data.change_percent;
    var changeEl = document.getElementById('changePercent');
    if (change !== undefined && change !== null && !isNaN(change)) {
        var sign = change > 0 ? '+' : '';
        changeEl.textContent = sign + Number(change).toFixed(1) + '%';
        changeEl.className = 'value';
        if (change > 0.5) changeEl.classList.add('green');
        else if (change < -0.5) changeEl.classList.add('red');
        else changeEl.classList.add('gold');
    } else {
        changeEl.textContent = '—';
    }
    
    document.getElementById('confidenceLevel').textContent = data.confidence || '—';

    document.getElementById('dataPoints').textContent = data.data_points || '—';
    document.getElementById('seasonalAvg').textContent = data.seasonal_comparison && data.seasonal_comparison.avg_seasonal ? 
        '₹' + Number(data.seasonal_comparison.avg_seasonal).toFixed(2) : '—';
    
    var totalModels = data.total_models || 5;
    document.getElementById('modelsWorking').textContent = data.models_working !== undefined ? 
        data.models_working + ' of ' + totalModels : '—';

    // ============================================================
    // 365-Day Chart
    // ============================================================
    var canvas = document.getElementById('priceChart');
    if (priceChart) {
        priceChart.destroy();
        priceChart = null;
    }

    if (data.history && data.history.prices && data.history.prices.length > 1) {
        var prices = data.history.prices;
        var labels = data.history.dates.map(function(d) { return formatDateForChart(d); });

        var predictionData = prices.slice(0, -1);
        if (predictedPrice && !isNaN(predictedPrice)) {
            predictionData.push(predictedPrice);
        } else {
            predictionData.push(prices[prices.length - 1]);
        }

        var datasets = [
            {
                label: 'Historical Price',
                data: prices,
                borderColor: '#2c7a5a',
                backgroundColor: 'rgba(44,122,90,0.06)',
                fill: true,
                tension: 0.3,
                pointRadius: 0.5,
                pointBackgroundColor: '#2c7a5a',
                borderWidth: 2
            },
            {
                label: 'Predicted Price',
                data: predictionData,
                borderColor: '#b9822a',
                backgroundColor: 'rgba(185,130,42,0.05)',
                borderDash: [6, 4],
                fill: false,
                tension: 0.3,
                pointRadius: function(context) {
                    return context.dataIndex === predictionData.length - 1 ? 6 : 0.5;
                },
                pointBackgroundColor: function(context) {
                    return context.dataIndex === predictionData.length - 1 ? '#b9822a' : '#b9822a';
                },
                pointBorderColor: '#b9822a',
                pointBorderWidth: 2
            }
        ];

        if (isMonthly && data.last_price) {
            datasets.push({
                label: 'Monthly Avg: ₹' + Number(data.last_price).toFixed(0),
                data: Array(labels.length).fill(data.last_price),
                borderColor: '#d9534f',
                borderDash: [2, 4],
                borderWidth: 1.5,
                pointRadius: 0,
                fill: false
            });
        }

        var ctx = canvas.getContext('2d');
        priceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: { 
                            boxWidth: 12, 
                            padding: 12, 
                            font: { size: 11, family: "'Inter', sans-serif", weight: '500' },
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(26,58,42,0.92)',
                        titleFont: { family: "'Inter', sans-serif", weight: '600' },
                        bodyFont: { family: "'Inter', sans-serif" },
                        cornerRadius: 8,
                        padding: 12,
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ₹' + Number(context.parsed.y).toFixed(2);
                            }
                        }
                    }
                },
                scales: {
                    x: { 
                        grid: { display: false },
                        ticks: { 
                            maxTicksLimit: 15,
                            font: { size: 9, family: "'Inter', sans-serif" },
                            maxRotation: 45,
                            minRotation: 45,
                            autoSkip: true,
                            color: '#6b6455'
                        }
                    },
                    y: { 
                        grid: { color: 'rgba(43,42,37,0.05)' },
                        ticks: { 
                            callback: function(value) { return '₹' + Number(value).toFixed(0); },
                            font: { size: 10, family: "'Inter', sans-serif" },
                            color: '#6b6455'
                        }
                    }
                }
            }
        });
    }
}

// ============================================================
// RENDER MONTHLY CHART - ALL YEARS (2015-2024)
// ============================================================
function renderMonthlyChart(monthlyData, month) {
    var canvas = document.getElementById('monthlyChart');
    var t = translations[currentLang];
    
    if (monthlyChartInstance) {
        monthlyChartInstance.destroy();
        monthlyChartInstance = null;
    }

    var monthName = getMonthName(month) || (currentLang === 'kn' ? 'ತಿಂಗಳು ಆಯ್ಕೆಮಾಡಿ' : 'Select Month');
    document.getElementById('monthBadge').textContent = monthName;

    if (!monthlyData || !monthlyData.data || monthlyData.data.length === 0) {
        var statsEl = document.getElementById('monthlyStats');
        statsEl.innerHTML = t.noHistoricalData;
        statsEl.style.color = 'var(--text-muted)';
        
        var ctx = canvas.getContext('2d');
        monthlyChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['No Data'],
                datasets: [{
                    label: 'Price',
                    data: [0],
                    backgroundColor: 'rgba(200,200,200,0.3)',
                    borderColor: '#ccc',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { display: false } },
                    y: { grid: { display: false }, ticks: { display: false } }
                }
            }
        });
        return;
    }

    var yearlyData = monthlyData.data.slice().sort(function(a, b) {
        return parseInt(a.year) - parseInt(b.year);
    });
    
    var years = yearlyData.map(function(d) { return d.year; });
    var prices = yearlyData.map(function(d) { return d.price; });
    
    var avgPrice = monthlyData.stats ? monthlyData.stats.avg : 0;
    var minPrice = monthlyData.stats ? monthlyData.stats.min : 0;
    var maxPrice = monthlyData.stats ? monthlyData.stats.max : 0;

    var barColors = prices.map(function(p) { return getBarColor(p, avgPrice); });

    var ctx = canvas.getContext('2d');
    monthlyChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: years,
            datasets: [
                {
                    label: 'Avg Price (₹)',
                    data: prices,
                    backgroundColor: barColors,
                    borderColor: barColors.map(function(c) { return c.replace('0.85', '1'); }),
                    borderWidth: 2,
                    borderRadius: 4,
                    barPercentage: 0.7
                },
                {
                    label: 'Overall Avg: ₹' + Number(avgPrice).toFixed(0),
                    data: Array(prices.length).fill(avgPrice),
                    borderColor: '#2c7a5a',
                    borderDash: [6, 4],
                    borderWidth: 2,
                    type: 'line',
                    pointRadius: 0,
                    fill: false,
                    tension: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: { 
                        boxWidth: 14, 
                        padding: 14, 
                        font: { size: 11, family: "'Inter', sans-serif", weight: '500' },
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(26,58,42,0.92)',
                    titleFont: { family: "'Inter', sans-serif", weight: '600' },
                    bodyFont: { family: "'Inter', sans-serif" },
                    cornerRadius: 8,
                    padding: 12,
                    callbacks: {
                        title: function(context) {
                            return context[0].label + ' (' + monthName + ')';
                        },
                        label: function(context) {
                            if (context.dataset.label.startsWith('Overall Avg')) {
                                return 'Overall Average: ₹' + Number(context.parsed.y).toFixed(2);
                            }
                            var yearData = yearlyData[context.dataIndex];
                            var label = 'Price: ₹' + Number(context.parsed.y).toFixed(2);
                            if (yearData && yearData.record_count) {
                                label += ' | ' + yearData.record_count + ' records';
                                if (yearData.min && yearData.max) {
                                    label += ' | Range: ₹' + yearData.min + ' - ₹' + yearData.max;
                                }
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { 
                        font: { size: 12, family: "'Inter', sans-serif", weight: '600' },
                        color: '#4a6a5a',
                        autoSkip: false,
                        maxRotation: 0
                    }
                },
                y: {
                    grid: { color: 'rgba(43,42,37,0.06)' },
                    ticks: {
                        callback: function(value) { return '₹' + Number(value).toFixed(0); },
                        font: { size: 10, family: "'Inter', sans-serif" },
                        color: '#6b6455'
                    }
                }
            }
        }
    });

    var statsEl = document.getElementById('monthlyStats');
    var trendIcon = '';
    if (prices.length >= 2) {
        var lastPrice = prices[prices.length - 1];
        var firstPrice = prices[0];
        if (lastPrice > firstPrice * 1.05) trendIcon = '<i class="fa-solid fa-arrow-trend-up" style="color:#10b981;margin-right:6px;"></i>';
        else if (lastPrice < firstPrice * 0.95) trendIcon = '<i class="fa-solid fa-arrow-trend-down" style="color:#ef4444;margin-right:6px;"></i>';
        else trendIcon = '<i class="fa-solid fa-arrow-right" style="color:#f59e0b;margin-right:6px;"></i>';
    }
    
    statsEl.innerHTML = trendIcon + '<i class="fa-solid fa-chart-line" style="color:var(--gold);margin:0 4px 0 2px;"></i>Avg: ₹' + Number(avgPrice).toFixed(2) + 
                       ' | <i class="fa-solid fa-arrow-up" style="color:#10b981;margin:0 4px 0 6px;"></i>High: ₹' + Number(maxPrice).toFixed(2) + 
                       ' | <i class="fa-solid fa-arrow-down" style="color:#ef4444;margin:0 4px 0 6px;"></i>Low: ₹' + Number(minPrice).toFixed(2) +
                       ' | <i class="fa-regular fa-calendar" style="color:var(--text-muted);margin:0 4px 0 6px;"></i>' + monthlyData.stats.count + ' records' +
                       ' | <i class="fa-regular fa-calendar-days" style="color:var(--text-muted);margin:0 4px 0 6px;"></i>' + yearlyData.length + ' years' +
                       ' | <i class="fa-solid fa-location-dot" style="color:var(--gold);margin:0 4px 0 6px;"></i>' + monthlyData.market;
    statsEl.style.color = 'var(--text-muted)';
    
    console.log('Monthly chart showing ALL YEARS:', years.join(', '));
}

// ============================================================
// REFRESH MONTHLY BUTTON
// ============================================================
refreshMonthlyBtn.addEventListener('click', function() {
    var t = translations[currentLang];
    
    if (resultBox.classList.contains('visible') && commoditySelect.value && marketSelect.value && monthSelect.value) {
        document.getElementById('monthlyStats').innerHTML = '<i class="fa-solid fa-arrows-rotate fa-spin" style="margin-right:6px;"></i>' + t.loadingYearlyData;
        loadMonthlyOnly();
    } else {
        var statsEl = document.getElementById('monthlyStats');
        statsEl.innerHTML = t.runPredictionFirst;
        statsEl.style.color = 'var(--text-muted)';
        if (monthlyChartInstance) {
            monthlyChartInstance.destroy();
            monthlyChartInstance = null;
        }
    }
});

// ============================================================
// PREDICT BUTTON EVENT
// ============================================================
predictBtn.addEventListener('click', loadFullPrediction);

// ============================================================
// INITIALIZE
// ============================================================
if (monthSelect.value) {
    var monthName = getMonthName(monthSelect.value) || (currentLang === 'kn' ? 'ತಿಂಗಳು ಆಯ್ಕೆಮಾಡಿ' : 'Select Month');
    document.getElementById('monthBadge').textContent = monthName;
}

// Auto-refresh when tab becomes visible
document.addEventListener('visibilitychange', function() {
    if (!document.hidden && resultBox.classList.contains('visible') && 
        commoditySelect.value && marketSelect.value && monthSelect.value) {
        loadMonthlyOnly();
    }
});

// Apply saved language preference (persists across pages)
var savedLang = localStorage.getItem('smartDssLang');
if (savedLang && savedLang !== currentLang) {
    setLanguage(savedLang);
}

console.log('KrishiSense Price DSS Dashboard loaded successfully!');
console.log('X-axis now shows full dates with year (e.g., "Feb 25, 2025")');
console.log('Yearly comparison chart shows ALL 10 YEARS (2015-2024)');
console.log('Model insights show summary of model performance');
console.log('Kannada language support enabled with recommendation translation');
console.log('Click "Compare" to view full model comparison');