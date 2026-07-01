import { headers } from "next/headers";

import { auth } from "@/lib/auth";
import { SettingsView } from "@/components/features/settings-view";

export const metadata = {
  title: "Settings",
};

export default async function SettingsPage() {
  // The (app) layout already gates on session; we read it again here
  // (cached within the request) to seed the profile fields without a
  // client-side loading flash.
  const session = await auth.api.getSession({ headers: await headers() });
  const user = session?.user;

  return (
    <SettingsView
      initialName={user?.name ?? ""}
      email={user?.email ?? ""}
      image={user?.image ?? null}
    />
  );
}
