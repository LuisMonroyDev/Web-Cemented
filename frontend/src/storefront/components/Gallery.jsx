import { useCallback, useEffect, useRef, useState } from "react";
import "./Gallery.css";
import { photos as fallbackPhotos } from "../data/photos";
import { fetchGallery } from "../../lib/api";

// --- Scroll-hint motion -----------------------------------------------------
// A deliberately un-generic "nudge": the strip drifts open with a soft,
// decelerating reveal, then takes a long, slow inertial path back. The
// asymmetric timing + small distance make it read as a subconscious cue
// ("this pans sideways") rather than an attention-grabbing bounce. It animates
// the real scroll position, so the slim indicator tracks along with it.
const PEEK_PX = 44; // how far the strip drifts to reveal there's more
const NUDGE_MS = 1250; // total duration — the slow return is what sells it
const OUT_PHASE = 0.28; // fraction of the timeline spent drifting open

const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
const easeInOutCubic = (t) =>
  t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

export default function Gallery() {
  const [photos, setPhotos] = useState(fallbackPhotos);
  const [scrollable, setScrollable] = useState(false);
  const [thumb, setThumb] = useState({ width: 0, left: 0 });

  const trackRef = useRef(null);
  const sectionRef = useRef(null);
  const animatingRef = useRef(false);
  const hintedRef = useRef(false);

  useEffect(() => {
    let active = true;
    fetchGallery()
      .then((data) => {
        if (active && data.length) {
          setPhotos(data.map((g) => ({ src: g.image, alt: g.caption })));
        }
      })
      .catch(() => {}); // keep placeholders if the API isn't reachable
    return () => {
      active = false;
    };
  }, []);

  // Keep the slim indicator in sync with the real scroll position.
  useEffect(() => {
    const track = trackRef.current;
    if (!track) return undefined;
    const update = () => {
      const { scrollWidth, clientWidth, scrollLeft } = track;
      const overflow = scrollWidth - clientWidth;
      if (overflow <= 4) {
        setScrollable(false);
        return;
      }
      setScrollable(true);
      const width = (clientWidth / scrollWidth) * 100;
      setThumb({ width, left: (scrollLeft / overflow) * (100 - width) });
    };
    update();
    track.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      track.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [photos]);

  const nudge = useCallback(() => {
    const track = trackRef.current;
    if (!track || animatingRef.current) return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches) return;
    if (track.scrollWidth - track.clientWidth <= 4) return; // nothing to reveal

    // Drift from wherever the user currently is — never jump them back to 0.
    const origin = track.scrollLeft;
    animatingRef.current = true;
    const snap = track.style.scrollSnapType;
    track.style.scrollSnapType = "none"; // don't let scroll-snap fight the nudge
    const start = performance.now();

    const frame = (now) => {
      const t = Math.min((now - start) / NUDGE_MS, 1);
      let x;
      if (t < OUT_PHASE) {
        // confident, decelerating reveal
        x = origin + PEEK_PX * easeOutCubic(t / OUT_PHASE);
      } else {
        // long, slow inertial settle back to origin
        x = origin + PEEK_PX * (1 - easeInOutCubic((t - OUT_PHASE) / (1 - OUT_PHASE)));
      }
      track.scrollLeft = x;
      if (t < 1) {
        requestAnimationFrame(frame);
      } else {
        track.scrollLeft = origin;
        track.style.scrollSnapType = snap;
        animatingRef.current = false;
      }
    };
    requestAnimationFrame(frame);
  }, []);

  // Fire the hint once, the first time the gallery scrolls into view.
  useEffect(() => {
    const section = sectionRef.current;
    if (!section || typeof IntersectionObserver === "undefined") return undefined;
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting && !hintedRef.current) {
            hintedRef.current = true;
            nudge();
            obs.disconnect();
          }
        });
      },
      { threshold: 0.45 }
    );
    obs.observe(section);
    return () => obs.disconnect();
  }, [nudge]);

  return (
    <section className="gallery" id="shop" aria-label="Gallery" ref={sectionRef}>
      <div className="gallery__track" ref={trackRef}>
        {photos.map((photo, i) => (
          <figure
            className="gallery__item"
            key={i}
            style={photo.src ? { backgroundImage: `url(${photo.src})` } : undefined}
          >
            {!photo.src && <figcaption className="gallery__ph">Photo {i + 1}</figcaption>}
          </figure>
        ))}
      </div>

      {scrollable && (
        <div className="gallery__scrollbar" aria-hidden="true">
          <span className="gallery__rail">
            <span
              className="gallery__thumb"
              style={{ width: `${thumb.width}%`, left: `${thumb.left}%` }}
            />
          </span>
        </div>
      )}
    </section>
  );
}
