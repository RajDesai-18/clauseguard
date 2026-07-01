/* eslint-disable react-hooks/set-state-in-effect */
"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";

import { authClient } from "@/lib/auth-client";

interface Props {
  initialName: string;
  email: string;
  image: string | null;
}

export function SettingsView({ initialName, email, image }: Props) {
  return (
    <div className="space-y-10">
      <header>
        <p className="text-caption text-muted-foreground mb-3 font-mono uppercase">Account</p>
        <h2 className="text-heading-lg font-display text-foreground font-medium">Settings</h2>
        <p className="text-body text-muted-foreground mt-2 max-w-[60ch]">
          Manage your profile, appearance, and account security.
        </p>
      </header>

      <ProfileSection initialName={initialName} email={email} image={image} />
      <SecuritySection />
      <AppearanceSection />
      <DangerZoneSection />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Profile
// ---------------------------------------------------------------------------

function ProfileSection({ initialName, email, image }: Props) {
  const router = useRouter();
  const [name, setName] = useState(initialName);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const trimmed = name.trim();
  const dirty = trimmed.length > 0 && trimmed !== initialName;
  const initials = getInitials(initialName || email);

  const handleSave = async () => {
    if (!dirty) return;
    setIsSaving(true);
    setError(null);
    setSaved(false);

    try {
      const res = await authClient.updateUser({ name: trimmed });
      // Better Auth's client returns { data, error } rather than throwing.
      if (res && "error" in res && res.error) {
        throw new Error(res.error.message ?? "Couldn't update your name.");
      }
      setSaved(true);
      // Re-run server components so the top-bar avatar/name pick up the change.
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't update your name.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <SettingsSection
      label="Profile"
      title="Your details"
      description="How you appear across ClauseGuard."
    >
      <div className="flex items-center gap-4">
        <div className="bg-muted text-foreground relative flex size-12 shrink-0 items-center justify-center overflow-hidden rounded-sm">
          {image ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={image} alt="" className="size-full object-cover" />
          ) : (
            <span className="font-mono text-[13px] uppercase">{initials}</span>
          )}
        </div>
        <div className="min-w-0">
          <p className="text-body-sm text-foreground truncate font-medium">{initialName || "—"}</p>
          <p className="text-body-sm text-muted-foreground truncate">{email}</p>
        </div>
      </div>

      <div className="space-y-2">
        <label
          htmlFor="display-name"
          className="text-caption text-muted-foreground block font-mono uppercase"
        >
          Display name
        </label>
        <div className="flex flex-wrap gap-2">
          <input
            id="display-name"
            type="text"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              setSaved(false);
              setError(null);
            }}
            maxLength={80}
            className="border-border bg-card text-foreground focus-visible:border-foreground focus-visible:ring-foreground/30 min-w-0 flex-1 rounded-sm border px-3 py-2 text-[14px] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-offset-0 focus-visible:outline-none"
          />
          <button
            type="button"
            onClick={handleSave}
            disabled={!dirty || isSaving}
            className="border-foreground bg-foreground text-background hover:bg-foreground/90 font-display rounded-sm border px-4 py-2 text-[13px] font-medium transition-colors duration-150 active:scale-[0.99] disabled:opacity-40"
          >
            {isSaving ? "Saving…" : "Save"}
          </button>
        </div>
        {error && <p className="text-destructive text-body-sm">{error}</p>}
        {saved && !error && <p className="text-muted-foreground text-body-sm">Saved.</p>}
      </div>

      <div className="space-y-1.5">
        <p className="text-caption text-muted-foreground font-mono uppercase">Email</p>
        <p className="text-body-sm text-foreground/85">{email}</p>
        <p className="text-caption text-muted-foreground/70 leading-relaxed normal-case">
          Changing your email requires a verification step, which will be available once email
          delivery is configured.
        </p>
      </div>
    </SettingsSection>
  );
}

// ---------------------------------------------------------------------------
// Security
// ---------------------------------------------------------------------------

const PASSWORD_MIN_LENGTH = 8;

