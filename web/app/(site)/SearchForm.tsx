// The first screen's search form: a GET form to /results (works without JavaScript; next/form
// adds client-side navigation). Choices are native radio buttons drawn as buttons.
import Form from "next/form";
import { formatDollars } from "@/lib/rent";
import { BUDGET_EXAMPLE, BUDGET_STEP, MAX_COMMUTE_MIN, SEARCH_SIZES } from "@/lib/search";
import { strings } from "@/lib/strings";

const t = strings.form;

interface Option {
  value: string;
  label: string;
}

/** A required single choice, nothing preselected: a fieldset of radios drawn as 48 px buttons. */
function Choice({
  name,
  legend,
  hint,
  options,
  columns,
}: {
  name: string;
  legend: string;
  hint?: string;
  options: Option[];
  columns: string;
}) {
  const hintId = hint ? `${name}-hint` : undefined;
  return (
    <fieldset aria-describedby={hintId}>
      <legend className="font-semibold">{legend}</legend>
      {hint && (
        <p id={hintId} className="mt-1 text-sm text-ink-muted">
          {hint}
        </p>
      )}
      <div className={`mt-3 grid gap-2 ${columns}`}>
        {options.map((o) => (
          <label key={o.value} className="relative">
            <input
              type="radio"
              name={name}
              value={o.value}
              required
              className="peer sr-only"
            />
            <span className="flex min-h-12 cursor-pointer items-center justify-center rounded-control border border-control bg-surface px-2 text-center leading-tight text-balance transition-colors duration-150 ease-out select-none peer-checked:border-ink peer-checked:bg-ink peer-checked:font-semibold peer-checked:text-white peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-focus hover:bg-hover active:bg-hover peer-checked:hover:bg-ink-hover peer-checked:active:bg-ink-hover">
              {o.label}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export default function SearchForm({
  campuses,
  departure,
}: {
  campuses: Option[];
  departure: { start: string; end: string };
}) {
  return (
    <Form action="/results" className="mt-8 flex flex-col gap-8">
      <Choice name="campus" legend={t.campus.legend} options={campuses} columns="grid-cols-3" />
      <Choice
        name="size"
        legend={t.size.legend}
        hint={t.size.hint}
        options={SEARCH_SIZES.map((s) => ({ value: s, label: t.size.labels[s] }))}
        columns="grid-cols-4"
      />
      <div>
        <label htmlFor="budget" className="font-semibold">
          {t.budget.label} <span className="font-normal text-ink-muted">({t.budget.optional})</span>
        </label>
        <p id="budget-hint" className="mt-1 text-sm text-ink-muted">
          {t.budget.hint(formatDollars(BUDGET_EXAMPLE))}
        </p>
        <div className="mt-3 flex h-12 w-44 items-center rounded-control border border-control bg-surface focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-focus">
          <span aria-hidden="true" className="pl-3 text-ink-muted">
            {t.budget.prefix}
          </span>
          <input
            id="budget"
            name="budget"
            type="number"
            inputMode="numeric"
            min={BUDGET_STEP}
            step={BUDGET_STEP}
            aria-describedby="budget-hint"
            className="h-full w-full min-w-0 bg-transparent px-2 outline-none"
          />
        </div>
      </div>
      <Choice
        name="max"
        legend={t.maxCommute.legend}
        hint={t.maxCommute.hint(departure.start, departure.end)}
        options={MAX_COMMUTE_MIN.map((m) => ({ value: String(m), label: t.maxCommute.option(m) }))}
        columns="grid-cols-4"
      />
      <button
        type="submit"
        className="h-12 cursor-pointer rounded-control bg-ink px-6 font-semibold text-white transition-colors duration-150 ease-out hover:bg-ink-hover active:bg-ink-hover sm:self-start"
      >
        {strings.home.submit}
      </button>
    </Form>
  );
}
