import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
  const base = siteUrl();
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [
          "/api/",
          "/en/admin",
          "/bn/admin",
          "/en/account",
          "/bn/account",
          "/en/cart",
          "/bn/cart",
          "/en/checkout",
          "/bn/checkout",
        ],
      },
    ],
    sitemap: `${base}/sitemap.xml`,
    host: base,
  };
}