function SecuritySection() {
  const [providers, setProviders] = useState<string[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await authClient.listAccounts();
      setProviders(extractProviders(res));
      setLoadError(null);
    } catch {
      setProviders([]);
      setLoadError("Couldn't load your sign-in methods.");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const hasPassword = providers?.includes("credential") ?? false;
  const googleConnected = providers?.includes("google") ?? false;
  // Google may only be disconnected if there's another way to sign in.
  // Google is the only social provider, so that "other way" is a password.
  const canDisconnectGoogle = hasPassword;

  return (
    <SettingsSection
      label="Security"
      title="Sign-in & password"
      description="How you access your account."
    >
      {providers === null ? (
        <p className="text-body-sm text-muted-foreground animate-pulse">Loading…</p>
      ) : loadError ? (
        <p className="text-destructive text-body-sm">{loadError}</p>
      ) : (
        <>
          <PasswordCard hasPassword={hasPassword} onChanged={refresh} />
          <ConnectedAccounts
            googleConnected={googleConnected}
            canDisconnect={canDisconnectGoogle}
            onChanged={refresh}
          />
        </>
      )}
    </SettingsSection>
  );
}

export function PasswordCard({
  hasPassword,
  onChanged,
}: {
  hasPassword: boolean;
  onChanged: () => void;
}) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [revokeOthers, setRevokeOthers] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  // Google-only accounts have no password to change, and set-password
  // isn't exposed as an auth route in this config. Setting a first
  // password is a sensitive account operation we'll wire through the
  // backend account endpoints (alongside delete-account) rather than
  // fake it client-side.
  if (!hasPassword) {
    return (
      <div className="space-y-2">
        <p className="text-body-sm text-foreground font-medium">Password</p>
        <p className="text-body-sm text-muted-foreground leading-relaxed">
          You signed in with Google, so this account has no password yet. Setting a password to
          enable email sign-in is coming with account management.
        </p>
      </div>
    );
  }

  const valid = next.length >= PASSWORD_MIN_LENGTH && next === confirm && current.length > 0;

  const submit = async () => {
    if (!valid) return;
    setBusy(true);
    setError(null);
    setDone(false);
    try {
      const res = await authClient.changePassword({
        currentPassword: current,
        newPassword: next,
        revokeOtherSessions: revokeOthers,
      });
      if (res && "error" in res && res.error) {
        throw new Error(res.error.message ?? "Couldn't update your password.");
      }
      setDone(true);
      setCurrent("");
      setNext("");
      setConfirm("");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't update your password.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <p className="text-body-sm text-foreground font-medium">Change password</p>
        <p className="text-body-sm text-muted-foreground mt-0.5">
          Update the password you use to sign in.
        </p>
      </div>

      <Field
        id="current-password"
        label="Current password"
        type="password"
        autoComplete="current-password"
        value={current}
        onChange={setCurrent}
      />
      <Field
        id="new-password"
        label="New password"
        type="password"
        autoComplete="new-password"
        value={next}
        onChange={(v) => {
          setNext(v);
          setDone(false);
          setError(null);
        }}
      />
      <Field
        id="confirm-password"
        label="Confirm new password"
        type="password"
        autoComplete="new-password"
        value={confirm}
        onChange={setConfirm}
      />

      {next.length > 0 && next.length < PASSWORD_MIN_LENGTH && (
        <p className="text-muted-foreground text-body-sm">
          Use at least {PASSWORD_MIN_LENGTH} characters.
        </p>
      )}
      {confirm.length > 0 && next !== confirm && (
        <p className="text-muted-foreground text-body-sm">Passwords don&rsquo;t match.</p>
      )}

      <label className="flex cursor-pointer items-center gap-2.5">
        <input
          type="checkbox"
          checked={revokeOthers}
          onChange={(e) => setRevokeOthers(e.target.checked)}
          className="accent-foreground size-3.5"
        />
        <span className="text-body-sm text-muted-foreground">Sign out other devices</span>
      </label>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={submit}
          disabled={!valid || busy}
          className="border-foreground bg-foreground text-background hover:bg-foreground/90 font-display rounded-sm border px-4 py-2 text-[13px] font-medium transition-colors duration-150 active:scale-[0.99] disabled:opacity-40"
        >
          {busy ? "Saving…" : "Update password"}
        </button>
        {done && !error && <span className="text-muted-foreground text-body-sm">Saved.</span>}
      </div>
      {error && <p className="text-destructive text-body-sm">{error}</p>}
    </div>
  );
}

export function ConnectedAccounts({
  googleConnected,
  canDisconnect,
  onChanged,
}: {
  googleConnected: boolean;
  canDisconnect: boolean;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connect = async () => {
    setBusy(true);
    setError(null);
    try {
      // Full OAuth redirect to Google; returns to /settings, where the
      // accounts list refetches on mount and shows the new link.
      await authClient.linkSocial({ provider: "google", callbackURL: "/settings" });
    } catch {
      setError("Couldn't start the Google connection.");
      setBusy(false);
    }
  };

  const disconnect = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await authClient.unlinkAccount({ providerId: "google" });
      if (res && "error" in res && res.error) {
        throw new Error(res.error.message ?? "Couldn't disconnect Google.");
      }
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't disconnect Google.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="border-border/40 border-t pt-6">
      <p className="text-body-sm text-foreground font-medium">Connected accounts</p>
      <div className="border-border/40 mt-3 flex items-center justify-between gap-4 rounded-sm border px-4 py-3">
        <div className="min-w-0">
          <p className="text-body-sm text-foreground font-medium">Google</p>
          <p className="text-body-sm text-muted-foreground">
            {googleConnected ? "Connected" : "Not connected"}
          </p>
        </div>
        {googleConnected ? (
          <button
            type="button"
            onClick={disconnect}
            disabled={busy || !canDisconnect}
            title={canDisconnect ? undefined : "Set a password first so you don't lose access."}
            className="border-border bg-card hover:bg-foreground/4 hover:border-border/80 text-foreground/90 hover:text-foreground shrink-0 rounded-sm border px-3.5 py-1.5 font-mono text-[11px] tracking-[0.08em] uppercase transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Disconnect
          </button>
        ) : (
          <button
            type="button"
            onClick={connect}
            disabled={busy}
            className="border-foreground bg-foreground text-background hover:bg-foreground/90 font-display shrink-0 rounded-sm border px-3.5 py-1.5 text-[13px] font-medium transition-colors duration-150 active:scale-[0.99] disabled:opacity-40"
          >
            Connect
          </button>
        )}
      </div>
      {googleConnected && !canDisconnect && (
        <p className="text-caption text-muted-foreground/70 mt-2 leading-relaxed normal-case">
          Google is currently your only way to sign in, so it can&rsquo;t be disconnected. Once
          password sign-in is available, you&rsquo;ll be able to remove it.
        </p>
      )}
      {error && <p className="text-destructive text-body-sm mt-2">{error}</p>}
    </div>
  );
}

// Accepts any of Better Auth's listAccounts return shapes and extracts
// provider ids. Confirmed shape here is { data: [{ providerId }] }, but
// this stays robust across versions that return a bare array or `provider`.
export function extractProviders(result: unknown): string[] {
  const rows = Array.isArray(result) ? result : ((result as { data?: unknown })?.data ?? []);
  if (!Array.isArray(rows)) return [];
  return rows
    .map((row) => {
      const r = row as { provider?: string; providerId?: string };
      return r.providerId ?? r.provider ?? "";
    })
    .filter(Boolean);
}

function Field({
  id,
  label,
  value,
  onChange,
  type = "text",
  autoComplete,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  autoComplete?: string;
}) {
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="text-caption text-muted-foreground block font-mono uppercase">
        {label}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        autoComplete={autoComplete}
        onChange={(e) => onChange(e.target.value)}
        className="border-border bg-card text-foreground focus-visible:border-foreground focus-visible:ring-foreground/30 w-full rounded-sm border px-3 py-2 text-[14px] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-offset-0 focus-visible:outline-none"
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Appearance
// ---------------------------------------------------------------------------

const THEME_OPTIONS = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "System" },
] as const;

