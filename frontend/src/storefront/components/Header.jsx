import { useState } from "react";
import "./Header.css";
import logoSrc from "../../assets/cemented_logo_web.png";
import { ADMIN_URL } from "../../lib/api";

// Logo is bundled by Vite from src/assets. If it ever fails to load,
// the header falls back to the "Cemented" wordmark.
const LOGO_SRC = logoSrc;

export default function Header() {
  const [logoOk, setLogoOk] = useState(true);

  return (
    <header className="hdr">
      <span className="hdr__est">Official Store</span>

      <div className="hdr__brand">
        {logoOk ? (
          <a className="hdr__logolink" href="#top">
            <img
              className="hdr__logo"
              src={LOGO_SRC}
              alt="Cemented"
              onError={() => setLogoOk(false)}
            />
          </a>
        ) : (
          <a className="hdr__wordmark" href="#top">
            Cemented
          </a>
        )}
        <span className="hdr__tag">[ Est. 2025 ]</span>
      </div>

      <nav className="hdr__nav">
        <a href="#music">Music</a>
        <a href="#merch">Merch</a>
        <a href="#cart">Cart (0)</a>
        <a className="hdr__login" href={ADMIN_URL} target="_blank" rel="noopener noreferrer">
          Log in
        </a>
      </nav>
    </header>
  );
}
