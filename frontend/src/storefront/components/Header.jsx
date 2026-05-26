import { useState } from "react";
import "./Header.css";
import logoSrc from "../../assets/cemented_logo_web.png";
import { useStore } from "../storeContext";

// Logo is bundled by Vite from src/assets. If it ever fails to load,
// the header falls back to the "Cemented" wordmark.
const LOGO_SRC = logoSrc;

export default function Header() {
  const [logoOk, setLogoOk] = useState(true);
  const { user, count, openAuth, openCart, signOut } = useStore();

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
        <button type="button" className="hdr__btn" onClick={openCart}>
          Cart ({count})
        </button>
        {user ? (
          <>
            <span className="hdr__user">{user.username}</span>
            <button type="button" className="hdr__btn hdr__login" onClick={signOut}>
              Log out
            </button>
          </>
        ) : (
          <button type="button" className="hdr__btn hdr__login" onClick={openAuth}>
            Log in
          </button>
        )}
      </nav>
    </header>
  );
}
