/**
 * puffco-ble Site Logic (app.js)
 * Copy handlers, mobile nav, docs sidebar auto-highlighting
 */

document.addEventListener('DOMContentLoaded', () => {
  initCopyButtons();
  initMobileMenu();
  initDocsSidebar();
});

/* ==========================================================================
   1. COPY TO CLIPBOARD
   ========================================================================== */
function initCopyButtons() {
  document.querySelectorAll('[data-copy]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const text = btn.getAttribute('data-copy');
      if (!text) return;

      try {
        await navigator.clipboard.writeText(text);
        const original = btn.innerHTML;
        const originalClass = btn.className;

        // Show feedback
        if (btn.classList.contains('btn-copy')) {
          // Hero install box copy button
          btn.classList.add('copied');
          btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
        } else {
          // Code block copy buttons
          btn.textContent = 'Copied!';
          btn.style.color = 'var(--green)';
        }

        if (window.trackCustomEvent) {
          window.trackCustomEvent('copy_snippet', { text: text.substring(0, 40) });
        }

        setTimeout(() => {
          btn.innerHTML = original;
          btn.className = originalClass;
          btn.style.color = '';
        }, 2000);
      } catch (err) {
        // Fallback: select text
        console.error('Copy failed:', err);
      }
    });
  });
}

/* ==========================================================================
   2. MOBILE NAV TOGGLE
   ========================================================================== */
function initMobileMenu() {
  const toggle = document.querySelector('.mobile-toggle');
  const nav = document.querySelector('.nav-links');

  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const isOpen = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', isOpen);
    });

    // Close menu when clicking a link
    nav.querySelectorAll('.nav-link').forEach((link) => {
      link.addEventListener('click', () => {
        nav.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      });
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
      if (!nav.contains(e.target) && !toggle.contains(e.target) && nav.classList.contains('open')) {
        nav.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }
}

/* ==========================================================================
   3. DOCS SIDEBAR — Auto-highlight on scroll + Mobile toggle
   ========================================================================== */
function initDocsSidebar() {
  const sidebar = document.getElementById('docs-sidebar');
  const sidebarToggle = document.getElementById('sidebar-toggle');
  const sidebarLinks = document.querySelectorAll('.sidebar-nav-link');

  if (!sidebar || sidebarLinks.length === 0) return;

  // -- Mobile sidebar drawer toggle --
  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', () => {
      const isOpen = sidebar.classList.toggle('open');
      sidebarToggle.classList.toggle('open', isOpen);
    });

    // Close sidebar when clicking a link (mobile)
    sidebarLinks.forEach((link) => {
      link.addEventListener('click', () => {
        if (window.innerWidth <= 900) {
          sidebar.classList.remove('open');
          sidebarToggle.classList.remove('open');
        }
      });
    });
  }

  // -- IntersectionObserver for auto-highlighting --
  const sections = document.querySelectorAll('.docs-section');
  if (sections.length === 0) return;

  // Build a map: section id -> sidebar link
  const linkMap = {};
  sidebarLinks.forEach((link) => {
    const href = link.getAttribute('href');
    if (href && href.startsWith('#')) {
      linkMap[href.slice(1)] = link;
    }
  });

  let currentActive = null;

  const observer = new IntersectionObserver(
    (entries) => {
      // Find the topmost visible section
      let topEntry = null;
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          if (!topEntry || entry.boundingClientRect.top < topEntry.boundingClientRect.top) {
            topEntry = entry;
          }
        }
      });

      if (topEntry) {
        const id = topEntry.target.id;
        const link = linkMap[id];
        if (link && link !== currentActive) {
          if (currentActive) currentActive.classList.remove('active');
          link.classList.add('active');
          currentActive = link;

          // Scroll sidebar to keep active link visible
          if (sidebar.scrollHeight > sidebar.clientHeight) {
            link.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
          }
        }
      }
    },
    {
      rootMargin: `-${getComputedStyle(document.documentElement).getPropertyValue('--nav-height').trim() || '60px'} 0px -60% 0px`,
      threshold: 0
    }
  );

  sections.forEach((section) => {
    observer.observe(section);
  });

  // Also handle hash on page load
  if (window.location.hash) {
    const id = window.location.hash.slice(1);
    const link = linkMap[id];
    if (link) {
      sidebarLinks.forEach((l) => l.classList.remove('active'));
      link.classList.add('active');
      currentActive = link;
    }
  }
}
