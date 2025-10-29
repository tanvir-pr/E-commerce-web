import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { HeroArt } from "@/components/storefront/HeroArt";

export async function HomeHero({ locale }: { locale: string }) {
  const t = await getTranslations("storefront");
  return (
    <section className="relative isolate min-h-[100svh] overflow-hidden">
      <HeroArt />
      <div className="relative z-10 mx-auto flex min-h-[100svh] w-full max-w-6xl flex-col justify-end px-md pb-3xl pt-2xl md:justify-center md:pb-2xl">
        <div className="max-w-xl">
          <h1 className="animate-rise-in font-display text-hero text-ink">{t("brand")}</h1>
          <p
            className="animate-rise-in mt-md max-w-lg text-display font-medium text-ink text-balance"
            style={{ animationDelay: "80ms" }}
          >
            {t("heroHeadline")}
          </p>
          <p
            className="animate-rise-in mt-md max-w-md text-base text-muted text-balance"
            style={{ animationDelay: "140ms" }}
          >
            {t("heroSupport")}
          </p>
          <div
            className="animate-rise-in mt-xl flex flex-wrap gap-sm"
            style={{ animationDelay: "200ms" }}
          >
            <Link
              href={`/${locale}/shop`}
              className="btn-press rounded-sm bg-sage px-lg py-sm text-sm font-medium text-white hover:bg-sage-deep"
            >
              {t("ctaShop")}
            </Link>
            <Link
              href={`/${locale}/search`}
              className="btn-press rounded-sm border border-ink/20 bg-surface/70 px-lg py-sm text-sm font-medium text-ink backdrop-blur-sm hover:border-sage"
            >
              {t("ctaSearch")}
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
