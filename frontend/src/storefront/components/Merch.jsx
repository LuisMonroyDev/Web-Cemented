import "./Merch.css";
import { products } from "../data/products";

export default function Merch() {
  return (
    <section className="section merch" id="merch">
      <div className="section__head">
        <h2 className="section__title">Merch</h2>
        <div className="section__rule" />
      </div>

      <div className="merch__grid">
        {products.map((product) => (
          <article className="card" key={product.id}>
            <div
              className="card__img"
              style={product.image ? { backgroundImage: `url(${product.image})` } : undefined}
            >
              {!product.image && <span className="card__ph">Merch</span>}
            </div>
            <h3 className="card__name">{product.name}</h3>
            <p className="card__price">${product.price}</p>
            <button className="card__btn" type="button">
              Add to Cart
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}
