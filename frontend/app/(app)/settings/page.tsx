import { Settings } from "lucide-react";

export const metadata = {
  title: "Settings",
};

/**
 * STUB (Phase 7): account + preferences.
 *
 * Placeholder route so the rail's Settings item (and the account-menu
 * link) resolve. The real build covers profile (name, photo), account
 * security (change email/password, Google connect/disconnect), the
 * light/dark theme toggle (tokens already exist in globals.css), and a
 * danger zone (delete account, sign out). See Phase 6 handoff.
 */
export default function SettingsPage() {
  return (
    <div className="flex min-h-[55vh] flex-col items-center justify-center px-6 text-center">
      <div className="w-full max-w-[520px]">
        <Settings
          className="text-muted-foreground/50 mx-auto size-7"
          strokeWidth={1.25}
          aria-hidden
        />
        <p className="text-caption text-muted-foreground mt-6 font-mono tracking-[0.14em] uppercase">
          Coming soon
        </p>
        <h2 className="font-display text-heading-lg text-foreground mt-4 font-medium tracking-[-0.02em]">
          Settings &amp; <span className="font-editorial">account</span>
        </h2>
        <p className="text-body text-muted-foreground mx-auto mt-3 max-w-[42ch] leading-relaxed">
          Profile, security, appearance, and account controls will live here. For now, you can
          manage sign-out from the account menu in the top right.
        </p>
      </div>
    </div>
  );
}
