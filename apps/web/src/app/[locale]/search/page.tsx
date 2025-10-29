import { getTranslations, setRequestLocale } from "next-intl/server";
import { Reveal } from "@/components/motion/Reveal";
import { SearchPanel } from "@/components/storefront/SearchPanel";
import type { SearchSort } from "@/lib/search";

type SearchParamsBag = {
  q?: string;
  concern?: string;
  ingredient?: string;
  skin_type?: string;
  category?: string;
  min_price_poisha?: string;
  max_price_poisha?: string;
  sort?: string;
  offset?: string;
};

function poishaToBdtInput(raw?: string): string | undefined {
  if (!raw) {
    return undefined;
  }
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n)) {
    return undefined;
  }
  return (n / 100).toFixed(n % 100 === 0 ? 0 : 2);
}

export default async function SearchPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<SearchParamsBag>;
}) {
  const { locale } = await params;
  const query = await searchParams;
  setRequestLocale(locale);
  const t = await getTranslations("search");

  const sort = (
    ["relevance", "name_asc", "name_desc", "price_asc", "price_desc"] as SearchSort[]
  ).includes(query.sort as SearchSort)
    ? (query.sort as SearchSort)
    : "relevance";

  return (
    <main id="main" className="mx-auto w-full max-w-6xl px-md py-xl">
      <Reveal>
        <h1 className="font-display text-hero text-ink">{t("title")}</h1>
        <p className="mt-sm max-w-xl text-muted">{t("lede")}</p>
      </Reveal>
      <div className="mt-xl">
        <SearchPanel
          locale={locale}
          initial={{
            q: query.q ?? "",
            concern: query.concern,
            ingredient: query.ingredient,
            skin_type: query.skin_type,
            category: query.category,
            min_price_bdt: poishaToBdtInput(query.min_price_poisha),
            max_price_bdt: poishaToBdtInput(query.max_price_poisha),
            sort,
            offset: query.offset ? Number.parseInt(query.offset, 10) || 0 : 0,
          }}
        />
      </div>
    </main>
  );
}
