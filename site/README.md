# 🌐 puffco-ble Netlify Static Site Folder

This directory is completely self-contained and ready for **instant drag-and-drop deployment on Netlify**. Zero build tools or npm dependencies are required.

---

## 🚀 How to Deploy on Netlify

### Option 1: Drag & Drop (Fastest - 30 Seconds)
1. Go to **[app.netlify.com/drop](https://app.netlify.com/drop)** (log in or sign up).
2. Drag and drop this entire `site/` folder directly into the browser drop zone.
3. Netlify will generate a live URL (e.g. `https://peaceful-puffco-12345.netlify.app`) immediately.
4. Go to **Site Configuration > Change site name** or add your custom domain.

### Option 2: Continuous Git Deployment
1. Link your GitHub repository `SoyMilkIsOk/puffco-ble` in Netlify.
2. In build settings:
   - **Base directory:** *(leave blank)*
   - **Build command:** *(leave blank)*
   - **Publish directory:** `site`
3. Every `git push` to `main` will automatically deploy changes.

---

## ⚙️ Customization Checklist

### 1. Google Analytics 4 (GA4) Tracking
- Open [`assets/js/analytics.js`](assets/js/analytics.js).
- Replace `'G-XXXXXXXXXX'` with your actual GA4 Measurement ID:
  ```javascript
  const GA_MEASUREMENT_ID = 'G-XXXXXXXXXX';
  ```
- The built-in GDPR/CCPA cookie consent banner will automatically manage visitor consent and load the tracker when permitted.

### 2. Buy Me a Coffee Username
- In [`index.html`](index.html) and [`docs.html`](docs.html), search for `buymeacoffee.com/soymilk` and replace `soymilk` with your username.

### 3. Custom Domain
- In Netlify, go to **Domain management > Add custom domain** (e.g., `puffco.dev` or `puffco-ble.com`).
- Netlify provisions automatic free SSL/TLS certificates via Let's Encrypt.
