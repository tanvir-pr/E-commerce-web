import { routing, type AppLocale } from "@/i18n/routing";

/** Public origin for canonical, OG, sitemap (browser-facing). */
export function siteUrl(): string {
  const raw =
    process.env.PUBLIC_WEB_URL ||
    process.env.NEXT_PUBLIC_SITE_URL ||
    "http://localhost:3001";
  return raw.replace(/\/$/, "");
}

export function localePath(locale: string, path = ""): string {
  const clean = path.startsWith("/") ? path : path ? `/${path}` : "";
  return `/${locale}${clean}`;
}

export function absoluteUrl(locale: string, path = ""): string {
  return `${siteUrl()}${localePath(locale, path)}`;
}

/** Turn API-relative media paths into absolute URLs via the public site proxy. */
export function absoluteAssetUrl(path: string | null | undefined): string | undefined {
  if (!path) {
    return undefined;
  }
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${siteUrl()}${normalized}`;
}

export function languageAlternates(path = ""): Record<string, string> {
  const languages: Record<string, string> = {};
  for (const locale of routing.locales) {
    languages[locale] = absoluteUrl(locale, path);
  }
  languages["x-default"] = absoluteUrl(routing.defaultLocale, path);
  return languages;
}

export function isAppLocale(value: string): value is AppLocale {
  return (routing.locales as readonly string[]).includes(value);
}
