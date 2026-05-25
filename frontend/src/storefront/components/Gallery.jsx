import "./Gallery.css";
import { photos } from "../data/photos";

export default function Gallery() {
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
