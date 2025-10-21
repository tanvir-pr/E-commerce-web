"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { fetchMe, isStaff, type Me } from "@/lib/api";
import {
  bulkProductStatus,
  createCategory,
  deleteCategory,
  fetchAdminCategories,
  fetchAdminProducts,
  fetchLowStock,
  flattenCategories,
  formatBdt,
  patchCategory,
  receiveStock,
  slugify,
  type CategoryNode,
  type LowStockItem,
  type ProductStatus,
  type ProductSummary,
} from "@/lib/catalog-admin";

type Tab = "products" | "categories" | "stock";

export function CatalogAdmin() {
  const t = useTranslations("adminCatalog");
  const ta = useTranslations("admin");
  const locale = useLocale();
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [tab, setTab] = useState<Tab>("products");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

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
      }
    })();
    return () => {
      active = false;
    };
  }, [ta]);

  if (me === undefined) {
    return <p className="text-sm text-muted">{ta("loading")}</p>;
  }
  if (error && !isStaff(me)) {
    return (
      <p role="alert" className="text-sm text-danger">
        {error}
      </p>
    );
  }

  const canWarehouse =
    Boolean(me?.roles.includes("super_admin")) ||
    Boolean(me?.permissions.includes("warehouse"));

  return (
    <div className="flex flex-col gap-lg">
      <div className="flex flex-wrap gap-xs border-b border-line pb-sm">
        {(["products", "categories", "stock"] as Tab[]).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => {
              setTab(key);
              setError(null);
              setMessage(null);
            }}
            className={
              tab === key
                ? "rounded-sm bg-ink px-sm py-xs text-sm text-paper"
                : "rounded-sm px-sm py-xs text-sm text-muted hover:text-ink"
            }
          >
            {t(`tabs.${key}`)}
          </button>
        ))}
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
      {tab === "products" ? (
        <ProductsPanel
          locale={locale}
          onError={setError}
          onMessage={setMessage}
        />
      ) : null}
      {tab === "categories" ? (
        <CategoriesPanel onError={setError} onMessage={setMessage} />
      ) : null}
      {tab === "stock" ? (
        <StockPanel
          locale={locale}
          canWarehouse={canWarehouse}
          onError={setError}
          onMessage={setMessage}
        />
      ) : null}
    </div>
  );
}