function AppearanceSection() {
  const { theme, setTheme } = useTheme();

  return (
    <SettingsSection
      label="Appearance"
      title="Theme"
      description="Bond-paper light or its charcoal reverse. System follows your device."
    >
      <div className="space-y-2">
        <p className="text-caption text-muted-foreground font-mono uppercase">Theme</p>
        <div
          role="radiogroup"
          aria-label="Theme"
          className="border-border inline-flex rounded-sm border p-0.5"
        >
          {THEME_OPTIONS.map((option) => {
            // `theme` is undefined until next-themes hydrates; treat that as
            // "no selection yet" so we never highlight the wrong option on
            // first paint. No mount effect needed.
            const active = theme === option.value;
            return (
              <button
                key={option.value}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => setTheme(option.value)}
                className={`ease-out-strong rounded-[3px] px-3.5 py-1.5 font-mono text-[11px] tracking-[0.08em] uppercase transition-colors duration-150 ${
                  active
                    ? "bg-foreground text-background"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>
    </SettingsSection>
  );
}

// ---------------------------------------------------------------------------
// Danger zone
// ---------------------------------------------------------------------------

function DangerZoneSection() {
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  const signOut = async () => {
    setSigningOut(true);
    try {
      await authClient.signOut();
      router.push("/login");
      router.refresh();
    } catch {
      // If sign-out fails the session is still valid; let the user retry.
      setSigningOut(false);
    }
  };

  return (
    <SettingsSection
      label="Account"
      title="Danger zone"
      description="Session and account controls."
    >
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-body-sm text-foreground font-medium">Sign out</p>
          <p className="text-body-sm text-muted-foreground mt-0.5">
            End your session on this device.
          </p>
        </div>
        <button
          type="button"
          onClick={signOut}
          disabled={signingOut}
          className="border-border bg-card hover:bg-foreground/4 hover:border-border/80 text-foreground/90 hover:text-foreground shrink-0 rounded-sm border px-4 py-2 font-mono text-[11px] tracking-[0.08em] uppercase transition-colors duration-150 disabled:opacity-40"
        >
          {signingOut ? "Signing out…" : "Sign out"}
        </button>
      </div>

      <div className="border-destructive/30 border-t pt-6">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="text-body-sm text-foreground font-medium">Delete account</p>
            <p className="text-body-sm text-muted-foreground mt-0.5 leading-relaxed">
              Permanently removes your account and every contract, clause, and file. Coming with
              account management.
            </p>
          </div>
          <button
            type="button"
            disabled
            title="Coming with account management"
            className="border-destructive/40 text-destructive/60 shrink-0 cursor-not-allowed rounded-sm border px-4 py-2 font-mono text-[11px] tracking-[0.08em] uppercase opacity-60"
          >
            Delete
          </button>
        </div>
      </div>
    </SettingsSection>
  );
}

// ---------------------------------------------------------------------------
// Shared
// ---------------------------------------------------------------------------

function SettingsSection({
  label,
  title,
  description,
  children,
}: {
  label: string;
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section className="border-border/40 border-t pt-8">
      <div className="grid gap-6 md:grid-cols-[240px_1fr]">
        <div>
          <p className="text-caption text-muted-foreground font-mono uppercase">{label}</p>
          <h3 className="font-display text-foreground mt-2 text-[17px] font-medium tracking-[-0.01em]">
            {title}
          </h3>
          {description && (
            <p className="text-body-sm text-muted-foreground mt-1.5 max-w-[34ch] leading-relaxed">
              {description}
            </p>
          )}
        </div>
        <div className="max-w-110 space-y-6">{children}</div>
      </div>
    </section>
  );
}

function getInitials(source: string): string {
  const trimmed = source.trim();
  if (!trimmed) return "?";
  const words = trimmed.split(/\s+/);
  if (words.length >= 2) {
    return (words[0][0] + words[words.length - 1][0]).toUpperCase();
  }
  const localPart = trimmed.split("@")[0];
  return localPart.slice(0, 2).toUpperCase();
}
