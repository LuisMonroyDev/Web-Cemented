import "./tokens.css";
import { StoreProvider } from "./StoreProvider";
import Header from "./components/Header";
import Gallery from "./components/Gallery";
import SpotifyEmbed from "./components/SpotifyEmbed";
import Merch from "./components/Merch";
import Footer from "./components/Footer";
import AuthModal from "./components/AuthModal";
import CartDrawer from "./components/CartDrawer";
import CheckoutBanner from "./components/CheckoutBanner";

export default function Storefront() {
  return (
    <StoreProvider>
      <div className="storefront" id="top">
        <CheckoutBanner />
        <Header />
        <Gallery />
        <SpotifyEmbed />
        <Merch />
        <Footer />
        <AuthModal />
        <CartDrawer />
      </div>
    </StoreProvider>
  );
}
