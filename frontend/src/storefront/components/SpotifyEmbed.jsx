import "./SpotifyEmbed.css";

// Replace PLACEHOLDER with your real Spotify album/playlist id, e.g.
//   album:  https://open.spotify.com/embed/album/<ID>
//   playlist: https://open.spotify.com/embed/playlist/<ID>
// theme=0 keeps Spotify's dark player, which matches the site.
const SPOTIFY_EMBED =
  "https://open.spotify.com/embed/album/2kqnBO94DQyk82mJt0OQ5e?utm_source=generator&theme=0";

export default function SpotifyEmbed() {
  return (
    <section className="section listen" id="music">
      <div className="section__head">
        <h2 className="section__title">Listen</h2>
        <div className="section__rule" />
      </div>

      <div className="listen__player">
        <iframe
          title="Cemented on Spotify"
          src={SPOTIFY_EMBED}
          width="100%"
          height="352"
          loading="lazy"
          allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
        />
      </div>
    </section>
  );
}
