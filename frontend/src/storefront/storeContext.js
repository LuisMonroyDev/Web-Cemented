import { createContext, useContext } from "react";

// Holds auth (user) + cart state and the actions that mutate them.
export const StoreContext = createContext(null);

export function useStore() {
  const ctx = useContext(StoreContext);
  if (!ctx) {
    throw new Error("useStore must be used inside <StoreProvider>");
  }
  return ctx;
}
