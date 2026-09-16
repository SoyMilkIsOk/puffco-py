/**
 * Google Analytics 4 (GA4) & Cookie Consent Management
 * puffco-ble Static Site Suite
 *
 * INSTRUCTIONS:
 * 1. Replace 'G-XXXXXXXXXX' below with your actual Google Analytics Measurement ID.
 * 2. When users click "Accept All", the tracker is initialized and persistent in localStorage.
 * 3. If consent is declined, tracking scripts are never loaded.
 */

const GA_MEASUREMENT_ID = 'G-XXXXXXXXXX'; // <-- PASTE YOUR GA4 MEASUREMENT ID HERE

(function () {
  'use strict';

  const STORAGE_KEY = 'puffco_cookie_consent';

  function initAnalytics() {
    if (GA_MEASUREMENT_ID === 'G-XXXXXXXXXX' || !GA_MEASUREMENT_ID) {
      console.info('[Analytics] Placeholder ID detected (G-XXXXXXXXXX). Set your Measurement ID in assets/js/analytics.js to enable live tracking.');
      return;
    }

    if (window.gaLoaded) return;
    window.gaLoaded = true;

    // Load Google Analytics script tag asynchronously
    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`;
    document.head.appendChild(script);

    window.dataLayer = window.dataLayer || [];
    function gtag() { window.dataLayer.push(arguments); }
    window.gtag = gtag;

    gtag('js', new Date());
    gtag('config', GA_MEASUREMENT_ID, {
      anonymize_ip: true,
      cookie_flags: 'SameSite=None;Secure'
    });

    console.info('[Analytics] Google Analytics 4 initialized successfully.');
  }

  // Public helper to track custom events (RTG tracking)
  window.trackCustomEvent = function (eventName, params = {}) {
    const consent = localStorage.getItem(STORAGE_KEY);
    if (consent === 'granted' && typeof window.gtag === 'function') {
      window.gtag('event', eventName, params);
      console.debug(`[Analytics Event] ${eventName}:`, params);
    }
  };

  // Cookie Consent Banner Setup
  function setupCookieConsent() {
    const banner = document.getElementById('cookie-banner');
    if (!banner) return;

    const consentStatus = localStorage.getItem(STORAGE_KEY);

    if (!consentStatus) {
      // Show banner after brief delay
      setTimeout(() => {
        banner.classList.add('show');
      }, 1000);
    } else if (consentStatus === 'granted') {
      initAnalytics();
    }

    // Accept Button
    const acceptBtn = document.getElementById('btn-cookie-accept');
    if (acceptBtn) {
      acceptBtn.addEventListener('click', () => {
        localStorage.setItem(STORAGE_KEY, 'granted');
        banner.classList.remove('show');
        initAnalytics();
        window.trackCustomEvent('cookie_consent_accepted');
      });
    }

    // Decline / Essential Button
    const declineBtn = document.getElementById('btn-cookie-decline');
    if (declineBtn) {
      declineBtn.addEventListener('click', () => {
        localStorage.setItem(STORAGE_KEY, 'denied');
        banner.classList.remove('show');
        console.info('[Analytics] User declined non-essential cookies.');
      });
    }

    // Reset / Re-open consent modal triggers
    const triggerButtons = document.querySelectorAll('.trigger-cookie-settings');
    triggerButtons.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        banner.classList.add('show');
      });
    });
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupCookieConsent);
  } else {
    setupCookieConsent();
  }
})();
