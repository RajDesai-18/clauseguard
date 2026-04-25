import Link from "next/link";
import { AuthCard } from "@/components/auth/auth-card";
import { LoginForm } from "@/components/auth/login-form";

export const metadata = {
  title: "Sign in — ClauseGuard",
  description: "Sign in to your ClauseGuard account.",
};

export default function LoginPage() {
  return (
    <AuthCard
      sectionNumber="005"
      sectionLabel="Sign in"
      heading="Sign in"
      subtitle="Sign in to continue to your dashboard."
      footer={
        <>
          Don&apos;t have an account?{" "}
          <Link
            href="/signup"
            className="text-foreground decoration-foreground/30 hover:decoration-foreground/80 underline underline-offset-4 transition-colors duration-200 [transition-timing-function:var(--ease-out-strong)]"
          >
            Sign up
          </Link>
        </>
      }
    >
      <LoginForm />
    </AuthCard>
  );
}
