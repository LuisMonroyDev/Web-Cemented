import { useEffect, useState } from "react";
import "./Footer.css";
import { fetchSiteSettings } from "../../lib/api";

// Maps each social link to the SiteSettings field that holds its URL.
const SOCIALS = [
  { key: "instagram_url", label: "Instagram" },
  { key: "tiktok_url", label: "TikTok" },
  { key: "youtube_url", label: "YouTube" },
  { key: "spotify_artist_url", label: "Spotify" },
];

export default function Footer() {
  const [settings, setSettings] = useState({});

  useEffect(() => {
    let active = true;
    fetchSiteSettings()
      .then((data) => {
        if (active) setSettings(data);
      })
      .catch(() => {}); // no links if the API isn't reachable
    return () => {
      active = false;
    };
  }, []);

  const links = SOCIALS.filter((social) => settings[social.key]);

  return (
    <footer className="ftr">
      <span className="ftr__copy">© 2026 Cemented — All Rights Reserved</span>
      {links.length > 0 && (
        <nav className="ftr__social">
          {links.map((social) => (
            <a
              key={social.key}
              href={settings[social.key]}
              target="_blank"
              rel="noreferrer"
            >
              {social.label}
            </a>
          ))}
        </nav>
      )}
    </footer>
  );
}
