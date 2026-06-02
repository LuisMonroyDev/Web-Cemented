import { useEffect, useState } from "react";
import "./Merch.css";
import { products as fallbackProducts } from "../data/products";
import { fetchProducts } from "../../lib/api";
import { useStore } from "../storeContext";

// Threshold below which we nudge shoppers with an "only N left" message.
const LOW_STOCK = 5;

// Returns the stock label + modifier class for a given count, or null when the
// count isn't known (e.g. the offline fallback catalog has no stock field).
// The caller decides which count to pass: a product's overall total, or the
// stock of whichever size the shopper has selected.
function stockLabel(count) {
  if (typeof count !== "number") return null;
  if (count <= 0) return { text: "Sold out", modifier: "out" };
  if (count <= LOW_STOCK) return { text: `Only ${count} left`, modifier: "low" };
  return { text: `${count} in stock`, modifier: "in" };
}

// A single merch card. Owns its own selected-size state so each card tracks its
// size independently. Sized products require a size before "Add to Cart"; sold-
// out sizes are shown disabled (greyed) rather than hidden.
function ProductCard({ product, onZoom }) {
  const { addToCart } = useStore();
  const [selectedSize, setSelectedSize] = useState(null);

  const hasSizes = Array.isArray(product.sizes) && product.sizes.length > 0;
  const soldOut = product.stock === 0; // total across sizes for sized products
  const needsSize = hasSizes && selectedSize == null;
  const zoomable = Boolean(product.image);

  // Stock readout follows the selection: once a size is picked, show that
  // size's remaining stock; with nothing picked (or a size-less product), show
  // the overall total left.
  const chosen = hasSizes ? product.sizes.find((s) => s.id === selectedSize) : null;
  const stock = stockLabel(chosen ? chosen.stock : product.stock);

  const onAdd = () => {
    if (soldOut || needsSize) return;
    addToCart(product.id, 1, selectedSize);
  };

  const btnLabel = soldOut ? "Sold out" : needsSize ? "Select a size" : "Add to Cart";

  return (
    <article className="card">
      <div
        className={`card__img${zoomable ? " card__img--zoomable" : ""}`}
        style={product.image ? { backgroundImage: `url(${product.image})` } : undefined}
        role={zoomable ? "button" : undefined}
        tabIndex={zoomable ? 0 : undefined}
        aria-label={zoomable ? `View ${product.name} larger` : undefined}
        onClick={zoomable ? onZoom : undefined}
        onKeyDown={
          zoomable
            ? (e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onZoom();
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

      {hasSizes && (
        <div className="card__sizes" role="group" aria-label={`Choose a size for ${product.name}`}>
          {product.sizes.map((size) => {
            const out = size.stock <= 0;
            const active = selectedSize === size.id;
            return (
              <button
                key={size.id}
                type="button"
                className={`card__size${active ? " card__size--active" : ""}`}
                disabled={out}
                aria-pressed={active}
                title={out ? `${size.label} — sold out` : size.label}
                onClick={() => setSelectedSize(size.id)}
              >
                {size.label}
              </button>
            );
          })}
        </div>
      )}

      <button
        className="card__btn"
        type="button"
        disabled={soldOut || needsSize}
        onClick={onAdd}
      >
        {btnLabel}
      </button>
    </article>
  );
}

export default function Merch() {
  const [products, setProducts] = useState(fallbackProducts);
  const [lightbox, setLightbox] = useState(null); // the product whose image is enlarged

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
        {products.map((product) => (
          <ProductCard
            key={product.id}
            product={product}
            onZoom={() => setLightbox(product)}
          />
        ))}
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
