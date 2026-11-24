// The first screen's search form: a GET form to /results (works without JavaScript; next/form
// adds client-side navigation). Choices are native radio buttons drawn as buttons. On the first
// screen nothing is preselected; on the results page it starts from the current search.
import Form from "next/form";
import { BUDGET_EXAMPLE, MAX_COMMUTE_MIN, SEARCH_SIZES, type Search } from "@/lib/search";
import type { SortKey } from "@/lib/shortlist";
import { strings } from "@/lib/strings";

const t = strings.form;

interface Option {
  value: string;
  label: string;
}

/** A required single choice: a fieldset of radios drawn as 48 px buttons. */
function Choice({
  name,
  legend,
  hint,
  options,
  columns,
  checked,
}: {
  name: string;
  legend: string;
  hint?: string;
  options: Option[];
  columns: string;
  checked?: string;
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
              defaultChecked={o.value === checked}
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
  initial,
  sort = "commute",
  submitLabel = strings.home.submit,
  className = "mt-8",
}: {
  campuses: Option[];
  departure: { start: string; end: string };
  initial?: Search;
  /** Kept when the search changes from the results page. */
  sort?: SortKey;
  submitLabel?: string;
  className?: string;
}) {
  return (
    <Form action="/results" className={`flex flex-col gap-8 ${className}`}>
      {sort !== "commute" && <input type="hidden" name="sort" value={sort} />}
      <Choice
        name="campus"
        legend={t.campus.legend}
        options={campuses}
        columns="grid-cols-3"
        checked={initial?.campus}
      />
      <Choice
        name="size"
        legend={t.size.legend}
        hint={t.size.hint}
        options={SEARCH_SIZES.map((s) => ({ value: s, label: t.size.labels[s] }))}
        columns="grid-cols-4"
        checked={initial?.size}
      />
      <div>
        <label htmlFor="budget" className="font-semibold">
          {t.budget.label} <span className="font-normal text-ink-muted">({t.budget.optional})</span>
        </label>
        <p id="budget-hint" className="mt-1 text-sm text-ink-muted">
          {t.budget.hint(strings.format.dollars(BUDGET_EXAMPLE))}
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
            min={1}
            step={1}
            defaultValue={initial?.budget ?? undefined}
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
        checked={initial ? String(initial.maxCommute) : undefined}
      />
      <button
        type="submit"
        className="h-12 cursor-pointer rounded-control bg-ink px-6 font-semibold text-white transition-colors duration-150 ease-out hover:bg-ink-hover active:bg-ink-hover sm:self-start"
      >
        {submitLabel}
      </button>
    </Form>
  );
}
