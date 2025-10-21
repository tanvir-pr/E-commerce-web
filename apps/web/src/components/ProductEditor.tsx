"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { fetchMe, isStaff, type Me } from "@/lib/api";
import {
  addVariant,
  bdtToPoisha,
  createProduct,
  deleteProduct,
  deleteProductImage,
  deleteVariant,
  fetchAdminAttributes,
  fetchAdminCategories,
  fetchAdminProduct,
  flattenCategories,
  patchProduct,
  patchVariant,
  poishaToBdtInput,
  receiveStock,
  slugify,
  uploadProductImage,
  type Attribute,
  type CategoryNode,
  type ProductDetail,
  type ProductStatus,
  type RoutineStep,
  type Variant,
} from "@/lib/catalog-admin";

type Props = {
  productId?: string;
};

type VariantDraft = {
  sku: string;
  size_label: string;
  shade_name: string;
  shade_hex: string;
  spf: string;
  price_bdt: string;
  weight_grams: string;
};

const EMPTY_VARIANT: VariantDraft = {
  sku: "",
  size_label: "",
  shade_name: "",
  shade_hex: "",
  spf: "",
  price_bdt: "",
  weight_grams: "",
};

export function ProductEditor({ productId }: Props) {
  const t = useTranslations("adminCatalog");
  const ta = useTranslations("admin");
  const locale = useLocale();
  const router = useRouter();
  const isNew = !productId;

  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [categories, setCategories] = useState<CategoryNode[]>([]);
  const [attributes, setAttributes] = useState<Attribute[]>([]);
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [loading, setLoading] = useState(true);

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [subtitle, setSubtitle] = useState("");
  const [description, setDescription] = useState("");
  const [howToUse, setHowToUse] = useState("");
  const [ingredients, setIngredients] = useState("");
  const [warnings, setWarnings] = useState("");
  const [routineStep, setRoutineStep] = useState<"" | RoutineStep>("");
  const [paoMonths, setPaoMonths] = useState("");
  const [shelfLife, setShelfLife] = useState("");
  const [status, setStatus] = useState<ProductStatus>("draft");
  const [attributeIds, setAttributeIds] = useState<string[]>([]);
  const [createVariant, setCreateVariant] = useState<VariantDraft>({ ...EMPTY_VARIANT });
  const [newVariant, setNewVariant] = useState<VariantDraft>({ ...EMPTY_VARIANT });
  const [imageSlot, setImageSlot] = useState("product");
  const [imageAlt, setImageAlt] = useState("");
  const [receiptQty, setReceiptQty] = useState("10");
  const [receiptVariantId, setReceiptVariantId] = useState("");

  const flatCategories = useMemo(() => flattenCategories(categories), [categories]);
  const canWarehouse =
    Boolean(me?.roles.includes("super_admin")) ||
    Boolean(me?.permissions.includes("warehouse"));

  const applyProduct = useCallback((row: ProductDetail) => {
    setProduct(row);
    setName(row.name);
    setSlug(row.slug);
    setCategoryId(row.category_id);
    setSubtitle(row.subtitle ?? "");
    setDescription(row.description ?? "");
    setHowToUse(row.how_to_use ?? "");
    setIngredients(row.ingredients_text ?? "");
    setWarnings(row.warnings ?? "");
    setRoutineStep((row.routine_step as RoutineStep | null) ?? "");
    setPaoMonths(row.pao_months != null ? String(row.pao_months) : "");
    setShelfLife(row.shelf_life_months != null ? String(row.shelf_life_months) : "");
    setStatus(row.status);
    setAttributeIds(row.attributes.map((a) => a.id));
    if (row.variants[0]) {
      setReceiptVariantId(row.variants[0].id);
    }
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      const current = await fetchMe();
      if (!active) {
        return;
      }
      setMe(current);
      if (!isStaff(current)) {
        setError(ta("forbidden"));
        setLoading(false);
        return;
      }
      try {
        const [cats, attrs] = await Promise.all([
          fetchAdminCategories(),
          fetchAdminAttributes(),
        ]);
        if (!active) {
          return;
        }
        setCategories(cats);
        setAttributes(attrs);
        const flat = flattenCategories(cats);
        if (isNew) {
          if (flat[0]) {
            setCategoryId(flat[0].id);
          }
        } else if (productId) {
          applyProduct(await fetchAdminProduct(productId));
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : t("loadFailed"));
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [applyProduct, isNew, productId, t, ta]);

  function toggleAttribute(id: string) {
    setAttributeIds((current) =>
      current.includes(id) ? current.filter((x) => x !== id) : [...current, id],
    );
  }

  async function reload() {
    if (!productId) {
      return;
    }
    applyProduct(await fetchAdminProduct(productId));
  }

  async function onSave(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    setMessage(null);
    try {
      if (isNew) {
        const variants =
          createVariant.sku.trim() && createVariant.price_bdt.trim()
            ? [
                {
                  sku: createVariant.sku.trim(),
                  size_label: createVariant.size_label || null,
                  shade_name: createVariant.shade_name || null,
                  shade_hex: createVariant.shade_hex || null,
                  spf: createVariant.spf ? Number.parseInt(createVariant.spf, 10) : null,
                  price_poisha: bdtToPoisha(createVariant.price_bdt),
                  weight_grams: createVariant.weight_grams
                    ? Number.parseInt(createVariant.weight_grams, 10)
                    : null,
                },
              ]
            : [];
        const created = await createProduct({
          category_id: categoryId,
          slug: slug || slugify(name),
          name,
          subtitle: subtitle || null,
          description: description || null,
          how_to_use: howToUse || null,
          ingredients_text: ingredients || null,
          warnings: warnings || null,
          routine_step: routineStep || null,
          pao_months: paoMonths ? Number.parseInt(paoMonths, 10) : null,
          shelf_life_months: shelfLife ? Number.parseInt(shelfLife, 10) : null,
          status,
          attribute_ids: attributeIds,
          variants,
        });
        setMessage(t("productCreated"));
        router.push(`/${locale}/admin/catalog/products/${created.id}`);
        return;
      }
      await patchProduct(productId!, {
        category_id: categoryId,
        name,
        subtitle: subtitle || null,
        description: description || null,
        how_to_use: howToUse || null,
        ingredients_text: ingredients || null,
        warnings: warnings || null,
        routine_step: routineStep || null,
        pao_months: paoMonths ? Number.parseInt(paoMonths, 10) : null,
        shelf_life_months: shelfLife ? Number.parseInt(shelfLife, 10) : null,
        status,
        attribute_ids: attributeIds,
      });
      setMessage(t("productSaved"));
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onSoftDelete() {
    if (!productId) {
      return;
    }
    if (!window.confirm(t("confirmDeleteProduct", { name }))) {
      return;
    }
    setPending(true);
    setError(null);
    try {
      await deleteProduct(productId);
      router.push(`/${locale}/admin/catalog`);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
      setPending(false);
    }
  }

  async function onAddVariant(event: FormEvent) {
    event.preventDefault();
    if (!productId) {
      return;
    }
    setPending(true);
    setError(null);
    try {
      await addVariant(productId, {
        sku: newVariant.sku.trim(),
        size_label: newVariant.size_label || null,
        shade_name: newVariant.shade_name || null,
        shade_hex: newVariant.shade_hex || null,
        spf: newVariant.spf ? Number.parseInt(newVariant.spf, 10) : null,
        price_poisha: bdtToPoisha(newVariant.price_bdt),
        weight_grams: newVariant.weight_grams
          ? Number.parseInt(newVariant.weight_grams, 10)
          : null,
      });
      setNewVariant({ ...EMPTY_VARIANT });
      setMessage(t("variantAdded"));
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onSaveVariant(row: Variant, priceBdt: string) {
    setPending(true);
    setError(null);
    try {
      await patchVariant(row.id, {
        price_poisha: bdtToPoisha(priceBdt),
        size_label: row.size_label,
        shade_name: row.shade_name,
        is_active: row.is_active,
      });
      setMessage(t("variantSaved"));
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onDeleteVariant(variantId: string) {
    if (!window.confirm(t("confirmDeleteVariant"))) {
      return;
    }
    setPending(true);
    setError(null);
    try {
      await deleteVariant(variantId);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onUploadImage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!productId) {
      return;
    }
    const form = event.currentTarget;
    const fileInput = form.elements.namedItem("file") as HTMLInputElement;
    const file = fileInput.files?.[0];
    if (!file) {
      setError(t("imageRequired"));
      return;
    }
    setPending(true);
    setError(null);
    try {
      await uploadProductImage(productId, file, imageSlot, imageAlt);
      setImageAlt("");
      form.reset();
      setMessage(t("imageUploaded"));
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onDeleteImage(imageId: string) {
    setPending(true);
    setError(null);
    try {
      await deleteProductImage(imageId);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onReceive(event: FormEvent) {
    event.preventDefault();
    if (!canWarehouse) {
      setError(t("warehouseRequired"));
      return;
    }
    setPending(true);
    setError(null);
    try {
      await receiveStock({
        variant_id: receiptVariantId,
        qty: Number.parseInt(receiptQty, 10),
      });
      setMessage(t("stockReceived"));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  if (me === undefined || loading) {
    return <p className="text-sm text-muted">{ta("loading")}</p>;
  }
  if (error && !isStaff(me)) {
    return (
      <p role="alert" className="text-sm text-danger">
        {error}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-lg">
      <div className="flex flex-wrap items-center justify-between gap-sm">
        <Link href={`/${locale}/admin/catalog`} className="text-sm text-muted underline">
          {t("backToCatalog")}
        </Link>
        {!isNew ? (
          <button
            type="button"
            disabled={pending}
            onClick={() => void onSoftDelete()}
            className="rounded-sm border border-danger px-sm py-xs text-sm text-danger disabled:opacity-60"
          >
            {t("softDelete")}
          </button>
        ) : null}
      </div>

      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}
      {message ? (
        <p role="status" className="text-sm text-ok">
          {message}
        </p>
      ) : null}

      <form onSubmit={onSave} className="grid gap-sm md:grid-cols-2">
        <label className="flex flex-col gap-xs text-sm md:col-span-2">
          <span>{t("productName")}</span>
          <input
            required
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (isNew && (!slug || slug === slugify(name))) {
                setSlug(slugify(e.target.value));
              }
            }}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
          />
        </label>
        <label className="flex flex-col gap-xs text-sm">
          <span>{t("slug")}</span>
          <input
            required
            disabled={!isNew}
            pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            className="rounded-sm border border-line bg-surface px-sm py-sm font-mono text-ink disabled:opacity-60"
          />
        </label>
        <label className="flex flex-col gap-xs text-sm">
          <span>{t("category")}</span>
          <select
            required
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
          >
            {flatCategories.map((node) => (
              <option key={node.id} value={node.id}>
                {node.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-xs text-sm md:col-span-2">
          <span>{t("subtitle")}</span>
          <input
            value={subtitle}
            onChange={(e) => setSubtitle(e.target.value)}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
          />
        </label>
        <label className="flex flex-col gap-xs text-sm md:col-span-2">
          <span>{t("description")}</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
          />
        </label>
        <label className="flex flex-col gap-xs text-sm md:col-span-2">
          <span>{t("howToUse")}</span>
          <textarea
            value={howToUse}
            onChange={(e) => setHowToUse(e.target.value)}
            rows={2}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
          />
        </label>
        <label className="flex flex-col gap-xs text-sm md:col-span-2">
          <span>{t("ingredients")}</span>
          <textarea
            value={ingredients}
            onChange={(e) => setIngredients(e.target.value)}
            rows={2}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
          />
        </label>
        <label className="flex flex-col gap-xs text-sm md:col-span-2">
          <span>{t("warnings")}</span>
          <textarea
            value={warnings}
            onChange={(e) => setWarnings(e.target.value)}
            rows={2}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
          />
        </label>
        <label className="flex flex-col gap-xs text-sm">
          <span>{t("routineStep")}</span>
          <select
            value={routineStep}
            onChange={(e) => setRoutineStep(e.target.value as "" | RoutineStep)}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
          >
            <option value="">{t("routineNone")}</option>
            <option value="am">AM</option>
            <option value="pm">PM</option>
            <option value="both">Both</option>
          </select>
        </label>
        <label className="flex flex-col gap-xs text-sm">
          <span>{t("statusLabel")}</span>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as ProductStatus)}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
          >
            <option value="draft">{t("status.draft")}</option>
            <option value="published">{t("status.published")}</option>
            <option value="archived">{t("status.archived")}</option>
          </select>
        </label>
        <label className="flex flex-col gap-xs text-sm">
          <span>{t("paoMonths")}</span>
          <input
            type="number"
            min={1}
            max={120}
            value={paoMonths}
            onChange={(e) => setPaoMonths(e.target.value)}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
          />
        </label>
        <label className="flex flex-col gap-xs text-sm">
          <span>{t("shelfLifeMonths")}</span>
          <input
            type="number"
            min={1}
            max={120}
            value={shelfLife}
            onChange={(e) => setShelfLife(e.target.value)}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
          />
        </label>

        <fieldset className="md:col-span-2">
          <legend className="mb-xs text-sm font-medium">{t("attributes")}</legend>
          <div className="grid gap-xs sm:grid-cols-2">
            {attributes
              .filter((a) => a.is_active)
              .map((attr) => (
                <label key={attr.id} className="flex items-center gap-sm text-sm">
                  <input
                    type="checkbox"
                    checked={attributeIds.includes(attr.id)}
                    onChange={() => toggleAttribute(attr.id)}
                  />
                  <span>
                    <span className="text-muted">{attr.kind}:</span> {attr.name}
                  </span>
                </label>
              ))}
          </div>
        </fieldset>

        {isNew ? (
          <fieldset className="grid gap-sm border-t border-line pt-md md:col-span-2 md:grid-cols-2">
            <legend className="mb-xs text-sm font-medium md:col-span-2">
              {t("initialVariant")}
            </legend>
            <VariantFields draft={createVariant} onChange={setCreateVariant} optional />
          </fieldset>
        ) : null}

        <button
          type="submit"
          disabled={pending}
          className="rounded-sm bg-ink px-md py-sm text-sm font-medium text-paper disabled:opacity-60 md:col-span-2 md:w-fit"
        >
          {pending ? t("working") : isNew ? t("createProduct") : t("saveProduct")}
        </button>
      </form>

      {!isNew && product ? (
        <>
          <section className="flex flex-col gap-md border-t border-line pt-md">
            <h2 className="text-sm font-semibold text-ink">{t("variants")}</h2>
            {product.variants.length === 0 ? (
              <p className="text-sm text-muted">{t("noVariants")}</p>
            ) : (
              <ul className="divide-y divide-line border border-line">
                {product.variants.map((row) => (
                  <VariantRow
                    key={row.id}
                    row={row}
                    pending={pending}
                    onSave={onSaveVariant}
                    onDelete={onDeleteVariant}
                  />
                ))}
              </ul>
            )}
            <form onSubmit={onAddVariant} className="grid gap-sm md:grid-cols-2">
              <h3 className="text-sm font-medium md:col-span-2">{t("addVariant")}</h3>
              <VariantFields draft={newVariant} onChange={setNewVariant} />
              <button
                type="submit"
                disabled={pending}
                className="rounded-sm border border-line px-md py-sm text-sm disabled:opacity-60 md:col-span-2 md:w-fit"
              >
                {t("addVariant")}
              </button>
            </form>
          </section>

          <section className="flex flex-col gap-md border-t border-line pt-md">
            <h2 className="text-sm font-semibold text-ink">{t("images")}</h2>
            {product.images.length === 0 ? (
              <p className="text-sm text-muted">{t("noImages")}</p>
            ) : (
              <ul className="grid gap-sm sm:grid-cols-2 md:grid-cols-3">
                {product.images.map((img) => (
                  <li key={img.id} className="border border-line p-sm">
                    {img.thumb_webp_url || img.card_webp_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={img.thumb_webp_url || img.card_webp_url || ""}
                        alt={img.alt_text ?? ""}
                        className="mb-sm h-28 w-full object-cover"
                      />
                    ) : (
                      <div className="mb-sm flex h-28 items-center justify-center bg-paper text-xs text-muted">
                        {img.slot}
                      </div>
                    )}
                    <p className="text-xs text-muted">
                      {img.slot} · {img.width}×{img.height}
                    </p>
                    <button
                      type="button"
                      disabled={pending}
                      onClick={() => void onDeleteImage(img.id)}
                      className="mt-xs text-sm text-danger underline disabled:opacity-60"
                    >
                      {t("delete")}
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <form onSubmit={onUploadImage} className="grid max-w-xl gap-sm md:grid-cols-2">
              <label className="flex flex-col gap-xs text-sm md:col-span-2">
                <span>{t("imageFile")}</span>
                <input
                  name="file"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  required
                  className="text-sm"
                />
              </label>
              <label className="flex flex-col gap-xs text-sm">
                <span>{t("imageSlot")}</span>
                <select
                  value={imageSlot}
                  onChange={(e) => setImageSlot(e.target.value)}
                  className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
                >
                  <option value="product">product</option>
                  <option value="texture">texture</option>
                  <option value="lifestyle">lifestyle</option>
                </select>
              </label>
              <label className="flex flex-col gap-xs text-sm">
                <span>{t("imageAlt")}</span>
                <input
                  value={imageAlt}
                  onChange={(e) => setImageAlt(e.target.value)}
                  className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
                />
              </label>
              <button
                type="submit"
                disabled={pending}
                className="rounded-sm border border-line px-md py-sm text-sm disabled:opacity-60 md:col-span-2 md:w-fit"
              >
                {t("uploadImage")}
              </button>
            </form>
          </section>

          <section className="flex flex-col gap-md border-t border-line pt-md">
            <h2 className="text-sm font-semibold text-ink">{t("stockSection")}</h2>
            {!canWarehouse ? (
              <p className="text-sm text-muted">{t("warehouseRequired")}</p>
            ) : null}
            <form onSubmit={onReceive} className="grid max-w-xl gap-sm md:grid-cols-2">
              <label className="flex flex-col gap-xs text-sm md:col-span-2">
                <span>{t("variant")}</span>
                <select
                  required
                  value={receiptVariantId}
                  onChange={(e) => setReceiptVariantId(e.target.value)}
                  className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
                >
                  {product.variants.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.sku}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-xs text-sm">
                <span>{t("qty")}</span>
                <input
                  required
                  type="number"
                  min={1}
                  value={receiptQty}
                  onChange={(e) => setReceiptQty(e.target.value)}
                  className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
                />
              </label>
              <button
                type="submit"
                disabled={pending || !canWarehouse || product.variants.length === 0}
                className="rounded-sm bg-ink px-md py-sm text-sm font-medium text-paper disabled:opacity-60 md:self-end"
              >
                {t("receiveStock")}
              </button>
            </form>
          </section>
        </>
      ) : null}
    </div>
  );
}

function VariantFields({
  draft,
  onChange,
  optional = false,
}: {
  draft: VariantDraft;
  onChange: (next: VariantDraft) => void;
  optional?: boolean;
}) {
  const t = useTranslations("adminCatalog");
  function set<K extends keyof VariantDraft>(key: K, value: VariantDraft[K]) {
    onChange({ ...draft, [key]: value });
  }
  return (
    <>
      <label className="flex flex-col gap-xs text-sm">
        <span>SKU</span>
        <input
          required={!optional}
          value={draft.sku}
          onChange={(e) => set("sku", e.target.value)}
          className="rounded-sm border border-line bg-surface px-sm py-sm font-mono text-ink"
        />
      </label>
      <label className="flex flex-col gap-xs text-sm">
        <span>{t("priceBdt")}</span>
        <input
          required={!optional}
          type="number"
          min={0}
          step="0.01"
          value={draft.price_bdt}
          onChange={(e) => set("price_bdt", e.target.value)}
          className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
        />
      </label>
      <label className="flex flex-col gap-xs text-sm">
        <span>{t("sizeLabel")}</span>
        <input
          value={draft.size_label}
          onChange={(e) => set("size_label", e.target.value)}
          className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
        />
      </label>
      <label className="flex flex-col gap-xs text-sm">
        <span>{t("shadeName")}</span>
        <input
          value={draft.shade_name}
          onChange={(e) => set("shade_name", e.target.value)}
          className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
        />
      </label>
      <label className="flex flex-col gap-xs text-sm">
        <span>{t("shadeHex")}</span>
        <input
          pattern="^#[0-9A-Fa-f]{6}$"
          placeholder="#AABBCC"
          value={draft.shade_hex}
          onChange={(e) => set("shade_hex", e.target.value)}
          className="rounded-sm border border-line bg-surface px-sm py-sm font-mono text-ink"
        />
      </label>
      <label className="flex flex-col gap-xs text-sm">
        <span>SPF</span>
        <input
          type="number"
          min={0}
          max={100}
          value={draft.spf}
          onChange={(e) => set("spf", e.target.value)}
          className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
        />
      </label>
      <label className="flex flex-col gap-xs text-sm">
        <span>{t("weightGrams")}</span>
        <input
          type="number"
          min={0}
          value={draft.weight_grams}
          onChange={(e) => set("weight_grams", e.target.value)}
          className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
        />
      </label>
    </>
  );
}

function VariantRow({
  row,
  pending,
  onSave,
  onDelete,
}: {
  row: Variant;
  pending: boolean;
  onSave: (row: Variant, priceBdt: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const t = useTranslations("adminCatalog");
  const [price, setPrice] = useState(poishaToBdtInput(row.price_poisha));
  useEffect(() => {
    setPrice(poishaToBdtInput(row.price_poisha));
  }, [row.price_poisha]);

  return (
    <li className="flex flex-col gap-sm px-sm py-sm text-sm md:flex-row md:items-end md:justify-between">
      <div>
        <p className="font-mono font-medium text-ink">{row.sku}</p>
        <p className="text-xs text-muted">
          {[row.size_label, row.shade_name, row.spf != null ? `SPF ${row.spf}` : null]
            .filter(Boolean)
            .join(" · ") || "—"}
          {row.is_active ? "" : ` · ${t("inactive")}`}
        </p>
      </div>
      <div className="flex flex-wrap items-end gap-sm">
        <label className="flex flex-col gap-xs">
          <span className="text-xs text-muted">{t("priceBdt")}</span>
          <input
            type="number"
            min={0}
            step="0.01"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="w-28 rounded-sm border border-line bg-surface px-sm py-xs text-ink"
          />
        </label>
        <button
          type="button"
          disabled={pending}
          onClick={() => void onSave(row, price)}
          className="rounded-sm border border-line px-sm py-xs disabled:opacity-60"
        >
          {t("save")}
        </button>
        <button
          type="button"
          disabled={pending}
          onClick={() => void onDelete(row.id)}
          className="rounded-sm border border-danger px-sm py-xs text-danger disabled:opacity-60"
        >
          {t("delete")}
        </button>
      </div>
    </li>
  );
}
