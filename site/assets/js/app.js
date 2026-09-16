/**
 * puffco-ble Landing Page & Simulator Logic (app.js)
 * Interactive CLI Emulator • Real-time Peak Pro Telemetry Simulator • Copy Handlers
 */

document.addEventListener('DOMContentLoaded', () => {
  initCopyButtons();
  initMobileMenu();
  initTerminalEmulator();
  initDeviceSimulator();
  initDocsSearch();
});

/* ==========================================================================
   1. COPY TO CLIPBOARD HANDLERS
   ========================================================================== */
function initCopyButtons() {
  const copyButtons = document.querySelectorAll('[data-copy]');
  copyButtons.forEach((btn) => {
    btn.addEventListener('click', async () => {
      const text = btn.getAttribute('data-copy');
      if (!text) return;

      try {
        await navigator.clipboard.writeText(text);
        const originalHTML = btn.innerHTML;
        btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#00ff9d" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg> Copied!`;
        btn.style.borderColor = '#00ff9d';

        if (window.trackCustomEvent) {
          window.trackCustomEvent('copy_code_snippet', { snippet: text.substring(0, 30) });
        }

        setTimeout(() => {
          btn.innerHTML = originalHTML;
          btn.style.borderColor = '';
        }, 2000);
      } catch (err) {
        console.error('Failed to copy: ', err);
      }
    });
  });
}

/* ==========================================================================
   2. MOBILE NAV TOGGLE
   ========================================================================== */
function initMobileMenu() {
  const toggleBtn = document.querySelector('.mobile-toggle');
  const navLinks = document.querySelector('.nav-links');

  if (toggleBtn && navLinks) {
    toggleBtn.addEventListener('click', () => {
      navLinks.classList.toggle('open');
      toggleBtn.setAttribute('aria-expanded', navLinks.classList.contains('open'));
    });
  }
}

/* ==========================================================================
   3. INTERACTIVE CLI TERMINAL EMULATOR
   ========================================================================== */
