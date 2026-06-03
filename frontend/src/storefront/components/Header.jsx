import { useState } from "react";
import "./Header.css";
import logoSrc from "../../assets/cemented_logo_web.png";
import { useStore } from "../storeContext";

// Logo is bundled by Vite from src/assets. If it ever fails to load,
// the header falls back to the "Cemented" wordmark.
const LOGO_SRC = logoSrc;

// Public booking contact for logged-out visitors (most likely promoters /
// bookers). A domain alias that forwards to the band inbox so it reads
// professionally. Signed-in customers get contact@ in the account drawer.
const BOOKING_EMAIL = "bookings@cemented.band";

// Slow, eased scroll so nav clicks "drag" the page rather than snap.
let scrollFrame = null;
function animateScrollTo(targetTop, duration = 900) {
  if (scrollFrame) cancelAnimationFrame(scrollFrame); // a fresh click wins
  const startTop = window.scrollY;
  const distance = targetTop - startTop;
  const startTime = performance.now();
  function step(now) {
    const t = Math.min((now - startTime) / duration, 1);
    const eased = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; // easeInOutQuad
    window.scrollTo(0, startTop + distance * eased);
    scrollFrame = t < 1 ? requestAnimationFrame(step) : null;
  }
  scrollFrame = requestAnimationFrame(step);
}

function scrollToSection(event, id) {
  event.preventDefault();
  const target = document.getElementById(id);
  if (!target) return;
  // Land just above the section so the sticky header doesn't cover its title.
  const header = document.querySelector(".hdr");
  const offset = (header?.offsetHeight ?? 0) + 16;
  const top = target.getBoundingClientRect().top + window.scrollY - offset;
  animateScrollTo(top);
}

// Logo click scrolls back to the top. preventDefault stops the browser from
// appending "#top" to the URL (and matches the nav links' smooth-scroll feel).
function scrollToTop(event) {
  event.preventDefault();
  animateScrollTo(0);
}

export default function Header() {
  const [logoOk, setLogoOk] = useState(true);
  // Mobile only: the nav collapses behind a hamburger. On desktop the nav is
  // always shown (CSS), so this flag is a no-op there.
  const [menuOpen, setMenuOpen] = useState(false);
  const { user, count, openAuth, openCart, openAccount } = useStore();

  const closeMenu = () => setMenuOpen(false);

  return (
    <header className="hdr">
      <span className="hdr__est">Official Store</span>

      <div className="hdr__brand">
        {logoOk ? (
          <a
            className="hdr__logolink"
            href="#top"
            onClick={(e) => {
              scrollToTop(e);
              closeMenu();
            }}
          >
            <img
              className="hdr__logo"
              src={LOGO_SRC}
              alt="Cemented"
              onError={() => setLogoOk(false)}
            />
          </a>
        ) : (
          <a
            className="hdr__wordmark"
            href="#top"
            onClick={(e) => {
              scrollToTop(e);
              closeMenu();
            }}
          >
            Cemented
          </a>
        )}
        <span className="hdr__tag">[ Est. 2025 ]</span>
      </div>

      {/* Mobile menu toggle — hidden on desktop via CSS. */}
      <button
        type="button"
        className="hdr__burger"
        aria-label={menuOpen ? "Close menu" : "Open menu"}
        aria-expanded={menuOpen}
        onClick={() => setMenuOpen((open) => !open)}
      >
        <svg width="26" height="26" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      <nav className={`hdr__nav${menuOpen ? " hdr__nav--open" : ""}`}>
        <a
          href="#music"
          onClick={(e) => {
            scrollToSection(e, "music");
            closeMenu();
          }}
        >
          Music
        </a>
        <a
          href="#merch"
          onClick={(e) => {
            scrollToSection(e, "merch");
            closeMenu();
          }}
        >
          Merch
        </a>
        <button
          type="button"
          className="hdr__btn"
          onClick={() => {
            openCart();
            closeMenu();
          }}
        >
          Cart ({count})
        </button>
        {user ? (
          <button
            type="button"
            className="hdr__btn hdr__account"
            onClick={() => {
              openAccount();
              closeMenu();
            }}
          >
            {user.username}
          </button>
        ) : (
          <>
            {/* Public booking contact — bookers usually aren't logged in. */}
            <a
              className="hdr__booking"
              href={`mailto:${BOOKING_EMAIL}`}
              onClick={closeMenu}
            >
              Booking
            </a>
            <button
              type="button"
              className="hdr__btn hdr__login"
              onClick={() => {
                openAuth();
                closeMenu();
              }}
            >
              Log in
            </button>
          </>
        )}
      </nav>
    </header>
  );
}
