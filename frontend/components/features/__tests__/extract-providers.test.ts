import { describe, it, expect } from "vitest";

import { extractProviders } from "@/components/features/settings-view";

describe("extractProviders", () => {
  it("reads the confirmed Better Auth shape: { data: [{ providerId }] }", () => {
    const input = {
      data: [
        { providerId: "google", accountId: "x" },
        { providerId: "credential", accountId: "y" },
      ],
      error: null,
    };
    expect(extractProviders(input)).toEqual(["google", "credential"]);
  });

  it("falls back to `provider` when `providerId` is absent", () => {
    const input = { data: [{ provider: "google" }] };
    expect(extractProviders(input)).toEqual(["google"]);
  });

  it("handles a bare array (no data wrapper)", () => {
    const input = [{ providerId: "google" }, { providerId: "credential" }];
    expect(extractProviders(input)).toEqual(["google", "credential"]);
  });

  it("drops rows with neither providerId nor provider", () => {
    const input = { data: [{ providerId: "google" }, { accountId: "orphan" }] };
    expect(extractProviders(input)).toEqual(["google"]);
  });

  it("returns an empty array for null, undefined, or malformed input", () => {
    expect(extractProviders(null)).toEqual([]);
    expect(extractProviders(undefined)).toEqual([]);
    expect(extractProviders({ data: "not-an-array" })).toEqual([]);
    expect(extractProviders({})).toEqual([]);
  });
});
