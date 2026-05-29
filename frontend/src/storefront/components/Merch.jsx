import { useEffect, useState } from "react";
import "./Merch.css";
import { products as fallbackProducts } from "../data/products";
import { fetchProducts } from "../../lib/api";
import { useStore } from "../storeContext";

// Threshold below which we nudge shoppers with an "only N left" message.
const LOW_STOCK = 5;

// Returns the stock label + modifier class for a product, or null when stock
// isn't known (e.g. the offline fallback catalog has no stock field).
function stockInfo(product) {
  if (typeof product.stock !== "number") return null;
  if (product.stock <= 0) return { text: "Sold out", modifier: "out" };
  if (product.stock <= LOW_STOCK)
    return { text: `Only ${product.stock} left`, modifier: "low" };
  return { text: `${product.stock} in stock`, modifier: "in" };
}

export default function Merch() {
  const [products, setProducts] = useState(fallbackProducts);
  const [lightbox, setLightbox] = useState(null); // the product whose image is enlarged
  const { addToCart } = useStore();

  useEffect(() => {
    let active = true;
    fetchProducts()
      .then((data) => {
        if (active && data.length) setProducts(data);
      })
      .catch(() => {}); // keep placeholders if the API isn't reachable
    return () => {
      active = false;
    };
  }, []);

  // Close the lightbox on Escape while it's open.
  useEffect(() => {
    if (!lightbox) return undefined;
    const onKey = (e) => {
      if (e.key === "Escape") setLightbox(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [lightbox]);

  return (
    <section className="section merch" id="merch">
      <div className="section__head">
        <h2 className="section__title">Merch</h2>
        <div className="section__rule" />
      </div>

      <div className="merch__grid">
        {products.map((product) => {
          const soldOut = product.stock === 0;
          const stock = stockInfo(product);
          const zoomable = Boolean(product.image);
          return (
            <article className="card" key={product.id}>
              <div
                className={`card__img${zoomable ? " card__img--zoomable" : ""}`}
                style={product.image ? { backgroundImage: `url(${product.image})` } : undefined}
                role={zoomable ? "button" : undefined}
                tabIndex={zoomable ? 0 : undefined}
                aria-label={zoomable ? `View ${product.name} larger` : undefined}
                onClick={zoomable ? () => setLightbox(product) : undefined}
                onKeyDown={
                  zoomable
                    ? (e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          setLightbox(product);
                        }
                      }
                    : undefined
                }
              >
                {!product.image && <span className="card__ph">Merch</span>}
              </div>
              <h3 className="card__name">{product.name}</h3>
              <div className="card__meta">
                <p className="card__price">${product.price}</p>
                {stock && (
                  <span className={`card__stock card__stock--${stock.modifier}`}>
                    {stock.text}
                  </span>
                )}
              </div>
              <button
                className="card__btn"
                type="button"
                disabled={soldOut}
                onClick={() => addToCart(product.id)}
              >
                {soldOut ? "Sold out" : "Add to Cart"}
              </button>
            </article>
          );
        })}
      </div>

      {lightbox && (
        <div
          className="lightbox"
          role="dialog"
          aria-modal="true"
          aria-label={lightbox.name}
          onClick={() => setLightbox(null)}
        >
          <button
            className="lightbox__close"
            type="button"
            aria-label="Close"
            onClick={() => setLightbox(null)}
          >
            &times;
          </button>
          <figure className="lightbox__figure" onClick={(e) => e.stopPropagation()}>
            <div className="lightbox__stage">
              <img className="lightbox__img" src={lightbox.image} alt={lightbox.name} />
            </div>
            <figcaption className="lightbox__caption">{lightbox.name}</figcaption>
          </figure>
        </div>
      )}
    </section>
  );
}
