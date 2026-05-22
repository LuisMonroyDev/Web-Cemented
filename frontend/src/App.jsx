import { useEffect, useState } from "react";
import { fetchHealth } from "./lib/api";
import "./App.css";

function App() {
  const [apiStatus, setApiStatus] = useState("checking…");

  useEffect(() => {
    fetchHealth()
      .then((data) => setApiStatus(`connected — ${data.status}`))
      .catch((error) => setApiStatus(`not connected — ${error.message}`));
  }, []);

  return (
    <main className="app">
      <h1>Web-Cemented</h1>
      <p className="tagline">Band site — skeleton</p>
      <p className="api-status">Backend API: {apiStatus}</p>
    </main>
  );
}

export default App;
