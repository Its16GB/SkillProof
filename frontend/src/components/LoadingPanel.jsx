import { CircleNotch } from "@phosphor-icons/react";

const STEPS = [
  "Contacting Adzuna",
  "Fetching up to 10 real postings",
  "Cleaning descriptions",
  "Running Groq skills extraction",
  "Aggregating salary, companies, titles",
];

export function LoadingPanel() {
  return (
    <div
      data-testid="analyze-loading"
      className="border border-border p-8 md:p-12"
    >
      <div className="flex items-center gap-3">
        <CircleNotch size={22} className="animate-spin text-primary" />
        <span className="font-display text-2xl">Analyzing live postings…</span>
      </div>
      <div className="mt-8 grid gap-3 md:grid-cols-5">
        {STEPS.map((s, i) => (
          <div
            key={s}
            className="border border-border p-4 text-sm"
            style={{
              animation: `pulse-fade 1.6s ease-in-out ${i * 0.35}s infinite`,
            }}
          >
            <div className="label-mono mb-2">{String(i + 1).padStart(2, "0")}</div>
            <div>{s}</div>
          </div>
        ))}
      </div>
      <style>{`
        @keyframes pulse-fade {
          0%, 100% { opacity: 0.4; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
