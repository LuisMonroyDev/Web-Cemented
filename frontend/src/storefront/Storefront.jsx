import "./tokens.css";
import Header from "./components/Header";
import Gallery from "./components/Gallery";
import SpotifyEmbed from "./components/SpotifyEmbed";
import Merch from "./components/Merch";
import Footer from "./components/Footer";

export default function Storefront() {
  return (
    <div className="storefront" id="top">
      <Header />
      <Gallery />
      <SpotifyEmbed />
      <Merch />
      <Footer />
    </div>
  );
}
