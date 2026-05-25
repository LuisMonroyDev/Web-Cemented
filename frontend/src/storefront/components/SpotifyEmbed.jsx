import { useEffect, useState } from "react";
import "./SpotifyEmbed.css";
import { fetchSiteSettings } from "../../lib/api";

// Used until the backend provides one, and if the API is unreachable.
// Must be a Spotify *embed* URL (https://open.spotify.com/embed/...).
const FALLBACK_EMBED =
  "https://open.spotify.com/embed/album/2kqnBO94DQyk82mJt0OQ5e?utm_source=generator&theme=0";

export default function SpotifyEmbed() {
  const [src, setSrc] = useState(FALLBACK_EMBED);

  useEffect(() => {
    let active = true;
    fetchSiteSettings()
      .then((settings) => {
        if (active && settings.spotify_embed_url) setSrc(settings.spotify_embed_url);
      })
      .catch(() => {}); // keep the fallback if the API isn't reachable
    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="section listen" id="music">
      <div className="section__head">
        <h2 className="section__title">Listen</h2>
        <div className="section__rule" />
      </div>

      <div className="listen__player">
        <iframe
          title="Cemented on Spotify"
          src={src}
          width="100%"
          height="352"
          loading="lazy"
          allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
        />
      </div>
    </section>
  );
}
