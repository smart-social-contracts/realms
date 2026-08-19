<script lang="ts">import { onMount } from "svelte";
import { browser } from "$app/environment";
import { goto } from "$app/navigation";
import { page } from "$app/stores";
import { _ } from "svelte-i18n";
import ItemCard from "$lib/components/ItemCard.svelte";
import SkeletonCard from "$lib/components/SkeletonCard.svelte";
import InfoTip from "$lib/components/InfoTip.svelte";
import { categories as parseCategories, screenshots as parseScreenshots } from "$lib/format";
import { fileUrl } from "$lib/file-registry-client";
import {
  marketplaceClient
} from "$lib/marketplace-client";
import { isAuthenticated, principalStore } from "$lib/auth";
import { CONFIG } from "$lib/config";
const KIND_VALUES = ["ext", "codex", "assistant"];
const KIND_I18N = {
  ext: "kind.extensions",
  codex: "kind.codices",
  assistant: "kind.assistants"
};
const PUBLISH_I18N = {
  ext: "discover.publish_ext",
  codex: "discover.publish_codex",
  assistant: "discover.publish_assistant"
};
const LANG_NAMES = {
  en: "English",
  es: "Español",
  fr: "Français",
  de: "Deutsch",
  it: "Italiano",
  pt: "Português",
  zh: "\u4E2D\u6587",
  ja: "\u65E5\u672C\u8A9E",
  ko: "\uD55C\uAD6D\uC5B4",
  ar: "\u0627\u0644\u0639\u0631\u0628\u064A\u0629",
  ru: "\u0420\u0443\u0441\u0441\u043A\u0438\u0439",
  nl: "Nederlands",
  pl: "Polski",
  tr: "T\xFCrk\xE7e",
  hi: "\u0939\u093F\u0928\u094D\u0926\u0940"
};
function parseLangs(raw) {
  return raw.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);
}
function langLabel(code) {
  return LANG_NAMES[code] ?? code.toUpperCase();
}
let kind = "ext";
let metric = "downloads";
let verifiedOnly = false;
let selectedCategory = "";
let selectedLanguage = "";
let loading = true;
let error = "";
let mounted = false;
let items = [];
let likedSet = new Set();
let searchQuery = "";
let catalogSection;
function scrollToCatalog(k) {
  kind = k;
  catalogSection?.scrollIntoView({ behavior: "smooth", block: "start" });
}
onMount(async () => {
  const params = $page.url.searchParams;
  const k = params.get("kind");
  if (k === "ext" || k === "codex" || k === "assistant") kind = k;
  const s = params.get("sort");
  if (s === "likes" || s === "downloads" || s === "newest") metric = s;
  verifiedOnly = params.get("verified") === "1";
  if (kind === "ext") selectedCategory = params.get("category") ?? "";
  if (kind === "ext") selectedLanguage = params.get("lang") ?? "";
  searchQuery = params.get("q") ?? "";
  if (searchQuery.trim() && !k) {
    kind = await resolveKindForQuery(searchQuery.trim(), verifiedOnly);
  }
  mounted = true;
});
$: void load(kind, metric, verifiedOnly, searchQuery);
$: if (kind !== "ext" && selectedCategory) selectedCategory = "";
$: if (kind !== "ext" && selectedLanguage) selectedLanguage = "";
$: availableCategories = kind === "ext" ? Array.from(new Set(items.flatMap((it) => parseCategories(categoriesFor(it))))).sort() : [];
$: availableLanguages = kind === "ext" ? Array.from(new Set(items.flatMap((it) => parseLangs(it.languages ?? "")))).sort() : [];
$: displayItems = kind === "ext" ? items.filter((it) => !selectedCategory || parseCategories(categoriesFor(it)).includes(selectedCategory)).filter((it) => !selectedLanguage || parseLangs(it.languages ?? "").includes(selectedLanguage)) : items;
$: if (browser && mounted) syncUrl(kind, metric, verifiedOnly, selectedCategory, selectedLanguage);
function syncUrl(k, m, v, cat, lang) {
  const params = new URLSearchParams();
  if (searchQuery.trim()) params.set("q", searchQuery.trim());
  if (k !== "ext") params.set("kind", k);
  if (m !== "downloads") params.set("sort", m);
  if (v) params.set("verified", "1");
  if (k === "ext" && cat) params.set("category", cat);
  if (k === "ext" && lang) params.set("lang", lang);
  const qs = params.toString();
  goto(qs ? `/?${qs}` : "/", { replaceState: true, keepFocus: true, noScroll: true });
}
async function resolveKindForQuery(q, verified) {
  try {
    const [assistants, extensions, codices] = await Promise.all([
      marketplaceClient.searchAssistants(q, verified),
      marketplaceClient.searchExtensions(q, verified),
      marketplaceClient.searchCodices(q, verified),
    ]);
    if (assistants.length) return "assistant";
    if (extensions.length) return "ext";
    if (codices.length) return "codex";
  } catch {
    /* fall through */
  }
  return "ext";
}
$: void refreshLikes($isAuthenticated, $principalStore?.toText());
async function refreshLikes(_authed, _principal) {
  if (!_authed) {
    likedSet = new Set();
    return;
  }
  try {
    const my = await marketplaceClient.myLikes();
    likedSet = new Set(my.map((m) => `${m.item_kind}|${m.item_id}`));
  } catch {
    likedSet = new Set();
  }
}
function byNewest(list) {
  return [...list].sort((a, b) => b.created_at - a.created_at);
}
async function load(k, m, v, q) {
  loading = true;
  error = "";
  try {
    const query = (q ?? "").trim();
    if (query) {
      if (k === "ext") items = await marketplaceClient.searchExtensions(query, v);
      else if (k === "codex") items = await marketplaceClient.searchCodices(query, v);
      else items = await marketplaceClient.searchAssistants(query, v);
    } else if (k === "ext") {
      items = m === "downloads" ? await marketplaceClient.topExtensionsByDownloads(20, v) : m === "likes" ? await marketplaceClient.topExtensionsByLikes(20, v) : byNewest((await marketplaceClient.listExtensions(1, 20, v)).listings);
    } else if (k === "codex") {
      items = m === "downloads" ? await marketplaceClient.topCodicesByDownloads(20, v) : m === "likes" ? await marketplaceClient.topCodicesByLikes(20, v) : byNewest((await marketplaceClient.listCodices(1, 20, v)).listings);
    } else {
      items = m === "downloads" ? await marketplaceClient.topAssistantsByDownloads(20, v) : m === "likes" ? await marketplaceClient.topAssistantsByLikes(20, v) : byNewest((await marketplaceClient.listAssistants(1, 20, v)).listings);
    }
  } catch (e) {
    error = e?.message ?? String(e);
    items = [];
  } finally {
    loading = false;
  }
}
function idOf(it) {
  return it.extension_id ?? it.codex_id ?? it.assistant_id ?? "";
}
function hrefOf(k, it) {
  if (k === "ext") return `/extensions/${encodeURIComponent(idOf(it))}`;
  if (k === "codex") return `/codices/${encodeURIComponent(idOf(it))}`;
  return `/assistants/${encodeURIComponent(idOf(it))}`;
}
function defaultIcon(k) {
  if (k === "codex") return "file-code";
  if (k === "assistant") return "robot";
  return "puzzle";
}
function categoriesFor(it) {
  if (it.categories) return it.categories;
  if (it.domains) return it.domains;
  return "";
}
function extensionThumbnail(ext) {
  const paths = parseScreenshots(ext.screenshots ?? "");
  if (!paths.length || !ext.file_registry_canister_id || !ext.file_registry_namespace) return "";
  return fileUrl(ext.file_registry_canister_id, ext.file_registry_namespace, paths[0]);
}
</script>

