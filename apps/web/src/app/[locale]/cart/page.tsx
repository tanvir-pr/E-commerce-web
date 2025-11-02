import { getTranslations, setRequestLocale } from "next-intl/server";
import { Reveal } from "@/components/motion/Reveal";
import { CartPanel } from "@/components/storefront/CartPanel";

export default async function CartPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("cart");
  return (
    <main id="main" className="mx-auto w-full max-w-6xl px-md py-xl">
      <Reveal>
        <h1 className="font-display text-hero text-ink">{t("title")}</h1>
        <p className="mt-sm max-w-xl text-muted">{t("lede")}</p>
      </Reveal>
      <div className="mt-xl">
        <CartPanel />
      </div>
    </main>
  );
}
