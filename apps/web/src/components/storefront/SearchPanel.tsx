"use client";

import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useTransition,
} from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { formatBdt } from "@/lib/catalog";
import { readRecentlyViewed, type RecentProduct } from "@/lib/recently-viewed";
import {
  buildSearchQuery,
  fetchSearch,
  fetchSuggest,
  type FacetValue,
  type SearchHit,
  type SearchParams,
  type SearchResult,
  type SearchSort,
  type SuggestHit,
} from "@/lib/search";

type Props = {
  locale: string;
  initial: SearchParams;
};

function paramsFromUrl(initial: SearchParams): SearchParams {
  return {
    q: initial.q ?? "",
    concern: initial.concern || undefined,
    ingredient: initial.ingredient || undefined,
    skin_type: initial.skin_type || undefined,
    category: initial.category || undefined,
    min_price_bdt: initial.min_price_bdt || undefined,
    max_price_bdt: initial.max_price_bdt || undefined,
    sort: initial.sort || "relevance",
    offset: initial.offset || 0,
  };
}

export function SearchPanel({ locale, initial }: Props) {
  const t = useTranslations("search");
  const router = useRouter();
  const [params, setParams] = useState<SearchParams>(() => paramsFromUrl(initial));
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [suggestions, setSuggestions] = useState<SuggestHit[]>([]);
  const [showSuggest, setShowSuggest] = useState(false);
  const [recent, setRecent] = useState<RecentProduct[]>([]);
  const suggestTimer = useRef<number | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const load = useCallback(
    (next: SearchParams) => {
      startTransition(() => {
        void (async () => {
          setError(null);
          try {
            const data = await fetchSearch(next);
            setResult(data);
            const qs = buildSearchQuery(next);
            router.replace(`/${locale}/search${qs ? `?${qs}` : ""}`, { scroll: false });
          } catch {
            setError(t("loadFailed"));
          }
        })();
      });
    },
    [locale, router, t],
  );

  useEffect(() => {
    load(paramsFromUrl(initial));
    setRecent(readRecentlyViewed());
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount with URL state only
  }, []);

  useEffect(() => {
    return () => {
      if (suggestTimer.current) {
        window.clearTimeout(suggestTimer.current);
      }
    };
  }, []);

  function update(patch: Partial<SearchParams>, reload = true) {
    setParams((current) => {
      const next = { ...current, ...patch, offset: patch.offset ?? 0 };
      if (reload) {
        load(next);
      }
      return next;
    });
  }

  function onQueryChange(value: string) {
    setParams((current) => ({ ...current, q: value }));
    if (suggestTimer.current) {
      window.clearTimeout(suggestTimer.current);
    }
    suggestTimer.current = window.setTimeout(() => {
      void (async () => {
        const items = await fetchSuggest(value);
        setSuggestions(items);
        setShowSuggest(items.length > 0);
      })();
    }, 180);
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setShowSuggest(false);
    update({ q: params.q ?? "", offset: 0 });
  }

  function toggleFacet(key: "concern" | "ingredient" | "skin_type" | "category", value: string) {
    const current = params[key];
    update({ [key]: current === value ? undefined : value });
  }

  const pageSize = result?.limit ?? 24;
  const canPrev = (params.offset ?? 0) > 0;
  const canNext = result ? (params.offset ?? 0) + pageSize < result.total : false;

  const facetBlocks = useMemo(
    () =>
      [
        { key: "skin_types" as const, param: "skin_type" as const, label: t("facetSkinType") },
        { key: "concerns" as const, param: "concern" as const, label: t("facetConcern") },
        { key: "ingredients" as const, param: "ingredient" as const, label: t("facetIngredient") },
        { key: "category_slug" as const, param: "category" as const, label: t("facetCategory") },
      ] as const,
    [t],
  );

  return (
    <div className="grid gap-xl lg:grid-cols-[16rem_minmax(0,1fr)]">
      <aside className="flex flex-col gap-lg">
        {facetBlocks.map((block) => (
          <FacetGroup
            key={block.key}
            title={block.label}
            values={result?.facets?.[block.key] ?? []}
            selected={params[block.param]}
            onSelect={(value) => toggleFacet(block.param, value)}
          />
        ))}

        <div>
          <h2 className="text-sm font-medium text-ink">{t("priceTitle")}</h2>
          <div className="mt-sm grid grid-cols-2 gap-xs">
            <label className="flex flex-col gap-2xs text-xs text-muted">
              {t("minPrice")}
              <input
                type="number"
                min={0}
                step="1"
                value={params.min_price_bdt ?? ""}
                onChange={(e) =>
                  setParams((current) => ({ ...current, min_price_bdt: e.target.value }))
                }
                className="rounded-sm border border-line bg-surface px-sm py-xs text-sm text-ink"
              />
            </label>
            <label className="flex flex-col gap-2xs text-xs text-muted">
              {t("maxPrice")}
              <input
                type="number"
                min={0}
                step="1"
                value={params.max_price_bdt ?? ""}
                onChange={(e) =>
                  setParams((current) => ({ ...current, max_price_bdt: e.target.value }))
                }
                className="rounded-sm border border-line bg-surface px-sm py-xs text-sm text-ink"
              />
            </label>
          </div>
          <button
            type="button"
            onClick={() =>
              update({
                min_price_bdt: params.min_price_bdt,
                max_price_bdt: params.max_price_bdt,
              })
            }
            className="mt-sm text-sm text-sage underline"
          >
            {t("applyPrice")}
          </button>
        </div>

        <p className="text-xs text-muted">{t("ratingNote")}</p>

        <button
          type="button"
          onClick={() =>
            update({
              q: "",
              concern: undefined,
              ingredient: undefined,
              skin_type: undefined,
              category: undefined,
              min_price_bdt: undefined,
              max_price_bdt: undefined,
              sort: "relevance",
            })
          }
          className="w-fit text-sm text-muted underline"
        >
          {t("clearFilters")}
        </button>
      </aside>

      <div className="min-w-0">
        <form onSubmit={onSubmit} className="relative">
          <label className="flex flex-col gap-xs text-sm">
            <span className="font-medium text-ink">{t("queryLabel")}</span>
            <input
              ref={inputRef}
              type="search"
              value={params.q ?? ""}
              onChange={(e) => onQueryChange(e.target.value)}
              onFocus={() => setShowSuggest(suggestions.length > 0)}
              onBlur={() => window.setTimeout(() => setShowSuggest(false), 120)}
              placeholder={t("queryPlaceholder")}
              className="rounded-sm border border-line bg-surface px-md py-sm text-base text-ink"
              autoComplete="off"
            />
          </label>
          {showSuggest ? (
            <ul className="absolute z-10 mt-xs w-full border border-line bg-surface shadow-sm">
              {suggestions.map((item) => (
                <li key={item.slug}>
                  <Link
                    href={`/${locale}/p/${item.slug}`}
                    className="flex items-baseline justify-between gap-md px-md py-sm text-sm hover:bg-paper"
                    onMouseDown={(e) => e.preventDefault()}
                  >
                    <span>
                      <span className="text-ink">{item.name}</span>
                      {item.category_slug ? (
                        <span className="ml-xs text-xs text-muted">{item.category_slug}</span>
                      ) : null}
                    </span>
                    <span className="text-muted">{formatBdt(item.from_price_poisha)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : null}
          <div className="mt-sm flex flex-wrap items-center gap-sm">
            <button
              type="submit"
              className="btn-press rounded-sm bg-sage px-md py-sm text-sm font-medium text-white hover:bg-sage-deep"
            >
              {t("search")}
            </button>
            <label className="flex items-center gap-xs text-sm text-muted">
              <span>{t("sort")}</span>
              <select
                value={params.sort ?? "relevance"}
                onChange={(e) => update({ sort: e.target.value as SearchSort })}
                className="rounded-sm border border-line bg-surface px-sm py-xs text-ink"
              >
                <option value="relevance">{t("sortRelevance")}</option>
                <option value="name_asc">{t("sortNameAsc")}</option>
                <option value="name_desc">{t("sortNameDesc")}</option>
                <option value="price_asc">{t("sortPriceAsc")}</option>
                <option value="price_desc">{t("sortPriceDesc")}</option>
              </select>
            </label>
            {pending ? <span className="text-xs text-muted">{t("searching")}</span> : null}
          </div>
        </form>

        {error ? (
          <p role="alert" className="mt-md text-sm text-danger">
            {error}
          </p>
        ) : null}

        <p className="mt-md text-sm text-muted">
          {result ? t("resultsCount", { count: result.total }) : t("searching")}
        </p>

        <ul className="mt-md divide-y divide-line border-t border-line">
          {(result?.items ?? []).map((hit) => (
            <SearchHitRow key={hit.id} hit={hit} locale={locale} />
          ))}
        </ul>

        {result && result.items.length === 0 ? (
          <p className="mt-md text-sm text-muted">{t("empty")}</p>
        ) : null}

        {result && result.total > pageSize ? (
          <div className="mt-lg flex gap-sm">
            <button
              type="button"
              disabled={!canPrev || pending}
              onClick={() =>
                update({ offset: Math.max(0, (params.offset ?? 0) - pageSize) })
              }
              className="rounded-sm border border-line px-md py-xs text-sm disabled:opacity-50"
            >
              {t("prev")}
            </button>
            <button
              type="button"
              disabled={!canNext || pending}
              onClick={() => update({ offset: (params.offset ?? 0) + pageSize })}
              className="rounded-sm border border-line px-md py-xs text-sm disabled:opacity-50"
            >
              {t("next")}
            </button>
          </div>
        ) : null}

        {recent.length > 0 ? (
          <section className="mt-3xl border-t border-line pt-xl">
            <h2 className="font-display text-2xl text-ink">{t("recentTitle")}</h2>
            <ul className="mt-md divide-y divide-line">
              {recent.map((item) => (
                <li key={item.slug}>
                  <Link
                    href={`/${locale}/p/${item.slug}`}
                    className="flex items-baseline justify-between gap-md py-sm text-sm hover:border-sage"
                  >
                    <span className="text-ink">{item.name}</span>
                    <span className="text-muted">{formatBdt(item.from_price_poisha)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>
    </div>
  );
}

function FacetGroup({
  title,
  values,
  selected,
  onSelect,
}: {
  title: string;
  values: FacetValue[];
  selected?: string;
  onSelect: (value: string) => void;
}) {
  if (values.length === 0) {
    return null;
  }
  return (
    <div>
      <h2 className="text-sm font-medium text-ink">{title}</h2>
      <ul className="mt-sm flex flex-col gap-xs">
        {values.map((row) => {
          const active = selected === row.value;
          return (
            <li key={row.value}>
              <button
                type="button"
                onClick={() => onSelect(row.value)}
                className={
                  active
                    ? "text-left text-sm text-sage-deep underline"
                    : "text-left text-sm text-muted hover:text-ink"
                }
              >
                {row.value}
                <span className="ml-xs text-xs text-muted">({row.count})</span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function SearchHitRow({ hit, locale }: { hit: SearchHit; locale: string }) {
  return (
    <li>
      <Link
        href={`/${locale}/p/${hit.slug}`}
        className="group flex flex-col gap-2xs py-md sm:flex-row sm:items-baseline sm:justify-between"
      >
        <div>
          <p className="font-display text-xl text-ink group-hover:text-sage-deep">{hit.name}</p>
          {hit.subtitle ? <p className="text-sm text-muted">{hit.subtitle}</p> : null}
          <p className="mt-2xs text-xs uppercase tracking-wide text-muted">
            {[hit.category_slug, hit.routine_step, ...hit.concerns.slice(0, 2)]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>
        <p className="shrink-0 text-sm font-medium text-ink">
          {formatBdt(hit.from_price_poisha)}
        </p>
      </Link>
    </li>
  );
}