<section class="landing-hero" aria-labelledby="landing-title">
  <div class="landing-badges">
    {#if CONFIG.env_name}
      <span class="badge badge-env">{$_('landing.badge_env', { values: { env: CONFIG.env_name } })}</span>
    {/if}
    {#if CONFIG.realms_version}
      <span class="badge badge-version">{$_('landing.badge_version', { values: { version: CONFIG.realms_version } })}</span>
    {/if}
  </div>
  <h1 id="landing-title">{$_('landing.product_name')}</h1>
  <p class="landing-pitch">{$_('landing.pitch')}</p>
  <ul class="landing-features" aria-label="Features">
    <li><i class="ti ti-rocket" aria-hidden="true"></i><span>{$_('landing.feature_launch')}</span></li>
    <li><i class="ti ti-puzzle" aria-hidden="true"></i><span>{$_('landing.feature_install')}</span></li>
    <li><i class="ti ti-users-group" aria-hidden="true"></i><span>{$_('landing.feature_community')}</span></li>
  </ul>
  <div class="landing-ctas">
    {#if CONFIG.portal_url}
      <a class="cta primary" href={CONFIG.portal_url} target="_blank" rel="noreferrer">
        <i class="ti ti-external-link" aria-hidden="true"></i>
        {$_('landing.cta_launch')}
      </a>
    {/if}
    <button type="button" class="cta secondary" on:click={() => scrollToCatalog('ext')}>
      {$_('landing.cta_browse_extensions')}
    </button>
    <button type="button" class="cta secondary" on:click={() => scrollToCatalog('codex')}>
      {$_('landing.cta_browse_codices')}
    </button>
  </div>
</section>

<section class="catalog" id="catalog" bind:this={catalogSection}>
  <header class="catalog-header">
    <h2>{$_('discover.title')}</h2>
    <p>{$_('discover.subtitle')}</p>
  </header>

<div class="kind-tabs" role="tablist" aria-label="Listing type">
  {#each KIND_VALUES as k}
    <button
      role="tab"
      aria-selected={kind === k}
      class:active={kind === k}
      on:click={() => (kind = k)}
    >{$_(KIND_I18N[k])}</button>
  {/each}
</div>

<div class="filters">
  <div class="toggle" role="group" aria-label="Sort by">
    <button aria-pressed={metric === 'downloads'} class:active={metric === 'downloads'} on:click={() => (metric = 'downloads')}>{$_('sort.most_downloaded')}</button>
    <button aria-pressed={metric === 'likes'} class:active={metric === 'likes'} on:click={() => (metric = 'likes')}>{$_('sort.most_liked')}</button>
    <button aria-pressed={metric === 'newest'} class:active={metric === 'newest'} on:click={() => (metric = 'newest')}>{$_('sort.newest')}</button>
  </div>
  <label class="verified-toggle">
    <input type="checkbox" bind:checked={verifiedOnly} />
    <span>{$_('filter.verified_only')}</span>
    <InfoTip text={$_('filter.verified_help')} label={$_('filter.verified_help_label')} />
  </label>
</div>

{#if kind === 'ext' && availableCategories.length > 0}
  <div class="cat-filter" role="group" aria-label="Filter extensions by category">
    <button class:active={selectedCategory === ''} on:click={() => (selectedCategory = '')}>{$_('filter.all')}</button>
    {#each availableCategories as c}
      <button
        class:active={selectedCategory === c}
        on:click={() => (selectedCategory = selectedCategory === c ? '' : c)}
      >{c.replace(/_/g, ' ')}</button>
    {/each}
  </div>
{/if}

{#if kind === 'ext' && availableLanguages.length > 0}
  <div class="cat-filter lang-filter" role="group" aria-label="Filter extensions by language">
    <span class="filter-label">{$_('filter.language')}:</span>
    <button class:active={selectedLanguage === ''} on:click={() => (selectedLanguage = '')}>{$_('filter.all')}</button>
    {#each availableLanguages as l}
      <button
        class:active={selectedLanguage === l}
        on:click={() => (selectedLanguage = selectedLanguage === l ? '' : l)}
      >{langLabel(l)}</button>
    {/each}
  </div>
{/if}

{#if loading}
  <div class="grid">
    {#each Array(8) as _}
      <SkeletonCard />
    {/each}
  </div>
{:else if error}
  <div class="state error"><p>{$_('discover.load_error', { values: { error } })}</p></div>
{:else if items.length === 0}
  <div class="state empty">
    <h2>{$_('discover.empty_title')}</h2>
    <p><a href="/upload">{$_(PUBLISH_I18N[kind])}</a></p>
  </div>
{:else if displayItems.length === 0}
  <div class="state empty">
    <h2>{$_('discover.no_matches_title')}</h2>
    <p>
      {#if selectedLanguage}
        {$_('discover.no_matches_lang', { values: { language: langLabel(selectedLanguage) } })}
      {:else}
        {$_('discover.no_matches', { values: { category: selectedCategory.replace(/_/g, ' ') } })}
      {/if}
      <button class="link" on:click={() => { selectedCategory = ''; selectedLanguage = ''; }}>{$_('discover.clear_filter')}</button>
    </p>
  </div>
{:else}
  <div class="grid">
    {#each displayItems as it}
      <ItemCard
        kind={kind}
        id={idOf(it)}
        name={it.name}
        description={it.description}
        version={it.version}
        developer={it.developer}
        icon={it.icon || defaultIcon(kind)}
        priceE8s={it.price_e8s}
        installs={it.installs}
        likes={it.likes}
        categoriesStr={categoriesFor(it)}
        verificationStatus={it.verification_status}
        liked={likedSet.has(`${kind}|${idOf(it)}`)}
        href={hrefOf(kind, it)}
        thumbnail={kind === "ext" ? extensionThumbnail(it) : ""}
      />
    {/each}
  </div>
{/if}
</section>

<style>
  .landing-hero {
    margin-bottom: 2.5rem;
    padding: 2rem 2.25rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0.75rem;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  }
  .landing-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }
  .badge {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.7rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.01em;
    text-transform: lowercase;
  }
  .badge-env {
    background: var(--surface-2);
    border: 1px solid var(--border);
    color: var(--text-muted);
  }
  .badge-version {
    background: var(--verified-bg);
    border: 1px solid rgba(22, 101, 52, 0.15);
    color: var(--verified);
  }
  .landing-hero h1 {
    font-size: clamp(1.75rem, 4vw, 2.5rem);
    margin: 0 0 0.6rem;
    letter-spacing: -0.02em;
  }
  .landing-pitch {
    color: var(--text-muted);
    font-size: 1.05rem;
    margin: 0 0 1.5rem;
    max-width: 42rem;
  }
  .landing-features {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 0.75rem 1.25rem;
    margin: 0 0 1.75rem;
    padding: 0;
    list-style: none;
  }
  .landing-features li {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    color: var(--text);
    font-size: 0.9rem;
  }
  .landing-features .ti {
    font-size: 1.15rem;
    color: var(--text-muted);
    flex-shrink: 0;
  }
  .landing-ctas {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
  }
  .cta {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.6rem 1.1rem;
    border-radius: 0.5rem;
    font-size: 0.9rem;
    font-weight: 600;
    text-decoration: none;
    transition: all 0.15s ease;
    cursor: pointer;
  }
  .cta .ti { font-size: 1rem; }
  .cta.primary {
    background: var(--primary);
    border: 1px solid var(--primary);
    color: #fff;
  }
  .cta.primary:hover {
    background: var(--primary-hover);
    border-color: var(--primary-hover);
  }
  .cta.secondary {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text);
  }
  .cta.secondary:hover {
    border-color: var(--border-strong);
    background: var(--surface-2);
  }
  .catalog-header h2 {
    font-size: 1.35rem;
    margin: 0 0 0.35rem;
  }
  .catalog-header p {
    color: var(--text-muted);
    margin: 0 0 1.5rem;
  }

  @media (max-width: 600px) {
    .landing-hero { padding: 1.5rem 1.25rem; }
    .landing-ctas .cta { flex: 1 1 100%; justify-content: center; }
  }

  /* Primary navigation between listing types â reads as content tabs. */
  .kind-tabs {
    display: flex;
    gap: 1.5rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.25rem;
  }
  .kind-tabs button {
    background: none;
    border: none;
    padding: 0.6rem 0;
    margin-bottom: -1px;
    border-bottom: 2px solid transparent;
    font-size: 0.95rem;
    color: var(--text-faint);
    transition: color 0.15s ease, border-color 0.15s ease;
  }
  .kind-tabs button:hover { color: var(--text); }
  .kind-tabs button.active {
    color: var(--text);
    font-weight: 600;
    border-bottom-color: var(--primary);
  }

  /* Secondary filters, right-aligned and visually distinct from the tabs. */
  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin-bottom: 2rem;
    align-items: center;
    justify-content: flex-end;
  }
  .toggle {
    display: inline-flex;
    background: var(--surface-2);
    border-radius: 0.5rem;
    padding: 0.2rem;
    gap: 0.2rem;
  }
  .toggle button {
    background: transparent;
    border: none;
    padding: 0.45rem 0.9rem;
    border-radius: 0.4rem;
    font-size: 0.85rem;
    color: var(--text-faint);
    transition: all 0.15s ease;
  }
  .toggle button:hover { color: var(--text); }
  .toggle button.active {
    background: var(--surface);
    color: var(--text);
    font-weight: 600;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  }
  .verified-toggle {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    color: var(--text-muted);
    font-size: 0.85rem;
  }
  .cat-filter {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin: -0.75rem 0 1.75rem;
  }
  .cat-filter .filter-label {
    font-size: 0.8rem;
    color: var(--text-faint);
    align-self: center;
  }
  .cat-filter button {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text-muted);
    padding: 0.35rem 0.8rem;
    border-radius: 999px;
    font-size: 0.8rem;
    text-transform: capitalize;
    transition: all 0.15s ease;
  }
  .cat-filter button:hover { border-color: var(--border-strong); color: var(--text); }
  .cat-filter button.active {
    background: var(--primary);
    border-color: var(--primary);
    color: #fff;
    font-weight: 600;
  }
  .link {
    background: none;
    border: none;
    padding: 0;
    color: var(--text);
    text-decoration: underline;
    cursor: pointer;
    font: inherit;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
    gap: 1.25rem;
  }
  .state {
    text-align: center;
    padding: 4rem 2rem;
    color: var(--text-muted);
  }
  .state.error { color: var(--danger); }
  .state.empty h2 { margin: 0 0 0.5rem; color: var(--text); }
</style>
