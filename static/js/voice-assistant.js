/**
 * KrishiSense - Krishi Mitra Voice Assistant & Chatbot
 * ----------------------------------------------------
 * Features:
 *  - Multilingual Voice & Chat (English & ಕನ್ನಡ)
 *  - Voice-driven tab & module navigation (Web Speech API)
 *  - Agricultural Chatbot (Crops, leaf diseases, mandi prices, pot telemetry)
 *  - User Activity capturing & timeline display
 *  - Kannada Speech Recognition (`kn-IN`) & Speech Synthesis
 */

(function () {
  if (window.__KRISHI_MITRA_LOADED__) return;
  window.__KRISHI_MITRA_LOADED__ = true;

  const STORAGE_MUTED_KEY = "krishisense_va_muted";
  const STORAGE_LANG_KEY = "krishisense_lang";

  let isListening = false;
  let recognition = null;
  let isMuted = localStorage.getItem(STORAGE_MUTED_KEY) === "true";
  let activeTab = "chat"; // 'chat' or 'activity'

  function getLang() {
    return localStorage.getItem(STORAGE_LANG_KEY) || "en";
  }

  function setLang(lang) {
    localStorage.setItem(STORAGE_LANG_KEY, lang);
    updateLanguageUI();
  }

  // Navigation Map (English and Kannada)
  const NAV_ROUTES = [
    {
      id: "dashboard",
      name: "Price DSS Dashboard",
      name_kn: "ಬೆಲೆ ಸಲಹಾ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
      url: "/dashboard",
      keywords: ["dashboard", "price dss", "mandi price", "price prediction", "price forecast", "market price", "prices", "price", "home",
                 "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್", "ಬೆಲೆ ಸಲಹೆ", "ಮಾರುಕಟ್ಟೆ ಬೆಲೆ", "ಬೆಲೆ ಮುನ್ಸೂಚನೆ", "ಮುಖಪುಟ", "ಹೋಮ್", "ಬೆಲೆ"]
    },
    {
      id: "crop",
      name: "Crop Advisor",
      name_kn: "ಬೆಳೆ ಸಲಹೆಗಾರ",
      url: "/crop",
      keywords: ["crop advisor", "crop", "recommend crop", "crop recommendation", "what to grow", "which crop", "seed", "npk",
                 "ಬೆಳೆ ಸಲಹೆಗಾರ", "ಬೆಳೆ ಶಿಫಾರಸು", "ಬೆಳೆ ಟ್ಯಾಬ್", "ಯಾವ ಬೆಳೆ", "ಬೆಳೆಗಳು", "ಬೆಳೆ"]
    },
    {
      id: "disease",
      name: "Leaf Disease Detection",
      name_kn: "ಎಲೆ ರೋಗ ಪತ್ತೆ",
      url: "/disease",
      keywords: ["disease", "leaf scan", "leaf disease", "plant disease", "scan leaf", "detect disease", "leaf infection", "blight",
                 "ಎಲೆ ಸ್ಕ್ಯಾನ್", "ಎಲೆ ರೋಗ", "ರೋಗ ಪತ್ತೆ", "ಗಿಡದ ರೋಗ", "ಎಲೆ ಟ್ಯಾಬ್", "ರೋಗ ಟ್ಯಾಬ್", "ಎಲೆ", "ರೋಗ"]
    },
    {
      id: "telemetry",
      name: "Sensor Node Telemetry",
      name_kn: "ಸೆನ್ಸಾರ್ ನೋಡ್ ಮಾನಿಟರಿಂಗ್",
      url: "/telemetry",
      keywords: ["sensor", "telemetry", "sensor node", "iot", "soil moisture", "pot", "hardware", "live reading",
                 "ಸೆನ್ಸಾರ್ ನೋಡ್", "ಸೆನ್ಸಾರ್ ಟ್ಯಾಬ್", "ಸೆನ್ಸಾರ್", "ತೇವಾಂಶ ನೋಡ್", "ಐಒಟಿ", "ಹಾರ್ಡ್‌ವೇರ್"]
    },
    {
      id: "insights",
      name: "Model Insights",
      name_kn: "ಮಾದರಿ ಒಳನೋಟಗಳು",
      url: "/insights",
      keywords: ["insights", "model insights", "feature importance", "shap", "trends",
                 "ಒಳನೋಟ", "ಒಳನೋಟಗಳು", "ಮಾಡೆಲ್ ಒಳನೋಟ"]
    },
    {
      id: "comparison",
      name: "Model Comparison",
      name_kn: "ಮಾದರಿ ಹೋಲಿಕೆ",
      url: "/model-comparison",
      keywords: ["comparison", "compare", "model comparison", "compare models", "algorithms", "accuracy table",
                 "ಮಾದರಿ ಹೋಲಿಕೆ", "ಹೋಲಿಕೆ", "ಮಾದರಿಗಳ ಹೋಲಿಕೆ"]
    },
    {
      id: "admin",
      name: "Admin Dashboard",
      name_kn: "ನಿರ್ವಾಹಕ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
      url: "/admin",
      keywords: ["admin", "admin panel", "administrator", "retrain",
                 "ನಿರ್ವಾಹಕ", "ನಿರ್ವಾಹಕ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್", "ಅಡ್ಮಿನ್"]
    },
    {
      id: "logout",
      name: "Logout",
      name_kn: "ಲಾಗ್ ಔಟ್",
      url: "/logout",
      keywords: ["logout", "log out", "sign out", "sign off", "exit",
                 "ಲಾಗ್ ಔಟ್", "ನಿರ್ಗಮಿಸಿ", "ಹೊರಬನ್ನಿ"]
    }
  ];

  function hasKannadaChars(str) {
    return /[\u0C80-\u0CFF]/.test(str);
  }

  // Speak aloud helper (Supports Kannada and English TTS)
  function speak(text, forceLang = null) {
    if (isMuted || !('speechSynthesis' in window)) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      const isKn = (forceLang === "kn") || (getLang() === "kn") || hasKannadaChars(text);

      utterance.lang = isKn ? "kn-IN" : "en-IN";
      utterance.rate = 0.95;
      utterance.pitch = 1.0;

      // Try selecting a Kannada voice if available
      const voices = window.speechSynthesis.getVoices();
      if (isKn && voices && voices.length > 0) {
        const knVoice = voices.find(v => v.lang && (v.lang.includes("kn") || v.lang.includes("kan")));
        if (knVoice) {
          utterance.voice = knVoice;
        }
      }

      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn("[KrishiMitra] Speech synthesis error:", e);
    }
  }

  // UI Injection
  function injectUI() {
    const isKn = getLang() === "kn";

    // 1. Floating Robot Launcher Button
    const fab = document.createElement("div");
    fab.className = "va-robot-launcher";
    fab.id = "vaFab";
    fab.setAttribute("title", isKn ? "ಕೃಷಿ ಮಿತ್ರ · ಧ್ವನಿ ಸಹಾಯಕ & ಚಾಟ್‌ಬಾಟ್" : "Krishi Mitra · Voice Assistant & Chatbot");
    fab.innerHTML = `
      <div class="va-robot-bubble" id="vaRobotBubble">
        <span class="va-bubble-text">${isKn ? 'ನಮಸ್ಕಾರ! ಕೃಷಿ ಮಿತ್ರ 👋' : "Hi! I'm Krishi Mitra 👋"}</span>
      </div>
      <div class="va-robot-figure">
        <img src="/static/img/krishi-bot-transparent.png?v=1" alt="Krishi Mitra Robot" class="va-robot-img" onerror="this.onerror=null; this.src='/static/img/krishi-bot.png';">
        <span class="va-robot-mic-badge" id="vaFabIcon"><i class="fa-solid fa-microphone"></i></span>
      </div>
      <div class="va-robot-shadow"></div>
    `;

    // 2. Chat Window
    const win = document.createElement("div");
    win.className = "va-window";
    win.id = "vaWindow";
    win.innerHTML = `
      <div class="va-header">
        <div class="va-header-left">
          <div class="va-avatar">
            <img src="/static/img/krishi-bot-transparent.png?v=1" alt="Krishi Mitra" onerror="this.onerror=null; this.src='/static/img/logo.png';">
            <span class="va-status-dot"></span>
          </div>
          <div>
            <div class="va-title">Krishi Mitra <span style="font-size:0.75rem; color:#f59e0b;">ಕೃಷಿ ಮಿತ್ರ</span></div>
            <div class="va-subtitle" id="vaHeaderSubtitle"><i class="fa-solid fa-wand-magic-sparkles"></i> ${isKn ? 'ಧ್ವನಿ ಸಹಾಯಕ & ಟ್ಯಾಬ್ ಬದಲಾವಣೆ' : 'Voice Assistant & Tab Switcher'}</div>
          </div>
        </div>
        <div class="va-header-actions">
          <!-- Language Toggle Pill -->
          <button type="button" class="va-icon-btn" id="vaLangToggleBtn" style="font-size:0.72rem; font-weight:800; width:auto; padding:0 8px;" title="Switch Language (English / ಕನ್ನಡ)">
            ${isKn ? 'ಕನ್ನಡ' : 'EN'}
          </button>
          <button type="button" class="va-icon-btn ${isMuted ? 'muted' : ''}" id="vaMuteBtn" title="Toggle Voice Audio">
            <i class="fa-solid ${isMuted ? 'fa-volume-xmark' : 'fa-volume-high'}"></i>
          </button>
          <button type="button" class="va-icon-btn" id="vaCloseBtn" title="Minimize">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
      </div>

      <div class="va-tabs">
        <button type="button" class="va-tab-btn active" id="vaTabChat">
          <i class="fa-solid fa-comments"></i> <span id="vaTabChatLabel">${isKn ? 'ಸಹಾಯಕ ಚಾಟ್' : 'Assistant Chat'}</span>
        </button>
        <button type="button" class="va-tab-btn" id="vaTabActivity">
          <i class="fa-solid fa-clock-rotate-left"></i> <span id="vaTabActivityLabel">${isKn ? 'ಚಟುವಟಿಕೆ ಲಾಗ್' : 'Activity Log'}</span>
        </button>
      </div>

      <!-- Quick Command Chips -->
      <div class="va-quick-chips" id="vaQuickChips">
        <!-- Rendered dynamically based on language -->
      </div>

      <!-- Messages Area -->
      <div class="va-messages" id="vaMessages">
        <div class="va-msg bot">
          <div style="display:flex; gap:8px; align-items:flex-start; width:100%;">
            <div style="width:30px; height:30px; flex-shrink:0; border-radius:50%; background:#ffffff; border:1.5px solid #f59e0b; overflow:hidden; display:flex; align-items:center; justify-content:center; box-shadow:0 2px 6px rgba(0,0,0,0.12);">
              <img src="/static/img/krishi-bot-transparent.png?v=1" alt="Bot" style="width:100%; height:100%; object-fit:contain;">
            </div>
            <div style="flex:1;">
              <div class="va-msg-bubble" id="vaWelcomeMessage">
                <!-- Rendered dynamically -->
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Activity Panel -->
      <div class="va-activity-panel" id="vaActivityPanel">
        <div style="font-size:0.75rem; color:#64748b; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
          <span id="vaActivityTitle"><strong>${isKn ? 'ದಾಖಲಾದ ನಿಮ್ಮ ಚಟುವಟಿಕೆಗಳು' : 'Your Captured Activities'}</strong></span>
          <button type="button" id="vaRefreshActivity" style="background:none; border:none; color:#0a3d24; cursor:pointer; font-size:0.75rem; font-weight:700;"><i class="fa-solid fa-rotate-right"></i> ${isKn ? 'ನವೀಕರಿಸಿ' : 'Refresh'}</button>
        </div>
        <div id="vaActivityList">
          <div style="text-align:center; padding:20px; color:#94a3b8; font-size:0.8rem;">Loading activities...</div>
        </div>
      </div>

      <!-- Voice Waveform Indicator -->
      <div class="va-voice-visualizer" id="vaVisualizer">
        <div class="va-wave-bar"></div>
        <div class="va-wave-bar"></div>
        <div class="va-wave-bar"></div>
        <div class="va-wave-bar"></div>
        <div class="va-wave-bar"></div>
        <span class="va-live-transcript" id="vaLiveTranscript">Listening...</span>
      </div>

      <!-- Input Field & Mic -->
      <div class="va-input-box">
        <button type="button" class="va-mic-btn" id="vaMicBtn" title="Hold or Click to Speak">
          <i class="fa-solid fa-microphone"></i>
        </button>
        <input type="text" class="va-text-input" id="vaTextInput" placeholder="Speak or type: 'Go to Crop Advisor'..." autocomplete="off">
        <button type="button" class="va-send-btn" id="vaSendBtn" title="Send Query">
          <i class="fa-solid fa-paper-plane"></i>
        </button>
      </div>
    `;

    // 3. Mobile Backdrop
    const backdrop = document.createElement("div");
    backdrop.className = "va-backdrop";
    backdrop.id = "vaBackdrop";

    document.body.appendChild(backdrop);
    document.body.appendChild(fab);
    document.body.appendChild(win);

    renderChipsAndWelcome();
  }

  function renderChipsAndWelcome() {
    const isKn = getLang() === "kn";
    const chipsContainer = document.getElementById("vaQuickChips");
    const welcomeEl = document.getElementById("vaWelcomeMessage");
    const textInput = document.getElementById("vaTextInput");
    const langBtn = document.getElementById("vaLangToggleBtn");
    const subtitle = document.getElementById("vaHeaderSubtitle");
    const tabChatLabel = document.getElementById("vaTabChatLabel");
    const tabActLabel = document.getElementById("vaTabActivityLabel");
    const actTitle = document.getElementById("vaActivityTitle");
    const fabBadge = document.querySelector(".va-fab-badge");

    if (langBtn) langBtn.textContent = isKn ? "ಕನ್ನಡ" : "EN";
    if (subtitle) subtitle.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> ${isKn ? 'ಧ್ವನಿ ಸಹಾಯಕ & ಟ್ಯಾಬ್ ಬದಲಾವಣೆ' : 'Voice Assistant & Tab Switcher'}`;
    if (tabChatLabel) tabChatLabel.textContent = isKn ? 'ಸಹಾಯಕ ಚಾಟ್' : 'Assistant Chat';
    if (tabActLabel) tabActLabel.textContent = isKn ? 'ಚಟುವಟಿಕೆ ಲಾಗ್' : 'Activity Log';
    if (actTitle) actTitle.innerHTML = `<strong>${isKn ? 'ದಾಖಲಾದ ನಿಮ್ಮ ಚಟುವಟಿಕೆಗಳು' : 'Your Captured Activities'}</strong>`;

    const bubbleText = document.querySelector(".va-bubble-text");
    if (bubbleText) {
      bubbleText.textContent = isKn ? "ನಮಸ್ಕಾರ! ಕೃಷಿ ಮಿತ್ರ 👋" : "Hi! I'm Krishi Mitra 👋";
    }

    if (chipsContainer) {
      if (isKn) {
        chipsContainer.innerHTML = `
          <span class="va-chip" data-cmd="ಬೆಳೆ ಸಲಹೆಗಾರನಿಗೆ ಹೋಗಿ"><i class="fa-solid fa-seedling" style="color:#10b981;"></i> ಬೆಳೆ ಸಲಹೆಗಾರ</span>
          <span class="va-chip" data-cmd="ಎಲೆ ಸ್ಕ್ಯಾನ್ ತೆರೆಯಿರಿ"><i class="fa-solid fa-leaf" style="color:#059669;"></i> ಎಲೆ ಸ್ಕ್ಯಾನ್</span>
          <span class="va-chip" data-cmd="ಅಡಿಕೆ ಬೆಲೆ ಎಷ್ಟು?"><i class="fa-solid fa-chart-line" style="color:#f59e0b;"></i> ಮಂಡಿ ಬೆಲೆ</span>
          <span class="va-chip" data-cmd="ಸೆನ್ಸಾರ್ ನೋಡ್ ತೆರೆಯಿರಿ"><i class="fa-solid fa-microchip" style="color:#0284c7;"></i> ಸೆನ್ಸಾರ್ ನೋಡ್</span>
          <span class="va-chip" data-cmd="ಮಣ್ಣಿನ ತೇವಾಂಶ ಎಷ್ಟು?"><i class="fa-solid fa-droplet" style="color:#06b6d4;"></i> ಮಣ್ಣಿನ ತೇವಾಂಶ?</span>
        `;
      } else {
        chipsContainer.innerHTML = `
          <span class="va-chip" data-cmd="open crop advisor"><i class="fa-solid fa-seedling" style="color:#10b981;"></i> Crop Advisor</span>
          <span class="va-chip" data-cmd="open leaf scan"><i class="fa-solid fa-leaf" style="color:#059669;"></i> Leaf Scan</span>
          <span class="va-chip" data-cmd="open price dss"><i class="fa-solid fa-chart-line" style="color:#f59e0b;"></i> Price DSS</span>
          <span class="va-chip" data-cmd="open sensor node"><i class="fa-solid fa-microchip" style="color:#0284c7;"></i> Sensor Node</span>
          <span class="va-chip" data-cmd="what is the soil moisture?"><i class="fa-solid fa-droplet" style="color:#06b6d4;"></i> Soil Moisture?</span>
        `;
      }

      // Re-bind click events on chips
      chipsContainer.querySelectorAll(".va-chip").forEach(chip => {
        chip.addEventListener("click", () => {
          const cmd = chip.getAttribute("data-cmd");
          if (cmd) handleUserQuery(cmd);
        });
      });
    }

    if (welcomeEl) {
      if (isKn) {
        welcomeEl.innerHTML = `
          👋 <strong>ನಮಸ್ಕಾರ!</strong> ನಾನು <strong>ಕೃಷಿ ಮಿತ್ರ</strong>, ನಿಮ್ಮ KrishiSense ಧ್ವನಿ ಸಹಾಯಕ.<br><br>
          • 🎙️ <strong>ಧ್ವನಿ ಆಜ್ಞೆಗಳು:</strong> <em>"ಬೆಳೆ ಸಲಹೆಗಾರ"</em>, <em>"ಎಲೆ ಸ್ಕ್ಯಾನ್"</em>, ಅಥವಾ <em>"ಸೆನ್ಸಾರ್ ನೋಡ್"</em> ಎಂದು ಹೇಳಿ ಟ್ಯಾಬ್ ಬದಲಾಯಿಸಿ.<br>
          • 💬 <strong>ಕೃಷಿ ಪ್ರಶ್ನೆಗಳು:</strong> <em>"ಮಣ್ಣಿನ ತೇವಾಂಶ ಎಷ್ಟು?"</em>, <em>"ಅಡಿಕೆ ಬೆಲೆ ಎಷ್ಟು?"</em>, ಅಥವಾ <em>"ಎಲೆ ಚುಕ್ಕೆ ರೋಗಕ್ಕೆ ಮದ್ದು ಏನು?"</em> ಎಂದು ಕೇಳಿ.
          <div class="va-msg-time">Just now</div>
        `;
      } else {
        welcomeEl.innerHTML = `
          👋 <strong>Namaste!</strong> I am <strong>Krishi Mitra</strong>, your KrishiSense voice assistant.<br><br>
          • 🎙️ <strong>Speak commands:</strong> <em>"Go to Crop Advisor"</em>, <em>"Open Leaf Scan"</em>, or <em>"Sensor Node"</em> to switch tabs.<br>
          • 💬 <strong>Ask farming questions:</strong> <em>"What is the current soil moisture?"</em>, <em>"Arecanut price trends"</em>, or <em>"How to treat leaf blight?"</em>.
          <div class="va-msg-time">Just now</div>
        `;
      }
    }

    if (textInput) {
      textInput.placeholder = isKn
        ? "ಮಾತನಾಡಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ: 'ಬೆಳೆ ಸಲಹೆಗಾರನಿಗೆ ಹೋಗಿ'..."
        : "Speak or type: 'Go to Crop Advisor'...";
    }
  }

  function updateLanguageUI() {
    renderChipsAndWelcome();
  }

  // Append a chat message to the UI
  function appendMessage(sender, htmlText, navTarget = null) {
    const container = document.getElementById("vaMessages");
    if (!container) return;

    const isKn = getLang() === "kn" || hasKannadaChars(htmlText);
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const msgDiv = document.createElement("div");
    msgDiv.className = `va-msg ${sender}`;

    let navHtml = "";
    if (navTarget) {
      const targetLabel = isKn ? (navTarget.name_kn || navTarget.name) : navTarget.name;
      navHtml = `
        <div class="va-nav-badge">
          <i class="fa-solid fa-arrow-up-right-from-square"></i> ${isKn ? `${targetLabel} ಪುಟಕ್ಕೆ ಬದಲಾಯಿಸಲಾಗಿದೆ` : `Switched to ${targetLabel}`}
        </div>
      `;
    }

    const formatted = htmlText
      .replace(/\n/g, "<br>")
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    if (sender === "bot") {
      msgDiv.innerHTML = `
        <div style="display:flex; gap:8px; align-items:flex-start;">
          <div style="width:30px; height:30px; flex-shrink:0; border-radius:50%; background:#ffffff; border:1.5px solid #f59e0b; overflow:hidden; display:flex; align-items:center; justify-content:center; box-shadow:0 2px 6px rgba(0,0,0,0.12);">
            <img src="/static/img/krishi-bot-transparent.png?v=1" alt="Bot" style="width:100%; height:100%; object-fit:contain;">
          </div>
          <div style="flex:1;">
            <div class="va-msg-bubble">
              ${formatted}
              ${navHtml}
            </div>
            <div class="va-msg-time">${timeStr}</div>
          </div>
        </div>
      `;
    } else {
      msgDiv.innerHTML = `
        <div class="va-msg-bubble">
          ${formatted}
          ${navHtml}
          <div class="va-msg-time">${timeStr}</div>
        </div>
      `;
    }

    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
  }

  // Check client-side direct navigation matches for ultra-fast switching
  function matchLocalNavigation(rawText) {
    const clean = rawText.toLowerCase().trim();
    for (const r of NAV_ROUTES) {
      for (const kw of r.keywords) {
        if (clean.includes(kw)) {
          return r;
        }
      }
    }
    return null;
  }

  // Execute tab navigation
  function executeNavigation(target) {
    const lang = getLang();
    const isKn = lang === "kn" || hasKannadaChars(target.name_kn || "");
    const name = isKn ? target.name_kn : target.name;
    const announce = isKn ? `${name} ಪುಟವನ್ನು ತೆರೆಯಲಾಗುತ್ತಿದೆ.` : `Navigating to ${name}.`;

    speak(announce, isKn ? "kn" : "en");
    appendMessage("bot", isKn ? `🚀 <strong>${name} ಪುಟಕ್ಕೆ ಕರೆದೊಯ್ಯಲಾಗುತ್ತಿದೆ</strong>...` : `🚀 <strong>Navigating to ${name}</strong>...`, target);

    // Record the activity to backend
    fetch("/api/assistant/activity", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action_type: "tab_navigation",
        description: isKn ? `${name} ಟ್ಯಾಬ್‌ಗೆ ಧ್ವನಿ ಮೂಲಕ ಬದಲಾವಣೆ` : `Voice navigation to ${target.name}`,
        details: `Destination: ${target.url}`,
        page: window.location.pathname
      })
    }).catch(() => {});

    // Redirect after brief visual / audio acknowledgment
    setTimeout(() => {
      window.location.href = target.url;
    }, 800);
  }

  // Send message to assistant chatbot backend
  function handleUserQuery(query) {
    const clean = query.trim();
    if (!clean) return;

    appendMessage("user", clean);

    const isKnInput = hasKannadaChars(clean) || (getLang() === "kn");

    // 1. Direct local navigation check for instantaneous tab switching
    const isQuestion = /ಎಷ್ಟು|ಹೇಗೆ|ಏನು|ಯಾವ|what|how|why|when|\?/i.test(clean);
    const localMatch = matchLocalNavigation(clean);
    const hasNavIntent = /go to|open|switch to|show|take me to|navigate|ತೆರೆಯಿರಿ|ಹೋಗಿ|ಬದಲಾಯಿಸಿ|ತೋರಿಸಿ|ಓಪನ್/i.test(clean) ||
                         ["crop", "disease", "telemetry", "dashboard", "logout", "insights", "comparison", "admin", "ಬೆಳೆ", "ಎಲೆ", "ಸೆನ್ಸಾರ್"].includes(clean.toLowerCase());

    if (localMatch && !isQuestion && (hasNavIntent || clean.split(" ").length <= 3)) {
      executeNavigation(localMatch);
      return;
    }

    // 2. Send to backend AI / Knowledge Assistant
    fetch("/api/assistant/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: clean,
        current_page: window.location.pathname,
        lang: isKnInput ? "kn" : "en"
      })
    })
      .then(res => res.json())
      .then(data => {
        if (data.action === "navigate" && data.target_url) {
          const target = NAV_ROUTES.find(r => r.url === data.target_url) || {
            name: data.target_name || "New Tab",
            name_kn: data.target_name || "ಹೊಸ ಟ್ಯಾಬ್",
            url: data.target_url
          };
          executeNavigation(target);
        } else {
          appendMessage("bot", data.reply || (isKnInput ? "ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಪ್ರಕ್ರಿಯೆಗೊಳಿಸಲಾಗುತ್ತಿದೆ..." : "I am processing your query."));
          if (data.speech) {
            speak(data.speech, data.lang || (isKnInput ? "kn" : "en"));
          }
        }
      })
      .catch(err => {
        console.error("[KrishiMitra] Chat error:", err);
        appendMessage("bot", isKnInput ? "⚠️ ಸರ್ವರ್ ಸಂಪರ್ಕ ಸಾಧಿಸಲು ಸಾಧ್ಯವಾಗುತ್ತಿಲ್ಲ." : "⚠️ Could not reach the assistant server. Please check connection.");
      });
  }

  // Load User Activities Timeline
  function loadActivities() {
    const listEl = document.getElementById("vaActivityList");
    if (!listEl) return;
    const isKn = getLang() === "kn";
    listEl.innerHTML = `<div style="text-align:center; padding:16px; color:#94a3b8; font-size:0.8rem;"><i class="fa-solid fa-spinner fa-spin"></i> ${isKn ? 'ಲೋಡ್ ಆಗುತ್ತಿದೆ...' : 'Loading...'}</div>`;

    fetch("/api/assistant/activities")
      .then(r => r.json())
      .then(data => {
        if (!data.activities || data.activities.length === 0) {
          listEl.innerHTML = `<div style="text-align:center; padding:20px; color:#94a3b8; font-size:0.8rem;">${isKn ? 'ಈ ಸೆಷನ್‌ನಲ್ಲಿ ಇನ್ನೂ ಯಾವುದೇ ಚಟುವಟಿಕೆ ದಾಖಲಾಗಿಲ್ಲ.' : 'No activities logged yet in this session.'}</div>`;
          return;
        }

        let html = "";
        data.activities.forEach(item => {
          const typeClass = item.action_type || "page_view";
          let typeLabel = typeClass.replace(/_/g, " ");
          if (isKn) {
            const knTypes = {
              "tab_navigation": "ಟ್ಯಾಬ್ ಬದಲಾವಣೆ",
              "chat_query": "ಸಹಾಯಕ ಚಾಟ್",
              "page_view": "ಪುಟ ವೀಕ್ಷಣೆ",
              "login": "ಲಾಗಿನ್",
              "logout": "ನಿರ್ಗಮಿಸಿ",
              "retrain": "ಮರು-ತರಬೇತಿ",
              "prediction": "ಮುನ್ಸೂಚನೆ",
              "user_action": "ಬಳಕೆದಾರ ಕ್ರಿಯೆ"
            };
            typeLabel = knTypes[typeClass] || typeLabel;
          }
          html += `
            <div class="va-activity-item">
              <div class="va-activity-top">
                <span class="va-act-type ${typeClass}">${typeLabel}</span>
                <span class="va-activity-time">${item.created_at || ""}</span>
              </div>
              <div class="va-activity-desc">${item.description || ""}</div>
              ${item.details ? `<div class="va-activity-detail">${item.details}</div>` : ""}
            </div>
          `;
        });
        listEl.innerHTML = html;
      })
      .catch(e => {
        listEl.innerHTML = `<div style="color:#ef4444; font-size:0.8rem; text-align:center;">${isKn ? 'ಚಟುವಟಿಕೆಗಳನ್ನು ಪಡೆಯಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ.' : 'Failed to load activities.'}</div>`;
      });
  }

  // Setup Speech Recognition
  function setupSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn("[KrishiMitra] Web Speech API not supported in this browser.");
      return null;
    }

    const rec = new SpeechRecognition();
    rec.continuous = false;
    rec.interimResults = true;

    rec.onstart = function () {
      isListening = true;
      updateListeningUI(true);
    };

    rec.onresult = function (event) {
      let interim = "";
      let final = "";

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          final += event.results[i][0].transcript;
        } else {
          interim += event.results[i][0].transcript;
        }
      }

      const visualizerText = document.getElementById("vaLiveTranscript");
      if (visualizerText) {
        visualizerText.textContent = interim || final || (getLang() === "kn" ? "ಆಲಿಸಲಾಗುತ್ತಿದೆ..." : "Listening...");
      }

      if (final.trim()) {
        const input = document.getElementById("vaTextInput");
        if (input) input.value = final.trim();
        handleUserQuery(final.trim());
      }
    };

    rec.onerror = function (event) {
      console.warn("[KrishiMitra] Speech recognition error:", event.error);
      isListening = false;
      updateListeningUI(false);
      const visualizerText = document.getElementById("vaLiveTranscript");
      if (visualizerText) {
        visualizerText.textContent = `Mic error: ${event.error}`;
      }
    };

    rec.onend = function () {
      isListening = false;
      updateListeningUI(false);
    };

    return rec;
  }

  function toggleSpeech() {
    if (!recognition) {
      recognition = setupSpeechRecognition();
    }

    if (!recognition) {
      const isKn = getLang() === "kn";
      alert(isKn
        ? "ನಿಮ್ಮ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಧ್ವನಿ ಗುರುತಿಸುವಿಕೆ ಬೆಂಬಲಿತವಾಗಿಲ್ಲ. ದಯವಿಟ್ಟು Google Chrome ಅಥವಾ Microsoft Edge ಬಳಸಿ, ಅಥವಾ ಚಾಟ್ ಬಾಕ್ಸ್‌ನಲ್ಲಿ ಟೈಪ್ ಮಾಡಿ."
        : "Voice speech recognition is not supported in this browser. Please use Google Chrome, Edge, or type your message in the chat box.");
      return;
    }

    if (isListening) {
      recognition.stop();
    } else {
      recognition.lang = getLang() === "kn" ? "kn-IN" : "en-IN";
      try {
        recognition.start();
      } catch (e) {
        console.warn("Could not start recognition:", e);
      }
    }
  }

  function updateListeningUI(active) {
    const fab = document.getElementById("vaFab");
    const micBtn = document.getElementById("vaMicBtn");
    const visualizer = document.getElementById("vaVisualizer");
    const transcript = document.getElementById("vaLiveTranscript");
    const bubbleText = document.querySelector(".va-bubble-text");
    const isKn = getLang() === "kn";

    if (active) {
      if (fab) fab.classList.add("listening");
      if (micBtn) micBtn.classList.add("listening");
      if (visualizer) visualizer.classList.add("active");
      if (transcript) transcript.textContent = isKn ? "🎙️ ಆಲಿಸಲಾಗುತ್ತಿದೆ... ಮಾತನಾಡಿ" : "🎙️ Listening... Speak your command";
      if (bubbleText) bubbleText.textContent = isKn ? "🎙️ ನಾನು ಆಲಿಸುತ್ತಿದ್ದೇನೆ..." : "🎙️ Listening to you...";
    } else {
      if (fab) fab.classList.remove("listening");
      if (micBtn) micBtn.classList.remove("listening");
      if (visualizer) visualizer.classList.remove("active");
      if (bubbleText) bubbleText.textContent = isKn ? "ನಮಸ್ಕಾರ! ಕೃಷಿ ಮಿತ್ರ 👋" : "Hi! I'm Krishi Mitra 👋";
    }
  }

  // Bind Event Listeners
  function bindEvents() {
    const fab = document.getElementById("vaFab");
    const win = document.getElementById("vaWindow");
    const closeBtn = document.getElementById("vaCloseBtn");
    const micBtn = document.getElementById("vaMicBtn");
    const sendBtn = document.getElementById("vaSendBtn");
    const textInput = document.getElementById("vaTextInput");
    const muteBtn = document.getElementById("vaMuteBtn");
    const langToggleBtn = document.getElementById("vaLangToggleBtn");
    const tabChat = document.getElementById("vaTabChat");
    const tabActivity = document.getElementById("vaTabActivity");
    const refreshActivityBtn = document.getElementById("vaRefreshActivity");

    const backdrop = document.getElementById("vaBackdrop");

    const quickChips = document.getElementById("vaQuickChips");
    const inputBox = document.querySelector(".va-input-box");

    function openAssistant() {
      win.classList.add("open");
      fab.classList.add("va-launcher-hidden");
      if (backdrop && window.innerWidth <= 680) {
        backdrop.classList.add("open");
      }
      if (window.innerWidth <= 680) {
        fab.classList.add("va-hidden-mobile");
      }
      setTimeout(() => textInput.focus(), 150);
    }

    function closeAssistant() {
      win.classList.remove("open");
      fab.classList.remove("va-launcher-hidden");
      if (backdrop) {
        backdrop.classList.remove("open");
      }
      fab.classList.remove("va-hidden-mobile");
    }

    // Toggle assistant window
    fab.addEventListener("click", () => {
      const isOpen = win.classList.contains("open");
      if (isOpen) {
        closeAssistant();
      } else {
        openAssistant();
      }
    });

    closeBtn.addEventListener("click", closeAssistant);

    if (backdrop) {
      backdrop.addEventListener("click", closeAssistant);
    }

    // Touch swipe down on mobile header to minimize
    const header = win.querySelector(".va-header");
    let touchStartY = 0;
    if (header) {
      header.addEventListener("touchstart", (e) => {
        touchStartY = e.touches[0].clientY;
      }, { passive: true });

      header.addEventListener("touchmove", (e) => {
        const touchCurrentY = e.touches[0].clientY;
        if (touchCurrentY - touchStartY > 60) {
          closeAssistant();
        }
      }, { passive: true });
    }

    // Dismiss on outside tap on small screens
    document.addEventListener("click", (e) => {
      if (win.classList.contains("open") && window.innerWidth <= 680) {
        if (!win.contains(e.target) && !fab.contains(e.target) && (!backdrop || !backdrop.contains(e.target))) {
          closeAssistant();
        }
      }
    });

    // Language Toggle Button [EN | ಕನ್ನಡ]
    if (langToggleBtn) {
      langToggleBtn.addEventListener("click", () => {
        const nextLang = getLang() === "kn" ? "en" : "kn";
        setLang(nextLang);
        // Also trigger page-level toggle if available
        if (window.KrishiI18n && typeof window.KrishiI18n.setLang === "function") {
          window.KrishiI18n.setLang(nextLang);
        }
      });
    }

    // Mic click
    micBtn.addEventListener("click", () => {
      toggleSpeech();
    });

    // Send query
    sendBtn.addEventListener("click", () => {
      const q = textInput.value;
      textInput.value = "";
      handleUserQuery(q);
    });

    textInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const q = textInput.value;
        textInput.value = "";
        handleUserQuery(q);
      }
    });

    // Mute toggle
    muteBtn.addEventListener("click", () => {
      isMuted = !isMuted;
      localStorage.setItem(STORAGE_MUTED_KEY, isMuted ? "true" : "false");
      muteBtn.classList.toggle("muted", isMuted);
      muteBtn.innerHTML = `<i class="fa-solid ${isMuted ? 'fa-volume-xmark' : 'fa-volume-high'}"></i>`;
      if (isMuted && ('speechSynthesis' in window)) {
        window.speechSynthesis.cancel();
      }
    });

    // Tab switching inside assistant
    tabChat.addEventListener("click", () => {
      activeTab = "chat";
      tabChat.classList.add("active");
      tabActivity.classList.remove("active");
      document.getElementById("vaMessages").style.display = "flex";
      document.getElementById("vaActivityPanel").classList.remove("active");
      if (quickChips) quickChips.style.display = "flex";
      if (inputBox) inputBox.style.display = "flex";
    });

    tabActivity.addEventListener("click", () => {
      activeTab = "activity";
      tabActivity.classList.add("active");
      tabChat.classList.remove("active");
      document.getElementById("vaMessages").style.display = "none";
      document.getElementById("vaActivityPanel").classList.add("active");
      if (quickChips) quickChips.style.display = "none";
      if (inputBox) inputBox.style.display = "none";
      loadActivities();
    });

    if (refreshActivityBtn) {
      refreshActivityBtn.addEventListener("click", loadActivities);
    }
  }

  // Automatic Activity Tracking on page load
  function logCurrentPageView() {
    const path = window.location.pathname;
    const isKn = getLang() === "kn";
    let pageName = isKn ? "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್" : "Dashboard";
    if (path.includes("crop")) pageName = isKn ? "ಬೆಳೆ ಸಲಹೆಗಾರ" : "Crop Advisor";
    else if (path.includes("disease")) pageName = isKn ? "ಎಲೆ ರೋಗ ಸ್ಕ್ಯಾನ್" : "Leaf Disease Scan";
    else if (path.includes("telemetry")) pageName = isKn ? "ಸೆನ್ಸಾರ್ ನೋಡ್ ಮಾನಿಟರಿಂಗ್" : "Sensor Node Telemetry";
    else if (path.includes("insight")) pageName = isKn ? "ಮಾದರಿ ಒಳನೋಟಗಳು" : "Model Insights";
    else if (path.includes("compare")) pageName = isKn ? "ಮಾದರಿ ಹೋಲಿಕೆ" : "Model Comparison";
    else if (path.includes("admin")) pageName = isKn ? "ನಿರ್ವಾಹಕ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್" : "Admin Dashboard";

    fetch("/api/assistant/activity", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action_type: "page_view",
        description: isKn ? `${pageName} ಪುಟವನ್ನು ವೀಕ್ಷಿಸಲಾಗಿದೆ` : `Viewed ${pageName}`,
        details: `Path: ${path}`,
        page: path
      })
    }).catch(() => {});
  }

  function init() {
    injectUI();
    bindEvents();
    logCurrentPageView();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
