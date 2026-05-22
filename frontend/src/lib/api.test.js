import { describe, it, expect, vi, afterEach } from "vitest";
import { fetchHealth } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchHealth", () => {
  it("returns the parsed JSON when the response is ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "ok", service: "web-cemented-api" }),
      }),
    );

    const data = await fetchHealth();

    expect(data.status).toBe("ok");
  });

  it("throws when the response is not ok", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));

    await expect(fetchHealth()).rejects.toThrow("500");
  });
});