function ProductsPanel({
  locale,
  onError,
  onMessage,
}: {
  locale: string;
  onError: (value: string | null) => void;
  onMessage: (value: string | null) => void;
}) {
  const t = useTranslations("adminCatalog");
  const [items, setItems] = useState<ProductSummary[]>([]);
  const [status, setStatus] = useState<string>("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    onError(null);
    try {
      const rows = await fetchAdminProducts(status ? { status } : undefined);
      setItems(rows);
      setSelected(new Set());
    } catch (err) {
      onError(err instanceof Error ? err.message : t("loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [onError, status, t]);

  useEffect(() => {
    void load();
  }, [load]);

  function toggle(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function toggleAll() {
    if (selected.size === items.length) {
      setSelected(new Set());
      return;
    }
    setSelected(new Set(items.map((row) => row.id)));
  }

  async function applyBulk(next: ProductStatus) {
    if (selected.size === 0) {
      return;
    }
    setPending(true);
    onError(null);
    onMessage(null);
    try {
      const result = await bulkProductStatus([...selected], next);
      onMessage(t("bulkUpdated", { count: result.updated, status: next }));
      await load();
    } catch (err) {
      onError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-md">
      <div className="flex flex-wrap items-center justify-between gap-sm">
        <div className="flex flex-wrap items-center gap-sm">
          <label className="flex items-center gap-xs text-sm">
            <span className="text-muted">{t("filterStatus")}</span>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="rounded-sm border border-line bg-surface px-sm py-xs text-ink"
            >
              <option value="">{t("allStatuses")}</option>
              <option value="draft">{t("status.draft")}</option>
              <option value="published">{t("status.published")}</option>
              <option value="archived">{t("status.archived")}</option>
            </select>
          </label>
          {selected.size > 0 ? (
            <div className="flex flex-wrap gap-xs">
              <button
                type="button"
                disabled={pending}
                onClick={() => void applyBulk("published")}
                className="rounded-sm border border-line px-sm py-xs text-sm disabled:opacity-60"
              >
                {t("bulkPublish")}
              </button>
              <button
                type="button"
                disabled={pending}
                onClick={() => void applyBulk("draft")}
                className="rounded-sm border border-line px-sm py-xs text-sm disabled:opacity-60"
              >
                {t("bulkDraft")}
              </button>
              <button
                type="button"
                disabled={pending}
                onClick={() => void applyBulk("archived")}
                className="rounded-sm border border-line px-sm py-xs text-sm disabled:opacity-60"
              >
                {t("bulkArchive")}
              </button>
            </div>
          ) : null}
        </div>
        <Link
          href={`/${locale}/admin/catalog/products/new`}
          className="rounded-sm bg-ink px-md py-sm text-sm font-medium text-paper"
        >
          {t("newProduct")}
        </Link>
      </div>
      {loading ? (
        <p className="text-sm text-muted">{t("loading")}</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-muted">{t("noProducts")}</p>
      ) : (
        <div className="overflow-x-auto border border-line">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <thead className="border-b border-line bg-paper/60 text-muted">
              <tr>
                <th className="px-sm py-sm">
                  <input
                    type="checkbox"
                    checked={selected.size === items.length && items.length > 0}
                    onChange={toggleAll}
                    aria-label={t("selectAll")}
                  />
                </th>
                <th className="px-sm py-sm font-medium">{t("colName")}</th>
                <th className="px-sm py-sm font-medium">{t("colStatus")}</th>
                <th className="px-sm py-sm font-medium">{t("colPrice")}</th>
                <th className="px-sm py-sm font-medium">{t("colCategory")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {items.map((row) => (
                <tr key={row.id} className="hover:bg-paper/40">
                  <td className="px-sm py-sm">
                    <input
                      type="checkbox"
                      checked={selected.has(row.id)}
                      onChange={() => toggle(row.id)}
                      aria-label={row.name}
                    />
                  </td>
                  <td className="px-sm py-sm">
                    <Link
                      href={`/${locale}/admin/catalog/products/${row.id}`}
                      className="font-medium text-ink underline"
                    >
                      {row.name}
                    </Link>
                    <p className="text-xs text-muted">{row.slug}</p>
                  </td>
                  <td className="px-sm py-sm">{t(`status.${row.status}`)}</td>
                  <td className="px-sm py-sm">{formatBdt(row.from_price_poisha)}</td>
                  <td className="px-sm py-sm text-muted">{row.category_slug ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function CategoriesPanel({
  onError,
  onMessage,
}: {
  onError: (value: string | null) => void;
  onMessage: (value: string | null) => void;
}) {
  const t = useTranslations("adminCatalog");
  const [tree, setTree] = useState<CategoryNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [parentId, setParentId] = useState("");
  const [description, setDescription] = useState("");
  const flat = useMemo(() => flattenCategories(tree), [tree]);

  const load = useCallback(async () => {
    setLoading(true);
    onError(null);
    try {
      setTree(await fetchAdminCategories());
    } catch (err) {
      onError(err instanceof Error ? err.message : t("loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [onError, t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    onError(null);
    onMessage(null);
    try {
      await createCategory({
        name,
        slug: slug || slugify(name),
        parent_id: parentId || null,
        description: description || null,
        is_active: true,
        sort_order: 0,
        attribute_ids: [],
      });
      setName("");
      setSlug("");
      setParentId("");
      setDescription("");
      onMessage(t("categoryCreated"));
      await load();
    } catch (err) {
      onError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function toggleActive(node: CategoryNode) {
    setPending(true);
    onError(null);
    try {
      await patchCategory(node.id, { is_active: !node.is_active });
      await load();
    } catch (err) {
      onError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onDelete(node: CategoryNode) {
    if (!window.confirm(t("confirmDeleteCategory", { name: node.name.replace(/^—\s*/, "") }))) {
      return;
    }
    setPending(true);
    onError(null);
    try {
      await deleteCategory(node.id);
      onMessage(t("categoryDeleted"));
      await load();
    } catch (err) {
      onError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-lg">
      <form onSubmit={onCreate} className="grid max-w-xl gap-sm md:grid-cols-2">
        <label className="flex flex-col gap-xs text-sm md:col-span-2">
          <span>{t("categoryName")}</span>
          <input
            required
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (!slug || slug === slugify(name)) {
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
            pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            className="rounded-sm border border-line bg-surface px-sm py-sm font-mono text-ink"
          />
        </label>
        <label className="flex flex-col gap-xs text-sm">
          <span>{t("parentCategory")}</span>
          <select
            value={parentId}
            onChange={(e) => setParentId(e.target.value)}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
          >
            <option value="">{t("noParent")}</option>
            {flat.map((node) => (
              <option key={node.id} value={node.id}>
                {node.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-xs text-sm md:col-span-2">
          <span>{t("description")}</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
          />
        </label>
        <button
          type="submit"
          disabled={pending}
          className="rounded-sm bg-ink px-md py-sm text-sm font-medium text-paper disabled:opacity-60 md:col-span-2 md:w-fit"
        >
          {pending ? t("working") : t("addCategory")}
        </button>
      </form>

      {loading ? (
        <p className="text-sm text-muted">{t("loading")}</p>
      ) : flat.length === 0 ? (
        <p className="text-sm text-muted">{t("noCategories")}</p>
      ) : (
        <ul className="divide-y divide-line border border-line">
          {flat.map((node) => (
            <li
              key={node.id}
              className="flex flex-wrap items-center justify-between gap-sm px-sm py-sm text-sm"
            >
              <div>
                <p className="font-medium text-ink">{node.name}</p>
                <p className="text-xs text-muted">
                  {node.slug}
                  {node.is_active ? "" : ` · ${t("inactive")}`}
                </p>
              </div>
              <div className="flex gap-xs">
                <button
                  type="button"
                  disabled={pending}
                  onClick={() => void toggleActive(node)}
                  className="rounded-sm border border-line px-sm py-xs disabled:opacity-60"
                >
                  {node.is_active ? t("deactivate") : t("activate")}
                </button>
                <button
                  type="button"
                  disabled={pending}
                  onClick={() => void onDelete(node)}
                  className="rounded-sm border border-danger px-sm py-xs text-danger disabled:opacity-60"
                >
                  {t("delete")}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function StockPanel({
  locale,
  canWarehouse,
  onError,
  onMessage,
}: {
  locale: string;
  canWarehouse: boolean;
  onError: (value: string | null) => void;
  onMessage: (value: string | null) => void;
}) {
  const t = useTranslations("adminCatalog");
  const [items, setItems] = useState<LowStockItem[]>([]);
  const [threshold, setThreshold] = useState(10);
  const [loading, setLoading] = useState(true);
  const [receiptVariant, setReceiptVariant] = useState("");
  const [qty, setQty] = useState("10");
  const [lot, setLot] = useState("");
  const [expires, setExpires] = useState("");
  const [pending, setPending] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    onError(null);
    try {
      setItems(await fetchLowStock(threshold));
    } catch (err) {
      onError(err instanceof Error ? err.message : t("loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [onError, t, threshold]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onReceive(event: FormEvent) {
    event.preventDefault();
    if (!canWarehouse) {
      onError(t("warehouseRequired"));
      return;
    }
    setPending(true);
    onError(null);
    onMessage(null);
    try {
      await receiveStock({
        variant_id: receiptVariant,
        qty: Number.parseInt(qty, 10),
        lot_code: lot || undefined,
        expires_on: expires || undefined,
      });
      onMessage(t("stockReceived"));
      setQty("10");
      setLot("");
      setExpires("");
      await load();
    } catch (err) {
      onError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-lg">
      <div className="flex flex-wrap items-end gap-sm">
        <label className="flex flex-col gap-xs text-sm">
          <span>{t("threshold")}</span>
          <input
            type="number"
            min={0}
            value={threshold}
            onChange={(e) => setThreshold(Number.parseInt(e.target.value, 10) || 0)}
            className="w-28 rounded-sm border border-line bg-surface px-sm py-sm text-ink"
          />
        </label>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-sm border border-line px-md py-sm text-sm"
        >
          {t("refresh")}
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-muted">{t("loading")}</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-muted">{t("noLowStock")}</p>
      ) : (
        <ul className="divide-y divide-line border border-line">
          {items.map((row) => (
            <li
              key={row.variant_id}
              className="flex flex-wrap items-center justify-between gap-sm px-sm py-sm text-sm"
            >
              <div>
                <p className="font-mono font-medium text-ink">{row.sku}</p>
                <p className="text-xs text-muted">
                  {row.product_slug ?? row.product_id}
                  {row.nearest_expiry ? ` · exp ${row.nearest_expiry}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-sm">
                <span className="text-muted">
                  {t("qtyOnHand", { qty: row.qty_on_hand })}
                </span>
                <Link
                  href={`/${locale}/admin/catalog/products/${row.product_id}`}
                  className="underline"
                >
                  {t("editProduct")}
                </Link>
                <button
                  type="button"
                  onClick={() => setReceiptVariant(row.variant_id)}
                  className="rounded-sm border border-line px-sm py-xs"
                >
                  {t("receive")}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <form
        onSubmit={onReceive}
        className="grid max-w-xl gap-sm border-t border-line pt-md md:grid-cols-2"
      >
        <h2 className="text-sm font-semibold text-ink md:col-span-2">{t("receiptTitle")}</h2>
        {!canWarehouse ? (
          <p className="text-sm text-muted md:col-span-2">{t("warehouseRequired")}</p>
        ) : null}
        <label className="flex flex-col gap-xs text-sm md:col-span-2">
          <span>{t("variantId")}</span>
          <input
            required
            value={receiptVariant}
            onChange={(e) => setReceiptVariant(e.target.value)}
            className="rounded-sm border border-line bg-surface px-sm py-sm font-mono text-ink"
          />
        </label>
        <label className="flex flex-col gap-xs text-sm">
          <span>{t("qty")}</span>
          <input
            required
            type="number"
            min={1}
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
          />
        </label>
        <label className="flex flex-col gap-xs text-sm">
          <span>{t("lotCode")}</span>
          <input
            value={lot}
            onChange={(e) => setLot(e.target.value)}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
          />
        </label>
        <label className="flex flex-col gap-xs text-sm md:col-span-2">
          <span>{t("expiresOn")}</span>
          <input
            type="date"
            value={expires}
            onChange={(e) => setExpires(e.target.value)}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
          />
        </label>
        <button
          type="submit"
          disabled={pending || !canWarehouse}
          className="rounded-sm bg-ink px-md py-sm text-sm font-medium text-paper disabled:opacity-60 md:col-span-2 md:w-fit"
        >
          {pending ? t("working") : t("receiveStock")}
        </button>
      </form>
    </div>
  );
}
