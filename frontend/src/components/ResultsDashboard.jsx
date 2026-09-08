import { useEffect, useMemo } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from "recharts";
import {
  Buildings,
  Certificate,
  Code,
  Handshake,
  Toolbox,
  Sparkle,
  ArrowUpRight,
  CurrencyDollar,
} from "@phosphor-icons/react";
import { capture } from "@/lib/analytics";

const CATEGORIES = [
  { key: "technical", label: "Technical", icon: Code },
  { key: "tools", label: "Tools & Platforms", icon: Toolbox },
  { key: "soft", label: "Soft Skills", icon: Handshake },
  { key: "certification", label: "Certifications", icon: Certificate },
];

const CURRENCY = {
  gb: "£", us: "$", ca: "$", au: "$", nz: "$", in: "₹", sg: "S$",
  de: "€", fr: "€", it: "€", es: "€", nl: "€", be: "€", at: "€", pl: "zł",
  ch: "CHF ", br: "R$", mx: "$", za: "R",
};

const fmtSalary = (v, code) => {
  if (v == null) return "—";
  const c = CURRENCY[code] || "";
  return `${c}${Math.round(v).toLocaleString()}`;
};

const formatAge = (seconds) => {
  if (!seconds || seconds < 60) return `${seconds || 0}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
};

export function ResultsDashboard({ data }) {
  const cur = data.query.country;

  useEffect(() => {
    capture("results_viewed", {
      country: data.query.country,
      cached: Boolean(data.cached),
      postings_analyzed: data.postings_analyzed,
    });
  }, [data]);

  const skillsByCat = useMemo(() => {
    const g = {};
    data.skills.forEach((s) => {
      (g[s.category] = g[s.category] || []).push(s);
    });
    return g;
  }, [data.skills]);

  const topChart = data.skills.slice(0, 12).map((s) => ({
    name: s.name,
    count: s.count,
    pct: s.percentage,
  }));

  return (
    <div data-testid="results-dashboard" className="space-y-10">
      {/* Proof headline */}
      <div className="grid gap-0 border border-border md:grid-cols-12">
        <div className="border-b border-border p-6 md:col-span-4 md:border-b-0 md:border-r md:p-8">
          <div className="flex items-center justify-between">
            <div className="label-mono">Postings analyzed</div>
            {data.cached && (
              <span
                data-testid="cache-badge"
                title={`Served from cache, ${formatAge(data.cache_age_seconds)} old`}
                className="inline-flex items-center gap-1.5 border border-emerald-500/50 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-mono uppercase tracking-widest text-emerald-700"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                Cached · {formatAge(data.cache_age_seconds)}
              </span>
            )}
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span
              data-testid="postings-count"
              className="font-mono text-6xl leading-none tracking-tight"
            >
              {data.postings_analyzed}
            </span>
            <span className="text-muted-foreground">/ 10 target</span>
          </div>
          <p className="mt-4 text-sm text-muted-foreground">
            Real, live postings pulled from Adzuna for{" "}
            <span className="font-mono text-foreground">{data.query.role}</span>
            {data.query.city ? (
              <> in <span className="font-mono text-foreground">{data.query.city}</span></>
            ) : null}{" "}
            · <span className="uppercase font-mono">{data.query.country}</span>
          </p>
        </div>
        <Stat label="Seniority" value={data.seniority_label} sub={`${data.query.years_experience} yrs`} />
        <Stat
          label="Skills extracted"
          value={`Top ${data.skills.length}`}
          sub={`+ ${data.ai_suggested_skills.length} AI-suggested`}
        />
        <Stat
          label="Avg salary"
          value={
            data.salary?.available
              ? fmtSalary((data.salary.avg_min + data.salary.avg_max) / 2 || data.salary.avg, cur)
              : "—"
          }
          sub={
            data.salary?.available
              ? `${fmtSalary(data.salary.min, cur)} – ${fmtSalary(data.salary.max, cur)}`
              : "Not reported"
          }
        />
      </div>

      {/* Top skills chart */}
      <div className="hidden border border-border p-6 md:block md:p-8">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="label-mono">Skill frequency</div>
            <h2 className="mt-2 font-display text-2xl md:text-3xl">
              Top 12 skills across {data.postings_analyzed} postings
            </h2>
          </div>
          <span className="text-xs text-muted-foreground font-mono">
            X&nbsp;=&nbsp;# postings mentioning skill
          </span>
        </div>
        <div className="h-[420px] w-full">
          <ResponsiveContainer>
            <BarChart data={topChart} layout="vertical" margin={{ left: 20, right: 40 }}>
              <XAxis type="number" stroke="hsl(var(--muted-foreground))" fontSize={11} />
              <YAxis
                dataKey="name"
                type="category"
                stroke="hsl(var(--muted-foreground))"
                width={140}
                fontSize={12}
              />
              <Tooltip
                cursor={{ fill: "hsl(var(--muted))" }}
                contentStyle={{
                  background: "hsl(var(--background))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: 0,
                  fontFamily: "var(--font-mono)",
                  fontSize: 12,
                }}
                formatter={(v, _n, p) => [`${v} postings (${p.payload.pct}%)`, "Frequency"]}
              />
              <Bar dataKey="count" radius={0}>
                {topChart.map((_, i) => (
                  <Cell key={i} fill="hsl(220 100% 50%)" />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Skills grouped by category */}
      <div className="grid gap-6 lg:grid-cols-2">
        {CATEGORIES.map(({ key, label, icon: Icon }) => {
          const items = skillsByCat[key] || [];
          if (!items.length) return null;
          return (
            <div key={key} className="border border-border p-6 md:p-8">
              <div className="mb-5 flex items-center gap-3">
                <Icon size={20} className="text-primary" />
                <h3 className="font-display text-xl">{label}</h3>
                <span className="ml-auto font-mono text-xs text-muted-foreground">
                  {items.length} skills
                </span>
              </div>
              <ul className="space-y-3" data-testid={`skills-${key}`}>
                {items.map((s) => (
                  <SkillRow key={s.name} skill={s} total={data.postings_analyzed} />
                ))}
              </ul>
            </div>
          );
        })}
      </div>

      {/* AI Suggested */}
      {data.ai_suggested_skills.length > 0 && (
        <div className="border border-primary/40 bg-primary/[0.03] p-6 md:p-8">
          <div className="mb-5 flex items-center gap-3">
            <Sparkle size={20} weight="fill" className="text-primary" />
            <h3 className="font-display text-xl">
              AI-suggested gap skills for {data.query.years_experience} yrs experience
            </h3>
          </div>
          <p className="mb-5 max-w-2xl text-sm text-muted-foreground">
            These are under-represented in the current postings but Groq
            Sonnet 4.6 believes a strong {data.seniority_label.toLowerCase()}{" "}
            candidate should have them.
          </p>
          <div className="flex flex-wrap gap-2" data-testid="ai-suggested-skills">
            {data.ai_suggested_skills.map((s) => (
              <span
                key={s.name}
                className="inline-flex items-center gap-2 border border-primary/60 px-3 py-1.5 text-sm text-primary"
              >
                <Sparkle size={12} weight="fill" />
                {s.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Companies + Titles */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="border border-border p-6 md:p-8">
          <div className="mb-4 flex items-center gap-3">
            <Buildings size={20} className="text-primary" />
            <h3 className="font-display text-xl">Top hiring companies</h3>
          </div>
          <ol className="space-y-2" data-testid="top-companies">
            {data.top_companies.map((c, i) => (
              <li
                key={c.name}
                className="flex items-center justify-between border-b border-border py-2 text-sm last:border-b-0"
              >
                <span className="flex items-center gap-3">
                  <span className="font-mono text-xs text-muted-foreground">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  {c.name}
                </span>
                <span className="font-mono text-xs">{c.count} postings</span>
              </li>
            ))}
          </ol>
        </div>

        <div className="border border-border p-6 md:p-8">
          <div className="mb-4 flex items-center gap-3">
            <Code size={20} className="text-primary" />
            <h3 className="font-display text-xl">Common job titles</h3>
          </div>
          <ol className="space-y-2" data-testid="top-titles">
            {data.top_titles.map((t, i) => (
              <li
                key={t.name}
                className="flex items-center justify-between border-b border-border py-2 text-sm last:border-b-0"
              >
                <span className="flex items-center gap-3">
                  <span className="font-mono text-xs text-muted-foreground">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  {t.name}
                </span>
                <span className="font-mono text-xs">×{t.count}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>

      {/* Proof: sample postings */}
      <div className="border border-border p-6 md:p-8">
        <div className="mb-5 flex items-center gap-3">
          <CurrencyDollar size={20} className="text-primary" />
          <h3 className="font-display text-xl">Evidence — real postings analyzed</h3>
        </div>
        <div className="grid gap-4 md:grid-cols-2" data-testid="sample-postings">
          {data.samples.map((s, i) => (
            <a
              key={i}
              data-testid={`posting-${i}`}
              href={s.url}
              target="_blank"
              rel="noreferrer"
              onClick={() =>
                capture("source_posting_clicked", {
                  country: data.query.country,
                  position: i + 1,
                })
              }
              className="group flex flex-col justify-between border border-border p-4 transition-transform duration-200 ease-out hover:-translate-y-[1px] hover:border-primary"
            >
              <div>
                <div className="mb-2 flex items-start justify-between gap-3">
                  <span className="line-clamp-2 text-sm font-semibold group-hover:text-primary">
                    {s.title}
                  </span>
                  <ArrowUpRight size={16} className="mt-0.5 shrink-0 text-muted-foreground group-hover:text-primary" />
                </div>
                <div className="label-mono">{s.company}</div>
              </div>
              <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
                <span>{s.location}</span>
                {s.salary_min ? (
                  <span className="font-mono">
                    {fmtSalary(s.salary_min, cur)}–{fmtSalary(s.salary_max, cur)}
                  </span>
                ) : (
                  <span>Salary undisclosed</span>
                )}
              </div>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, sub }) {
  return (
    <div className="border-b border-border p-6 md:col-span-2 md:border-b-0 md:border-r md:p-8 last:md:border-r-0">
      <div className="label-mono">{label}</div>
      <div className="mt-3 font-mono text-2xl md:text-3xl">{value}</div>
      {sub && <div className="mt-1 text-xs text-muted-foreground">{sub}</div>}
    </div>
  );
}

function SkillRow({ skill, total }) {
  const pct = Math.min(100, skill.percentage);
  return (
    <li>
      <div className="mb-1 flex items-baseline justify-between text-sm">
        <span className="font-medium">{skill.name}</span>
        <span className="font-mono text-xs text-muted-foreground">
          {skill.count}/{total} · {pct}%
        </span>
      </div>
      <div className="h-2 w-full bg-muted">
        <div
          className="h-full bg-primary transition-[width] duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </li>
  );
}
