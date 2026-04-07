export default function LandingPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6">
      <h1 className="font-display text-5xl font-bold tracking-tight">
        ClauseGuard
      </h1>
      <p className="font-body text-lg text-muted-foreground max-w-md text-center">
        AI-powered contract review for startups and freelancers.
        Upload. Analyze. Negotiate with confidence.
      </p>
      <div className="flex gap-3">
        <span className="inline-flex items-center rounded-full px-3 py-1 text-sm font-medium bg-risk-green/20 text-risk-green">
          Low Risk
        </span>
        <span className="inline-flex items-center rounded-full px-3 py-1 text-sm font-medium bg-risk-yellow/20 text-risk-yellow">
          Medium Risk
        </span>
        <span className="inline-flex items-center rounded-full px-3 py-1 text-sm font-medium bg-risk-red/20 text-risk-red">
          High Risk
        </span>
      </div>
    </main>
  );
}