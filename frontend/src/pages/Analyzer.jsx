import { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { SearchForm } from "@/components/SearchForm";
import { ResultsDashboard } from "@/components/ResultsDashboard";
import { LoadingPanel } from "@/components/LoadingPanel";
import { Sparkle, GlobeHemisphereWest, ArrowRight } from "@phosphor-icons/react";
import { capture, experienceBand } from "@/lib/analytics";

const API = `${process.env.REACT_APP_BACKEND_URL || "http://localhost:8000"}/api`;

export default function Analyzer() {
  const [countries, setCountries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios
      .get(`${API}/countries`)
      .then((r) => setCountries(r.data))
      .catch(() => {
        capture("country_list_failed");
        toast.error("Could not load country list. Try refreshing.");
      });
  }, []);

  const runAnalysis = async (payload) => {
    const startedAt = performance.now();
    const eventContext = {
      country: payload.country,
      experience_band: experienceBand(payload.years_experience),
      has_city: Boolean(payload.city),
    };

    capture("analysis_started", eventContext);
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const { data } = await axios.post(`${API}/analyze`, payload, {
        timeout: 120000,
      });
      setResult(data);
      capture("analysis_completed", {
        ...eventContext,
        cached: Boolean(data.cached),
        duration_ms: Math.round(performance.now() - startedAt),
        postings_analyzed: data.postings_analyzed,
        skills_extracted: data.skills.length,
      });
      toast.success(`Analyzed ${data.postings_analyzed} live postings.`);
      setTimeout(() => {
        document
          .getElementById("results")
          ?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
    } catch (e) {
      const msg =
        e.response?.data?.detail ||
        e.message ||
        "Something went wrong. Please try again.";
      capture("analysis_failed", {
        ...eventContext,
        duration_ms: Math.round(performance.now() - startedAt),
        http_status: e.response?.status || null,
      });
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen">
      {/* Top bar */}
      <header className="sticky top-0 z-40 border-b border-border bg-background/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-6 py-4 md:px-10">
          <div className="flex items-center gap-3">
            <div className="grid h-9 w-9 place-items-center border border-foreground bg-foreground text-background">
              <Sparkle size={18} weight="fill" />
            </div>
            <div className="flex flex-col leading-tight">
              <span className="font-display text-lg">SkillProof</span>
              <span className="label-mono">Job-Posting Evidence</span>
            </div>
          </div>
          <a
            data-testid="github-source-link"
            href="https://github.com/Its16GB/SkillProof"
            target="_blank"
            rel="noreferrer"
            onClick={() => capture("github_source_clicked")}
            className="hidden items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground md:flex"
          >
            <GlobeHemisphereWest size={16} />
            Open source · Deployable
          </a>
        </div>
      </header>

      {/* Hero */}
      <section className="border-b border-border">
        <div className="mx-auto grid max-w-[1400px] gap-10 px-6 py-14 md:grid-cols-12 md:px-10 md:py-24">
          <div className="md:col-span-7">
            <div className="label-mono mb-6 flex items-center gap-3">
              <span className="h-px w-8 bg-foreground/60" />
              Skills-gap analysis · powered by real postings
            </div>
            <h1 className="font-display text-4xl leading-[1.05] sm:text-5xl lg:text-6xl">
              Know exactly what skills to<br />
              <span className="text-primary">put on your CV</span> for the role
              you want &mdash; anywhere in the world.
            </h1>
            <p className="mt-6 max-w-xl text-base leading-relaxed text-muted-foreground">
              Pull up to <span className="font-mono text-foreground">50 live job
              postings</span> from Adzuna, then let Claude extract
              the exact skills, tools and certifications employers actually ask
              for &mdash; ranked by how many postings mention them.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3 text-sm">
              <span className="flex items-center gap-2 text-muted-foreground">
                <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                Real Adzuna postings as evidence
              </span>
              <span className="flex items-center gap-2 text-muted-foreground">
                <span className="h-1.5 w-1.5 rounded-full bg-foreground" />
                AI-suggested gap skills
              </span>
              <span className="flex items-center gap-2 text-muted-foreground">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                Salary + top hiring companies
              </span>
            </div>
          </div>

          <div className="md:col-span-5">
            <SearchForm
              countries={countries}
              onSubmit={runAnalysis}
              disabled={loading}
            />
          </div>
        </div>
      </section>

      {/* Loading / Error / Results */}
      <section id="results" className="mx-auto max-w-[1400px] px-6 py-12 md:px-10 md:py-20">
        {loading && <LoadingPanel />}

        {!loading && error && (
          <div
            data-testid="analyze-error"
            className="border border-destructive/40 bg-destructive/5 p-8"
          >
            <div className="label-mono mb-2 text-destructive">Analysis failed</div>
            <p className="text-base">{error}</p>
            <p className="mt-3 text-sm text-muted-foreground">
              Tip: try a broader role (e.g. &ldquo;Software Engineer&rdquo; instead of a very
              specific title), remove the city, or select a country with more
              activity like US, UK or India.
            </p>
          </div>
        )}

        {!loading && !error && result && <ResultsDashboard data={result} />}

        {!loading && !error && !result && (
          <div className="border border-border p-10 text-center md:p-16">
            <div className="label-mono mb-4">Ready when you are</div>
            <h2 className="font-display text-2xl sm:text-3xl">
              Pick a role, place and experience level
            </h2>
            <p className="mx-auto mt-3 max-w-lg text-sm text-muted-foreground">
              You&apos;ll get skill frequencies, an AI-suggested gap list, salary
              range, top hiring companies and the exact postings the analysis
              is based on.
            </p>
            <div className="mt-6 inline-flex items-center gap-2 border border-foreground px-4 py-2 text-sm">
              Try &ldquo;Data Scientist&rdquo; in India&nbsp;
              <ArrowRight size={14} />
            </div>
          </div>
        )}
      </section>

      <footer className="border-t border-border py-8">
        <div className="mx-auto flex max-w-[1400px] flex-col items-start justify-between gap-2 px-6 text-sm text-muted-foreground md:flex-row md:items-center md:px-10">
          <span>
            SkillProof · Powered by{" "}
            <a
              className="underline underline-offset-2 hover:text-foreground"
              href="https://developer.adzuna.com/"
              target="_blank"
              rel="noreferrer"
            >
              Adzuna
            </a>{" "}
            &amp; Claude
          </span>
          <span className="label-mono">Open Source · MIT</span>
        </div>
      </footer>
    </div>
  );
}
