import { useState } from "react";
import "./AuthModal.css";
import { useStore } from "../storeContext";

export default function AuthModal() {
  const { authOpen, closeAuth, signIn, signUp } = useStore();
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (!authOpen) return null;

  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "login") {
        await signIn(form.username, form.password);
      } else {
        await signUp(form);
      }
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setBusy(false);
    }
  };

  const toggle = () => {
    setMode(mode === "login" ? "signup" : "login");
    setError("");
  };

  return (
    <div className="authmodal" role="dialog" aria-modal="true">
      <div className="authmodal__scrim" onClick={closeAuth} />
      <div className="authmodal__card">
        <button className="authmodal__close" type="button" onClick={closeAuth} aria-label="Close">
          ×
        </button>
        <p className="authmodal__brand">Cemented</p>
        <h2 className="authmodal__title">{mode === "login" ? "Sign in" : "Create account"}</h2>

        <form className="authmodal__form" onSubmit={submit}>
          <label>
            Username
            <input value={form.username} onChange={update("username")} autoComplete="username" required />
          </label>
          {mode === "signup" && (
            <label>
              Email
              <input
                type="email"
                value={form.email}
                onChange={update("email")}
                autoComplete="email"
                required
              />
            </label>
          )}
          <label>
            Password
            <input
              type="password"
              value={form.password}
              onChange={update("password")}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
            />
          </label>
          {error && <p className="authmodal__error">{error}</p>}
          <button className="authmodal__submit" type="submit" disabled={busy}>
            {busy ? "…" : mode === "login" ? "Sign in" : "Sign up"}
          </button>
        </form>

        <p className="authmodal__toggle">
          {mode === "login" ? "No account yet?" : "Already have one?"}{" "}
          <button type="button" onClick={toggle}>
            {mode === "login" ? "Sign up" : "Sign in"}
          </button>
        </p>
      </div>
    </div>
  );
}