function initTerminalEmulator() {
  const screen = document.getElementById('terminal-screen');
  const input = document.getElementById('terminal-cli-input');
  const cmdButtons = document.querySelectorAll('.btn-terminal-cmd');
  if (!screen || !input) return;

  const commandHistory = [];
  let historyIndex = -1;

  // Append a line to the terminal
  function printLine(html) {
    const div = document.createElement('div');
    div.className = 'term-line';
    div.innerHTML = html;
    screen.appendChild(div);
    screen.scrollTop = screen.scrollHeight;
  }

  // Pre-canned simulated command outputs
  function executeCommand(rawCmd) {
    const cmd = rawCmd.trim();
    if (!cmd) return;

    commandHistory.push(cmd);
    historyIndex = commandHistory.length;

    // Echo input prompt
    printLine(`<span class="prompt-host">soymilk@puffco-station</span>:<span class="prompt-path">~/puffco-ble</span>$ <span class="term-white">${escapeHtml(cmd)}</span>`);

    if (window.trackCustomEvent) {
      window.trackCustomEvent('cli_command_executed', { command: cmd });
    }

    const lower = cmd.toLowerCase();

    if (lower === 'clear') {
      screen.innerHTML = '';
      return;
    }

    if (lower === 'help') {
      printLine(`<span class="term-dim">Available Commands:</span>`);
      printLine(`  <span class="term-cyan">puffco-ble scan</span>            - Scan for nearby Puffco BLE hardware`);
      printLine(`  <span class="term-cyan">puffco-ble monitor</span>         - Live stream chamber temperature & battery HUD`);
      printLine(`  <span class="term-cyan">puffco-ble info</span>            - Connect and dump serial, firmware, and lifetime dabs`);
      printLine(`  <span class="term-cyan">puffco-ble sesh start</span>      - Trigger heat session on active profile`);
      printLine(`  <span class="term-cyan">puffco-ble sesh boost</span>      - Add +15s duration and +10°F boost`);
      printLine(`  <span class="term-cyan">puffco-ble sesh stop</span>       - Abort active heating cycle`);
      printLine(`  <span class="term-cyan">clear</span>                       - Clear terminal screen`);
      return;
    }

    if (lower === 'puffco-ble scan') {
      printLine(`<span class="term-dim">[0.02s] Initializing Bleak Bluetooth Low Energy scanner...</span>`);
      printLine(`<span class="term-dim">[0.45s] Filtering manufacturer OUI and Lorax GATT UUIDs...</span>`);
      setTimeout(() => {
        printLine(`
<div class="term-hud-box">
  <table class="term-table">
    <thead>
      <tr><th>DEVICE NAME</th><th>MAC ADDRESS</th><th>RSSI</th><th>MODEL</th><th>CHAMBER</th></tr>
    </thead>
    <tbody>
      <tr><td class="term-cyan">Peak Pro V2 (Onyx)</td><td>C4:7C:8D:1F:B2:8E</td><td class="term-green">-54 dBm</td><td>Peak Pro 2.0</td><td class="term-amber">3DXL</td></tr>
      <tr><td class="term-pink">Proxy Vaporizer</td><td>D2:4B:9A:88:01:C2</td><td class="term-dim">-78 dBm</td><td>Proxy V1</td><td class="term-cyan">Standard</td></tr>
    </tbody>
  </table>
  <span class="term-green">✔ 2 Puffco BLE devices discovered in 1.4s.</span>
</div>`);
      }, 500);
      return;
    }

    if (lower === 'puffco-ble monitor') {
      printLine(`<span class="term-dim">Connecting to Peak Pro V2 (C4:7C:8D:1F:B2:8E)...</span>`);
      setTimeout(() => {
        printLine(`<span class="term-green">✔ Authenticated via Lorax VFS SHA-256 seed challenge.</span>`);
        printLine(`<span class="term-cyan">Streaming real-time telemetry at 60ms adaptive polling:</span>`);
        printLine(`
<div class="term-hud-box">
  <div style="font-family: monospace; font-size: 0.8rem; line-height: 1.5;">
    <div>┌─────────────────────────────────────────────────────────────────┐</div>
    <div>│ <span class="term-pink">💨 PUFFCO-BLE TELEMETRY HUD</span>                     [PID: 49102]     │</div>
    <div>├─────────────────────────────────────────────────────────────────┤</div>
    <div>│ Device: <span class="term-white">Peak Pro V2</span>            │ Chamber: <span class="term-amber">3DXL Chamber</span>           │</div>
    <div>│ Live Temp: <span class="term-green">510.4°F</span>             │ Target Temp: <span class="term-cyan">510.0°F</span>             │</div>
    <div>│ Battery: <span class="term-green">■■■■■■■■□□ 84%</span>       │ Charging: <span class="term-dim">No (Wireless Qi Ready)</span> │</div>
    <div>│ State: <span class="term-amber">HEAT_ACTIVE (Sesh)</span>       │ Time Remaining: <span class="term-white">28s</span>              │</div>
    <div>│ Total Lifetime Dabs: <span class="term-purple">1,420</span>      │ Polling Rate: <span class="term-cyan">16.4 FPS (61ms)</span>   │</div>
    <div>└─────────────────────────────────────────────────────────────────┘</div>
  </div>
</div>`);
      }, 600);
      return;
    }

    if (lower === 'puffco-ble info') {
      printLine(`<span class="term-dim">Querying Lorax VFS memory tree...</span>`);
      setTimeout(() => {
        printLine(`
<div class="term-hud-box">
  <div><span class="term-dim">Hardware Model:</span>      <span class="term-white">Puffco Peak Pro (Hardware Rev 4)</span></div>
  <div><span class="term-dim">Firmware Version:</span>    <span class="term-cyan">v5.4.1 (Lorax VFS Build 2024.11)</span></div>
  <div><span class="term-dim">Serial Number:</span>       <span class="term-pink">PK2-4919-C82-0194</span></div>
  <div><span class="term-dim">Lifetime Odometer:</span>   <span class="term-purple">1,420 dabs completed</span></div>
  <div><span class="term-dim">Stealth Mode:</span>        <span class="term-dim">Disabled (Mood Lights Active)</span></div>
  <div style="margin-top: 8px;"><span class="term-dim">Configured Heat Profiles:</span></div>
  <div>  [Slot 0] <span class="term-cyan">Daily Driver:</span> 490°F / 45s</div>
  <div>  [Slot 1] <span class="term-green">Flavor Savor:</span> 510°F / 40s (Active)</div>
  <div>  [Slot 2] <span class="term-amber">Heavy Cloud:</span>  535°F / 40s</div>
  <div>  [Slot 3] <span class="term-pink">3DXL Sesh:</span>    565°F / 35s</div>
</div>`);
      }, 500);
      return;
    }

    if (lower === 'puffco-ble sesh start') {
      printLine(`<span class="term-dim">Writing 0x07 to Lorax path /p/app/mc...</span>`);
      setTimeout(() => {
        printLine(`<span class="term-amber">⚡ Chamber preheat initiated! Target: 510°F</span>`);
        printLine(`<span class="term-green">✔ Ready to rip in 12 seconds. Enjoy the cloud!</span>`);
      }, 400);
      return;
    }

    if (lower === 'puffco-ble sesh boost') {
      printLine(`<span class="term-dim">Writing 0x09 to Lorax path /p/app/mc...</span>`);
      setTimeout(() => {
        printLine(`<span class="term-purple">🚀 Heat Boost applied: +15s duration, +10°F target temp!</span>`);
      }, 350);
      return;
    }

    if (lower === 'puffco-ble sesh stop') {
      printLine(`<span class="term-dim">Writing 0x08 to Lorax path /p/app/mc...</span>`);
      setTimeout(() => {
        printLine(`<span class="term-dim">🛑 Session cancelled. Heating element powered down.</span>`);
      }, 350);
      return;
    }

    // Default unknown
    printLine(`<span class="term-pink">Command not recognized: "${escapeHtml(cmd)}". Type <span class="term-cyan">help</span> or click toolbar buttons above.</span>`);
  }

  // Handle Enter key and history navigation
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const val = input.value;
      input.value = '';
      executeCommand(val);
    } else if (e.key === 'ArrowUp') {
      if (historyIndex > 0) {
        historyIndex--;
        input.value = commandHistory[historyIndex] || '';
      }
    } else if (e.key === 'ArrowDown') {
      if (historyIndex < commandHistory.length - 1) {
        historyIndex++;
        input.value = commandHistory[historyIndex] || '';
      } else {
        historyIndex = commandHistory.length;
        input.value = '';
      }
    }
  });

  // Quick command toolbar buttons
  cmdButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const cmd = btn.getAttribute('data-cmd');
      if (cmd) {
        executeCommand(cmd);
      }
    });
  });
}

