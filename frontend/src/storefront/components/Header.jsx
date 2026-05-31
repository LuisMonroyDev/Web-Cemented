import { useState } from "react";
import "./Header.css";
import logoSrc from "../../assets/cemented_logo_web.png";
import { useStore } from "../storeContext";

// Logo is bundled by Vite from src/assets. If it ever fails to load,
// the header falls back to the "Cemented" wordmark.
const LOGO_SRC = logoSrc;

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
  const { user, count, openAuth, openCart, openAccount } = useStore();

  return (
    <header className="hdr">
      <span className="hdr__est">Official Store</span>

      <div className="hdr__brand">
        {logoOk ? (
          <a className="hdr__logolink" href="#top" onClick={scrollToTop}>
            <img
              className="hdr__logo"
              src={LOGO_SRC}
              alt="Cemented"
              onError={() => setLogoOk(false)}
            />
          </a>
        ) : (
          <a className="hdr__wordmark" href="#top" onClick={scrollToTop}>
            Cemented
          </a>
        )}
        <span className="hdr__tag">[ Est. 2025 ]</span>
      </div>

      <nav className="hdr__nav">
        <a href="#music" onClick={(e) => scrollToSection(e, "music")}>Music</a>
        <a href="#merch" onClick={(e) => scrollToSection(e, "merch")}>Merch</a>
        <button type="button" className="hdr__btn" onClick={openCart}>
          Cart ({count})
        </button>
        {user ? (
          <button type="button" className="hdr__btn hdr__account" onClick={openAccount}>
            {user.username}
          </button>
        ) : (
          <button type="button" className="hdr__btn hdr__login" onClick={openAuth}>
            Log in
          </button>
        )}
      </nav>
    </header>
  );
}
