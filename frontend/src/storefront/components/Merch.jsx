import { useEffect, useState } from "react";
import "./Merch.css";
import { products as fallbackProducts } from "../data/products";
import { fetchProducts } from "../../lib/api";
import { useStore } from "../storeContext";

export default function Merch() {
  const [products, setProducts] = useState(fallbackProducts);
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

  return (
    <section className="section merch" id="merch">
      <div className="section__head">
        <h2 className="section__title">Merch</h2>
        <div className="section__rule" />
      </div>

      <div className="merch__grid">
        {products.map((product) => {
          const soldOut = product.stock === 0;
          return (
            <article className="card" key={product.id}>
              <div
                className="card__img"
                style={product.image ? { backgroundImage: `url(${product.image})` } : undefined}
              >
                {!product.image && <span className="card__ph">Merch</span>}
              </div>
              <h3 className="card__name">{product.name}</h3>
              <p className="card__price">${product.price}</p>
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
    </section>
  );
}