/* ==========================================================================
   4. INTERACTIVE DEVICE TELEMETRY & HEAT SIMULATOR
   ========================================================================== */
function initDeviceSimulator() {
  const dial = document.getElementById('device-dial');
  const tempDisplay = document.getElementById('dial-temp-value');
  const stateDisplay = document.getElementById('dial-state-text');
  const targetDisplay = document.getElementById('dial-target-value');
  const batteryDisplay = document.getElementById('dial-battery-value');
  const dabsDisplay = document.getElementById('dial-dabs-value');
  const timeDisplay = document.getElementById('dial-time-value');

  const btnStart = document.getElementById('sim-btn-start');
  const btnBoost = document.getElementById('sim-btn-boost');
  const btnStop = document.getElementById('sim-btn-stop');
  const btnStealth = document.getElementById('sim-btn-stealth');
  const profilePills = document.querySelectorAll('.profile-pill');

  if (!dial || !tempDisplay) return;

  const profiles = [
    { name: 'Daily Driver', temp: 490, duration: 45 },
    { name: 'Flavor Savor', temp: 510, duration: 40 },
    { name: 'Heavy Cloud', temp: 535, duration: 40 },
    { name: '3DXL Sesh', temp: 565, duration: 35 },
  ];

  let currentProfileIndex = 1;
  let liveTemp = 74.0;
  let targetTemp = profiles[currentProfileIndex].temp;
  let remainingTime = 0;
  let operatingState = 'IDLE'; // IDLE, HEAT_PREHEAT, HEAT_ACTIVE, HEAT_FADE
  let stealthMode = false;
  let lifetimeDabs = 1420;
  let batteryPct = 84;
  let heatInterval = null;

  function updateUI() {
    tempDisplay.textContent = liveTemp.toFixed(1);
    targetDisplay.textContent = `${targetTemp}°F`;
    stateDisplay.textContent = operatingState;
    batteryDisplay.textContent = `${batteryPct}%`;
    dabsDisplay.textContent = lifetimeDabs.toLocaleString();
    timeDisplay.textContent = remainingTime > 0 ? `${remainingTime}s` : '--';

    dial.classList.remove('heating', 'active-sesh', 'stealth');
    if (stealthMode) {
      dial.classList.add('stealth');
    } else if (operatingState === 'HEAT_PREHEAT') {
      dial.classList.add('heating');
    } else if (operatingState === 'HEAT_ACTIVE' || operatingState === 'HEAT_FADE') {
      dial.classList.add('active-sesh');
    }

    if (btnBoost) {
      btnBoost.disabled = (operatingState !== 'HEAT_ACTIVE');
    }
  }

  function startSession() {
    if (operatingState !== 'IDLE') return;

    operatingState = 'HEAT_PREHEAT';
    remainingTime = profiles[currentProfileIndex].duration;
    updateUI();

    if (heatInterval) clearInterval(heatInterval);

    heatInterval = setInterval(() => {
      if (operatingState === 'HEAT_PREHEAT') {
        liveTemp += 18.5;
        if (liveTemp >= targetTemp) {
          liveTemp = targetTemp;
          operatingState = 'HEAT_ACTIVE';
        }
      } else if (operatingState === 'HEAT_ACTIVE') {
        remainingTime--;
        // Minor natural fluctuations around target
        liveTemp = targetTemp + (Math.sin(remainingTime) * 1.5);
        if (remainingTime <= 0) {
          operatingState = 'HEAT_FADE';
          lifetimeDabs++;
        }
      } else if (operatingState === 'HEAT_FADE') {
        liveTemp -= 22.0;
        if (liveTemp <= 75.0) {
          liveTemp = 74.0;
          operatingState = 'IDLE';
          clearInterval(heatInterval);
        }
      }
      updateUI();
    }, 400);

    if (window.trackCustomEvent) {
      window.trackCustomEvent('simulator_sesh_started', {
        profile: profiles[currentProfileIndex].name,
        target_temp: targetTemp
      });
    }
  }

  function boostSession() {
    if (operatingState !== 'HEAT_ACTIVE') return;
    targetTemp += 10;
    remainingTime += 15;
    updateUI();

    if (window.trackCustomEvent) {
      window.trackCustomEvent('simulator_boost_triggered', {
        new_target: targetTemp,
        remaining: remainingTime
      });
    }
  }

  function stopSession() {
    if (operatingState === 'IDLE') return;
    operatingState = 'HEAT_FADE';
    remainingTime = 0;
    updateUI();
  }

  function toggleStealth() {
    stealthMode = !stealthMode;
    if (btnStealth) {
      btnStealth.textContent = stealthMode ? 'Lights: OFF (Stealth)' : 'Lights: ON';
      btnStealth.classList.toggle('active', stealthMode);
    }
    updateUI();
  }

  // Profile selection
  profilePills.forEach((pill) => {
    pill.addEventListener('click', () => {
      const idx = parseInt(pill.getAttribute('data-slot'), 10);
      if (!isNaN(idx) && idx >= 0 && idx < profiles.length) {
        profilePills.forEach((p) => p.classList.remove('active'));
        pill.classList.add('active');
        currentProfileIndex = idx;
        targetTemp = profiles[idx].temp;
        if (operatingState === 'IDLE') {
          remainingTime = profiles[idx].duration;
        }
        updateUI();
      }
    });
  });

  if (btnStart) btnStart.addEventListener('click', startSession);
  if (btnBoost) btnBoost.addEventListener('click', boostSession);
  if (btnStop) btnStop.addEventListener('click', stopSession);
  if (btnStealth) btnStealth.addEventListener('click', toggleStealth);

  updateUI();
}

/* ==========================================================================
   5. DOCS IN-PAGE SEARCH
   ========================================================================== */
function initDocsSearch() {
  const searchInput = document.getElementById('docs-search-input');
  if (!searchInput) return;

  searchInput.addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase().trim();
    const sections = document.querySelectorAll('.docs-section');

    sections.forEach((sec) => {
      const text = sec.textContent.toLowerCase();
      if (!q || text.includes(q)) {
        sec.style.display = '';
      } else {
        sec.style.display = 'none';
      }
    });
  });
}

// Utility HTML escape
function escapeHtml(str) {
  return str.replace(/[&<>'"]/g, 
    tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag)
  );
}
