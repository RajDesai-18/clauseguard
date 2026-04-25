import Link from "next/link";
import { AuthCard } from "@/components/auth/auth-card";
import { SignupForm } from "@/components/auth/signup-form";

export const metadata = {
  title: "Create an account — ClauseGuard",
  description: "Create your ClauseGuard account.",
};

export default function SignupPage() {
  return (
    <AuthCard
      sectionNumber="006"
      sectionLabel="Sign up"
      heading="Create an account"
      subtitle="Start reviewing contracts in minutes."
      footer={
        <>
          Already have an account?{" "}
          <Link
            href="/login"
            className="text-foreground decoration-foreground/30 hover:decoration-foreground/80 underline underline-offset-4 transition-colors duration-200 [transition-timing-function:var(--ease-out-strong)]"
          >
            Sign in
          </Link>
        </>
      }
    >
      <SignupForm />
    </AuthCard>
  );
}
