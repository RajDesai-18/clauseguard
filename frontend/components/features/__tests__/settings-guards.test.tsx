import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { PasswordCard, ConnectedAccounts } from "@/components/features/settings-view";

// The password change path calls authClient.changePassword; the connect/
// disconnect paths call linkSocial / unlinkAccount. Mock the client so no
// real network happens and we can assert on the guard behavior.
vi.mock("@/lib/auth-client", () => ({
  authClient: {
    changePassword: vi.fn(),
    setPassword: vi.fn(),
    linkSocial: vi.fn(),
    unlinkAccount: vi.fn(),
    listAccounts: vi.fn(),
  },
}));

const { authClient } = await import("@/lib/auth-client");

beforeEach(() => {
  vi.clearAllMocks();
});

describe("PasswordCard", () => {
  it("shows the set-password form for a Google-only account (no password)", () => {
    render(<PasswordCard hasPassword={false} onChanged={() => {}} />);

    // Set-password affordance, not the change-password form.
    expect(screen.getByText(/signed in with google/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^new password$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^confirm password$/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /set password/i })).toBeInTheDocument();
    // The tell that distinguishes set-password from change-password:
    // there is no current-password field, because there is nothing to verify.
    expect(screen.queryByLabelText(/current password/i)).not.toBeInTheDocument();
  });

  it("posts to the set-password route and refetches accounts on success", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ok: true }),
    } as Response);
    vi.stubGlobal("fetch", fetchMock);

    const onChanged = vi.fn();
    const user = userEvent.setup();
    render(<PasswordCard hasPassword={false} onChanged={onChanged} />);

    const submit = screen.getByRole("button", { name: /set password/i });
    expect(submit).toBeDisabled();

    // A matching 8+ char password satisfies validity.
    await user.type(screen.getByLabelText(/^new password$/i), "newpassword1");
    await user.type(screen.getByLabelText(/^confirm password$/i), "newpassword1");
    expect(submit).toBeEnabled();

    await user.click(submit);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/account/set-password",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ newPassword: "newpassword1" }),
      })
    );
    expect(onChanged).toHaveBeenCalledTimes(1);

    vi.unstubAllGlobals();
  });

  it("shows the change-password form when a password already exists", () => {
    render(<PasswordCard hasPassword={true} onChanged={() => {}} />);

    expect(screen.getByLabelText(/current password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^new password$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm new password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /update password/i })).toBeInTheDocument();
  });

  it("keeps the submit disabled until the form is valid", async () => {
    const user = userEvent.setup();
    render(<PasswordCard hasPassword={true} onChanged={() => {}} />);

    const submit = screen.getByRole("button", { name: /update password/i });
    expect(submit).toBeDisabled();

    // Fill current + a matching 8+ char new/confirm to satisfy validity.
    await user.type(screen.getByLabelText(/current password/i), "oldpassword");
    await user.type(screen.getByLabelText(/^new password$/i), "newpassword1");
    await user.type(screen.getByLabelText(/confirm new password/i), "newpassword1");

    expect(submit).toBeEnabled();
  });

  it("does not enable submit when new and confirm differ", async () => {
    const user = userEvent.setup();
    render(<PasswordCard hasPassword={true} onChanged={() => {}} />);

    await user.type(screen.getByLabelText(/current password/i), "oldpassword");
    await user.type(screen.getByLabelText(/^new password$/i), "newpassword1");
    await user.type(screen.getByLabelText(/confirm new password/i), "different99");

    expect(screen.getByRole("button", { name: /update password/i })).toBeDisabled();
    expect(screen.getByText(/passwords don.t match/i)).toBeInTheDocument();
  });
});

describe("ConnectedAccounts", () => {
  it("disables Disconnect when it would lock the user out (canDisconnect=false)", () => {
    render(<ConnectedAccounts googleConnected={true} canDisconnect={false} onChanged={() => {}} />);

    const disconnect = screen.getByRole("button", { name: /disconnect/i });
    expect(disconnect).toBeDisabled();
    // The explanatory note is present.
    expect(screen.getByText(/only way to sign in/i)).toBeInTheDocument();
  });

  it("enables Disconnect when a fallback credential exists (canDisconnect=true)", () => {
    render(<ConnectedAccounts googleConnected={true} canDisconnect={true} onChanged={() => {}} />);

    expect(screen.getByRole("button", { name: /disconnect/i })).toBeEnabled();
    expect(screen.queryByText(/only way to sign in/i)).not.toBeInTheDocument();
  });

  it("calls unlinkAccount with the google provider on disconnect", async () => {
    vi.mocked(authClient.unlinkAccount).mockResolvedValueOnce({ data: null, error: null } as never);
    const onChanged = vi.fn();
    const user = userEvent.setup();
    render(<ConnectedAccounts googleConnected={true} canDisconnect={true} onChanged={onChanged} />);

    await user.click(screen.getByRole("button", { name: /disconnect/i }));

    expect(authClient.unlinkAccount).toHaveBeenCalledWith({ providerId: "google" });
  });

  it("shows Connect (not Disconnect) when Google is not linked", () => {
    render(
      <ConnectedAccounts googleConnected={false} canDisconnect={false} onChanged={() => {}} />
    );

    expect(screen.getByRole("button", { name: /^connect$/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /disconnect/i })).not.toBeInTheDocument();
  });
});
