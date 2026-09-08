import { useMemo, useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { MagnifyingGlass, Briefcase, MapPin, Timer } from "@phosphor-icons/react";

const YEAR_LABEL = (y) => {
  if (y <= 1) return "Entry-level / Junior";
  if (y <= 3) return "Junior / Associate";
  if (y <= 6) return "Mid-level";
  if (y <= 10) return "Senior";
  return "Lead / Principal";
};

export function SearchForm({ countries, onSubmit, disabled }) {
  const [role, setRole] = useState("");
  const [country, setCountry] = useState("gb");
  const [city, setCity] = useState("");
  const [years, setYears] = useState(3);

  const canSubmit = useMemo(
    () => role.trim().length >= 2 && !!country && !disabled,
    [role, country, disabled]
  );

  const submit = (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    onSubmit({
      role: role.trim(),
      country,
      city: city.trim() || null,
      years_experience: Number(years),
    });
  };

  return (
    <form
      onSubmit={submit}
      data-testid="analyzer-search-form"
      className="border border-border bg-card p-6 md:p-8"
    >
      <div className="label-mono mb-6">Analyze skills demand</div>

      <div className="space-y-5">
        <Field icon={<Briefcase size={16} />} label="Role / Job title">
          <Input
            data-testid="input-role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            placeholder="e.g. Data Scientist, Product Manager"
            className="border-x-0 border-t-0 rounded-none border-b border-border px-0 focus-visible:ring-0 focus-visible:border-primary text-base"
            required
          />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field icon={<MapPin size={16} />} label="Country">
            <Select value={country} onValueChange={setCountry}>
              <SelectTrigger
                data-testid="select-country"
                className="rounded-none border-x-0 border-t-0 border-b border-border px-0 focus:ring-0"
              >
                <SelectValue placeholder="Choose" />
              </SelectTrigger>
              <SelectContent className="max-h-64">
                {countries.map((c) => (
                  <SelectItem key={c.code} value={c.code}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field icon={<MapPin size={16} />} label="City (optional)">
            <Input
              data-testid="input-city"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="Any"
              className="border-x-0 border-t-0 rounded-none border-b border-border px-0 focus-visible:ring-0 focus-visible:border-primary"
            />
          </Field>
        </div>

        <Field icon={<Timer size={16} />} label="Years of experience">
          <div className="pt-1">
            <div className="mb-3 flex items-baseline justify-between">
              <span
                data-testid="years-value"
                className="font-mono text-3xl tracking-tight"
              >
                {years}
                <span className="ml-1 text-sm text-muted-foreground">
                  {years === 1 ? "year" : "years"}
                </span>
              </span>
              <span className="text-xs text-muted-foreground">{YEAR_LABEL(years)}</span>
            </div>
            <Slider
              data-testid="slider-years"
              value={[years]}
              min={0}
              max={20}
              step={1}
              onValueChange={(v) => setYears(v[0])}
            />
            <div className="mt-2 flex justify-between text-[10px] text-muted-foreground font-mono">
              <span>0</span><span>5</span><span>10</span><span>15</span><span>20+</span>
            </div>
          </div>
        </Field>
      </div>

      <Button
        data-testid="analyze-submit-button"
        type="submit"
        disabled={!canSubmit}
        className="mt-8 h-12 w-full rounded-none bg-foreground text-background transition-transform duration-200 ease-out hover:-translate-y-[1px] hover:bg-foreground/90 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <MagnifyingGlass size={18} className="mr-2" weight="bold" />
        {disabled ? "Analyzing 50 postings…" : "Analyze real postings"}
      </Button>

      <p className="mt-4 text-xs text-muted-foreground">
        Uses live Adzuna postings + Groq for skills extraction.
        Analysis takes 15–35 s.
      </p>
    </form>
  );
}

function Field({ icon, label, children }) {
  return (
    <div>
      <label className="mb-2 flex items-center gap-2 text-xs uppercase tracking-[0.15em] text-muted-foreground">
        <span className="text-foreground/60">{icon}</span>
        {label}
      </label>
      {children}
    </div>
  );
}
