import { useEffect, useState } from "react";
import "./Gallery.css";
import { photos as fallbackPhotos } from "../data/photos";
import { fetchGallery } from "../../lib/api";

export default function Gallery() {
  const [photos, setPhotos] = useState(fallbackPhotos);

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

  return (
    <section className="gallery" id="shop" aria-label="Gallery">
      <div className="gallery__track">
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
    </section>
  );
}
