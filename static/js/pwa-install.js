/**
 * KrishiSense - PWA Installation & Service Worker Handler
 * Clean, mobile-responsive bottom install card & interactive visual modal guide
 */

(function () {
  let deferredPrompt = null;
  const STORAGE_LANG_KEY = "krishisense_lang";
  const STORAGE_DISMISS_KEY = "krishisense_pwa_dismissed";

  function getLang() {
    return localStorage.getItem(STORAGE_LANG_KEY) || "en";
  }

  // 1. Register Service Worker (where supported)
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js')
        .then((reg) => {
          console.log('[PWA] ServiceWorker registered with scope:', reg.scope);
        })
        .catch((err) => {
          console.warn('[PWA] ServiceWorker registration notice:', err);
        });
    });
  }

  // 2. Check if already running in standalone mode (already installed)
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;

  // 3. Capture beforeinstallprompt event (desktop Chrome, Edge, supported HTTPS)
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    window.__PWA_PROMPT__ = e;
    showInstallBanner();
  });

  window.addEventListener('appinstalled', () => {
    console.log('[PWA] KrishiSense app was installed successfully!');
    deferredPrompt = null;
    hideInstallBanner();
  });

  // 4. Inject Install Banner & Modal HTML
  function renderInstallUI() {
    if (document.getElementById('pwaInstallDock')) return;

    const isKn = getLang() === "kn";

    // Bottom Dock Banner
    const dock = document.createElement('div');
    dock.id = 'pwaInstallDock';
    dock.className = 'pwa-install-dock';
    dock.innerHTML = `
      <div class="pwa-dock-content">
        <img src="/static/img/icon-192.png" alt="KrishiSense" class="pwa-dock-icon">
        <div class="pwa-dock-info">
          <div class="pwa-dock-title" id="pwaDockTitle">${isKn ? 'ಕೃಷಿಸೆನ್ಸ್ ಮೊಬೈಲ್ ಆ್ಯಪ್' : 'KrishiSense App'}</div>
          <div class="pwa-dock-sub" id="pwaDockSub">${isKn ? 'ಆಫ್‌ಲೈನ್ ಬೆಂಬಲ · ಸುಲಭ ಬಳಕೆ' : 'Download for quick home-screen access'}</div>
        </div>
      </div>
      <div class="pwa-dock-actions">
        <button type="button" class="pwa-btn-install" id="pwaBtnInstall">
          <i class="fa-solid fa-download"></i> <span id="pwaBtnText">${isKn ? 'ಇನ್‌ಸ್ಟಾಲ್' : 'Install App'}</span>
        </button>
        <button type="button" class="pwa-btn-dismiss" id="pwaBtnDismiss" title="Dismiss">&times;</button>
      </div>
    `;
    document.body.appendChild(dock);

    // Click handler for banner install button
    document.getElementById('pwaBtnInstall').addEventListener('click', (ev) => {
      ev.stopPropagation();
      window.triggerPWAInstall();
    });

    // Dismiss handler
    document.getElementById('pwaBtnDismiss').addEventListener('click', (ev) => {
      ev.stopPropagation();
      hideInstallBanner();
      sessionStorage.setItem(STORAGE_DISMISS_KEY, 'true');
    });

    // Visual Modal Guide for Mobile Users (when browser requires 3-dots menu)
    const modal = document.createElement('div');
    modal.id = 'pwaGuideModal';
    modal.className = 'pwa-guide-modal';
    modal.innerHTML = `
      <div class="pwa-modal-backdrop" id="pwaModalBackdrop"></div>
      <div class="pwa-modal-card">
        <div class="pwa-guide-arrow">
          <i class="fa-solid fa-arrow-up-long"></i>
          <span>${isKn ? 'ಮೇಲಿನ 3 ಚುಕ್ಕೆಗಳನ್ನು (⋮) ಒತ್ತಿ' : 'Tap the 3 dots (⋮) above'}</span>
        </div>
        <div class="pwa-modal-header">
          <img src="/static/img/icon-192.png" alt="App Icon" class="pwa-modal-icon">
          <div>
            <h3 id="pwaModalTitle">${isKn ? 'KrishiSense ಆ್ಯಪ್ ಇನ್‌ಸ್ಟಾಲ್ ಮಾಡಿ' : 'Install KrishiSense App'}</h3>
            <p id="pwaModalSub">${isKn ? 'ನಿಮ್ಮ ಮೊಬೈಲ್ ಹೋಮ್ ಸ್ಕ್ರೀನ್‌ನಲ್ಲಿ ಸೇರಿಸಿ' : 'Add directly to your Android / iOS home screen'}</p>
          </div>
          <button type="button" class="pwa-modal-close" id="pwaModalClose">&times;</button>
        </div>
        <div class="pwa-steps-list" id="pwaStepsContainer">
          <!-- Populated dynamically based on platform -->
        </div>
        <button type="button" class="pwa-modal-ok-btn" id="pwaModalOkBtn">
          ${isKn ? 'ಅರ್ಥವಾಯಿತು · ಈಗಲೇ ಸೇರಿಸಿ' : 'Got It · Add to Home Screen'}
        </button>
      </div>
    `;
    document.body.appendChild(modal);

    document.getElementById('pwaModalClose').addEventListener('click', closeGuideModal);
    document.getElementById('pwaModalBackdrop').addEventListener('click', closeGuideModal);
    document.getElementById('pwaModalOkBtn').addEventListener('click', closeGuideModal);
  }

  function showInstallBanner() {
    if (isStandalone) return;
    if (sessionStorage.getItem(STORAGE_DISMISS_KEY) === 'true') return;
    renderInstallUI();
    const dock = document.getElementById('pwaInstallDock');
    if (dock) {
      // Adjust position if voice assistant robot FAB is present
      const hasRobot = !!document.getElementById('assistantToggleBtn') || !!document.querySelector('.voice-assistant-fab');
      if (hasRobot) {
        dock.classList.add('pwa-dock-above-robot');
      } else {
        dock.classList.remove('pwa-dock-above-robot');
      }
      dock.classList.add('visible');
    }
  }

  function hideInstallBanner() {
    const dock = document.getElementById('pwaInstallDock');
    if (dock) dock.classList.remove('visible');
  }

  function openGuideModal() {
    renderInstallUI();
    const isKn = getLang() === "kn";
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    const stepsContainer = document.getElementById('pwaStepsContainer');

    if (isIOS) {
      stepsContainer.innerHTML = `
        <div class="pwa-step-item">
          <div class="pwa-step-num">1</div>
          <div class="pwa-step-text">
            <strong>${isKn ? 'Share ಬಟನ್ ಒತ್ತಿ' : 'Tap the Share Button'}</strong>
            <span>${isKn ? 'Safari ಕೆಳಭಾಗದಲ್ಲಿರುವ ಶೇರ್ ಐಕಾನ್ (⎋) ಒತ್ತಿ.' : 'Tap the Share icon (⎋) at the bottom of Safari.'}</span>
          </div>
        </div>
        <div class="pwa-step-item">
          <div class="pwa-step-num">2</div>
          <div class="pwa-step-text">
            <strong>${isKn ? 'Add to Home Screen ಆಯ್ಕೆಮಾಡಿ' : 'Select "Add to Home Screen"'}</strong>
            <span>${isKn ? 'ಮೆನುವಿನಲ್ಲಿ ಕೆಳಗೆ ಸ್ಕ್ರಾಲ್ ಮಾಡಿ ⊞ Add to Home Screen ಒತ್ತಿ.' : 'Scroll down and tap ⊞ Add to Home Screen.'}</span>
          </div>
        </div>
        <div class="pwa-step-item">
          <div class="pwa-step-num">3</div>
          <div class="pwa-step-text">
            <strong>${isKn ? 'ಆ್ಯಪ್ ಆಗಿ ಬಳಸಿ' : 'Launch from Home Screen'}</strong>
            <span>${isKn ? 'KrishiSense ನಿಮ್ಮ ಮೊಬೈಲ್‌ನಲ್ಲಿ ಆ್ಯಪ್ ಆಗಿ ತೆರೆಯುತ್ತದೆ!' : 'KrishiSense will open full-screen like a native mobile app!'}</span>
          </div>
        </div>
      `;
    } else {
      // Android / Chrome / Edge
      stepsContainer.innerHTML = `
        <div class="pwa-step-item">
          <div class="pwa-step-num">1</div>
          <div class="pwa-step-text">
            <strong>${isKn ? 'ಬ್ರೌಸರ್ ಮೆನು (⋮) ಒತ್ತಿ' : 'Tap the Browser Menu (⋮)'}</strong>
            <span>${isKn ? 'ಪರದೆಯ ಮೇಲಿನ ಬಲ ಮೂಲೆಯಲ್ಲಿರುವ 3 ಚುಕ್ಕೆಗಳ ಮೆನು (⋮) ಒತ್ತಿ.' : 'Tap the 3 dots in the top-right corner of Chrome.'}</span>
          </div>
        </div>
        <div class="pwa-step-item">
          <div class="pwa-step-num">2</div>
          <div class="pwa-step-text">
            <strong>${isKn ? '"Add to Home screen" ಅಥವಾ "Install app" ಆಯ್ಕೆಮಾಡಿ' : 'Tap "Add to Home screen" or "Install app"'}</strong>
            <span>${isKn ? 'ಮೆನುವಿನಲ್ಲಿ ಕಾಣಿಸುವ "Add to Home screen" ಅಥವಾ "Install" ಒತ್ತಿ.' : 'Choose "Add to Home screen" or "Install app" from the menu.'}</span>
          </div>
        </div>
        <div class="pwa-step-item">
          <div class="pwa-step-num">3</div>
          <div class="pwa-step-text">
            <strong>${isKn ? '"Add" ಒತ್ತಿ - ಆ್ಯಪ್ ಸಿದ್ಧ!' : 'Tap "Add" — Done!'}</strong>
            <span>${isKn ? 'KrishiSense ಐಕಾನ್ ನಿಮ್ಮ ಫೋನ್ ಹೋಮ್ ಸ್ಕ್ರೀನ್‌ನಲ್ಲಿ ಆ್ಯಪ್ ಆಗಿ ಡೌನ್‌ಲೋಡ್ ಆಗುತ್ತದೆ.' : 'KrishiSense installs onto your mobile phone launcher with its app icon.'}</span>
          </div>
        </div>
      `;
    }

    const modal = document.getElementById('pwaGuideModal');
    if (modal) modal.classList.add('visible');
  }

  function closeGuideModal() {
    const modal = document.getElementById('pwaGuideModal');
    if (modal) modal.classList.remove('visible');
  }

  // Global trigger function (callable by button, voice assistant, etc.)
  window.triggerPWAInstall = function () {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      deferredPrompt.userChoice.then((choiceResult) => {
        if (choiceResult.outcome === 'accepted') {
          console.log('[PWA] User accepted the install prompt');
        }
        deferredPrompt = null;
        hideInstallBanner();
      });
      return;
    }

    // When running over LAN HTTP, Chrome requires selecting "Add to Home screen" from the menu
    openGuideModal();
  };

  // 5. Inject Clean Responsive Styles for Install Dock & Modal
  const style = document.createElement('style');
  style.id = 'pwa-install-styles';
  style.textContent = `
    /* Floating Bottom Dock */
    .pwa-install-dock {
      position: fixed;
      bottom: 16px;
      left: 16px;
      right: 16px;
      max-width: 440px;
      margin: 0 auto;
      z-index: 99990;
      background: rgba(6, 42, 24, 0.96);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 2px solid #f59e0b;
      border-radius: 20px;
      padding: 10px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      box-shadow: 0 14px 35px rgba(0, 0, 0, 0.35), 0 0 18px rgba(245, 158, 11, 0.25);
      transform: translateY(120%);
      opacity: 0;
      pointer-events: none;
      transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.3s ease;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .pwa-install-dock.visible {
      transform: translateY(0);
      opacity: 1;
      pointer-events: auto;
    }
    /* When Voice Assistant Robot is visible, sit neatly above it on mobile */
    @media (max-width: 768px) {
      .pwa-install-dock.pwa-dock-above-robot {
        bottom: 88px;
      }
    }
    .pwa-dock-content {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
    }
    .pwa-dock-icon {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      background: #ffffff;
      padding: 2px;
      box-shadow: 0 4px 10px rgba(0,0,0,0.2);
      flex-shrink: 0;
    }
    .pwa-dock-info {
      min-width: 0;
    }
    .pwa-dock-title {
      color: #ffffff;
      font-weight: 800;
      font-size: 0.88rem;
      line-height: 1.2;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .pwa-dock-sub {
      color: #cbd5e1;
      font-size: 0.72rem;
      margin-top: 2px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .pwa-dock-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }
    .pwa-btn-install {
      background: linear-gradient(135deg, #f59e0b, #d97706);
      color: #062a18;
      border: none;
      font-weight: 800;
      font-size: 0.78rem;
      padding: 8px 14px;
      border-radius: 20px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
      white-space: nowrap;
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .pwa-btn-install:hover {
      transform: scale(1.04);
      box-shadow: 0 6px 16px rgba(245, 158, 11, 0.55);
    }
    .pwa-btn-dismiss {
      background: transparent;
      border: none;
      color: #94a3b8;
      font-size: 1.3rem;
      line-height: 1;
      cursor: pointer;
      padding: 4px;
      transition: color 0.2s;
    }
    .pwa-btn-dismiss:hover {
      color: #ffffff;
    }

    /* Modal Guide Styles */
    .pwa-guide-modal {
      position: fixed;
      inset: 0;
      z-index: 100000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.25s ease;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .pwa-guide-modal.visible {
      opacity: 1;
      pointer-events: auto;
    }
    .pwa-modal-backdrop {
      position: absolute;
      inset: 0;
      background: rgba(10, 25, 18, 0.75);
      backdrop-filter: blur(6px);
      -webkit-backdrop-filter: blur(6px);
    }
    .pwa-modal-card {
      position: relative;
      background: #ffffff;
      border-radius: 22px;
      max-width: 420px;
      width: 100%;
      padding: 24px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);
      border: 3px solid #f59e0b;
      transform: translateY(20px) scale(0.96);
      transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .pwa-guide-modal.visible .pwa-modal-card {
      transform: translateY(0) scale(1);
    }
    .pwa-guide-arrow {
      position: absolute;
      top: -46px;
      right: 18px;
      color: #fbbf24;
      font-weight: 800;
      font-size: 0.85rem;
      display: flex;
      align-items: center;
      gap: 6px;
      background: rgba(6, 42, 24, 0.95);
      padding: 6px 12px;
      border-radius: 20px;
      border: 1.5px solid #fbbf24;
      box-shadow: 0 6px 16px rgba(0,0,0,0.3);
      animation: pwa-bounce-up 1.6s infinite;
    }
    @keyframes pwa-bounce-up {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-8px); }
    }
    .pwa-modal-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 18px;
    }
    .pwa-modal-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      border: 2px solid #f59e0b;
      padding: 2px;
      background: #fff;
    }
    .pwa-modal-header h3 {
      font-size: 1.05rem;
      font-weight: 800;
      color: #0a3d24;
      margin: 0;
      line-height: 1.25;
    }
    .pwa-modal-header p {
      font-size: 0.78rem;
      color: #64748b;
      margin: 3px 0 0;
    }
    .pwa-modal-close {
      margin-left: auto;
      background: none;
      border: none;
      font-size: 1.5rem;
      color: #94a3b8;
      cursor: pointer;
      line-height: 1;
      padding: 2px;
    }
    .pwa-modal-close:hover {
      color: #0f172a;
    }
    .pwa-steps-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-bottom: 20px;
    }
    .pwa-step-item {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      background: #f8fafc;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid #e2e8f0;
    }
    .pwa-step-num {
      width: 26px;
      height: 26px;
      border-radius: 50%;
      background: linear-gradient(135deg, #0a3d24, #15803d);
      color: #ffffff;
      font-weight: 800;
      font-size: 0.8rem;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      margin-top: 2px;
    }
    .pwa-step-text {
      font-size: 0.82rem;
      color: #1e293b;
      line-height: 1.4;
    }
    .pwa-step-text strong {
      display: block;
      color: #0a3d24;
      font-size: 0.88rem;
      margin-bottom: 2px;
    }
    .pwa-step-text span {
      color: #64748b;
      font-size: 0.78rem;
    }
    .pwa-modal-ok-btn {
      width: 100%;
      background: linear-gradient(135deg, #0a3d24, #15803d);
      color: #ffffff;
      border: none;
      padding: 12px;
      border-radius: 14px;
      font-weight: 700;
      font-size: 0.9rem;
      cursor: pointer;
      box-shadow: 0 4px 14px rgba(10, 61, 36, 0.25);
      transition: transform 0.15s ease;
    }
    .pwa-modal-ok-btn:hover {
      transform: translateY(-1px);
    }
  `;
  document.head.appendChild(style);

  // Automatically show the bottom install dock after 1.8 seconds on mobile/desktop if not in standalone
  setTimeout(() => {
    if (!isStandalone) {
      showInstallBanner();
    }
  }, 1800);
})();
