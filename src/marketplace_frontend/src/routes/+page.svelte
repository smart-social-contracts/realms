<script lang="ts">import { onMount } from "svelte";
import { browser } from "$app/environment";
import { goto } from "$app/navigation";
import { page } from "$app/stores";
import { _ } from "svelte-i18n";
import ItemCard from "$lib/components/ItemCard.svelte";
import SkeletonCard from "$lib/components/SkeletonCard.svelte";
import InfoTip from "$lib/components/InfoTip.svelte";
import { categories as parseCategories } from "$lib/format";
import { listingScreenshotUrls } from "$lib/file-registry-client";
import {
  marketplaceClient
} from "$lib/marketplace-client";
import { isAuthenticated, principalStore } from "$lib/auth";
import { CONFIG } from "$lib/config";
import { parseVerifiedOnlyParam, setVerifiedOnlySearchParam } from "$lib/verified-filter";
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
function stripBullet(text) {
  return String(text ?? "").replace(/^\s*•\s*/, "");
}
let kind = "ext";
let metric = "downloads";
let verifiedOnly = true;
let selectedCategory = "";
let selectedLanguage = "";
let loading = true;
let error = "";
let mounted = false;
let items = [];
let likedSet = new Set();
let searchQuery = "";
let catalogSection;
/** @type {{ value: number, key: string }[]} */
let catalogStats = [];
function scrollToCatalog(k) {
  if (k) kind = k;
  catalogSection?.scrollIntoView({ behavior: "smooth", block: "start" });
}
async function loadCatalogStats() {
  try {
    const status = await marketplaceClient.getStatus();
    catalogStats = [
      { value: status.extensions_count, key: "landing.stat_extensions" },
      { value: status.codices_count, key: "landing.stat_codices" },
      { value: status.assistants_count, key: "landing.stat_assistants" },
    ].filter((row) => Number(row.value) > 0);
  } catch {
    catalogStats = [];
  }
}
onMount(async () => {
  const params = $page.url.searchParams;
  const k = params.get("kind");
  if (k === "ext" || k === "codex" || k === "assistant") kind = k;
  const s = params.get("sort");
  if (s === "likes" || s === "downloads" || s === "newest") metric = s;
  verifiedOnly = parseVerifiedOnlyParam(params.get("verified"));
  if (kind === "ext") selectedCategory = params.get("category") ?? "";
  if (kind === "ext") selectedLanguage = params.get("lang") ?? "";
  searchQuery = params.get("q") ?? "";
  if (searchQuery.trim() && !k) {
    kind = await resolveKindForQuery(searchQuery.trim(), verifiedOnly);
  }
  mounted = true;
  void loadCatalogStats();
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
  setVerifiedOnlySearchParam(params, v);
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
  return listingScreenshotUrls(ext)[0] || "";
}
</script>

<svelte:head>
  <link
    rel="preload"
    as="image"
    type="image/avif"
    href="/images/hero-mosaic-1920.avif"
    imagesrcset="/images/hero-mosaic-1280.avif 1280w, /images/hero-mosaic-1920.avif 1920w"
    imagesizes="100vw"
  />
</svelte:head>

<section class="landing-hero" aria-labelledby="landing-title">
  <div class="landing-bg" aria-hidden="true">
    <picture>
      <source
        type="image/avif"
        sizes="100vw"
        srcset="/images/hero-mosaic-1280.avif 1280w, /images/hero-mosaic-1920.avif 1920w"
      />
      <source
        type="image/webp"
        sizes="100vw"
        srcset="/images/hero-mosaic-1280.webp 1280w, /images/hero-mosaic-1920.webp 1920w"
      />
      <img
        src="/images/hero-mosaic.jpg"
        srcset="/images/hero-mosaic-1280.jpg 1280w, /images/hero-mosaic.jpg 1920w"
        sizes="100vw"
        alt=""
        width="1920"
        height="1280"
        fetchpriority="high"
        decoding="async"
      />
    </picture>
    <div class="landing-overlay"></div>
  </div>
  <div class="landing-card">
    <div class="landing-wordmark">
      <img src="/images/logo_horizontal.svg" alt="Realms" />
    </div>
    <h1 id="landing-title" class="landing-tagline">{$_('about.hero.title')}</h1>
    <div class="landing-stanza">
      <p>{stripBullet($_('about.hero.subtitle1'))}</p>
      <p>{stripBullet($_('about.hero.subtitle2'))}</p>
      <p>{stripBullet($_('about.hero.subtitle3'))}</p>
    </div>
    <div class="landing-ctas">
      <a class="cta ghost" href="/about">{$_('landing.cta_what')}</a>
      <button type="button" class="cta ghost" on:click={() => scrollToCatalog('ext')}>
        {$_('landing.cta_browse')}
      </button>
      <a class="cta primary" href={CONFIG.portal_url || 'https://demo.gos.earth'} target="_blank" rel="noreferrer">
        {$_('landing.cta_launch')}
      </a>
    </div>
  </div>
  <p class="landing-credit">
    <span>{$_('landing.credit')}</span>
    <svg class="swiss" viewBox="0 0 32 32" aria-label={$_('landing.credit_country')}>
      <rect width="32" height="32" rx="2.5" fill="#D52B1E" />
      <path d="M13 7h6v6h6v6h-6v6h-6v-6H7v-6h6z" fill="#fff" />
    </svg>
  </p>
  <button type="button" class="scroll-flag" on:click={() => scrollToCatalog()}>
    <span class="scroll-line"></span>
    <span class="scroll-label">{$_('landing.scroll_hint')}</span>
  </button>
</section>

<section class="trust" aria-label={$_('landing.trust_label')}>
  <div class="trust-inner">
    {#each catalogStats as stat}
      <div class="trust-item">
        <span class="trust-num">{stat.value}</span>
        <span class="trust-label">{$_(stat.key)}</span>
      </div>
    {/each}
    <div class="trust-item">
      <span class="trust-num">100%</span>
      <span class="trust-label">{$_('landing.stat_onchain')}</span>
    </div>
    <div class="trust-item">
      <span class="trust-num">0</span>
      <span class="trust-label">{$_('landing.stat_servers')}</span>
    </div>
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
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 2.5rem 1.25rem 5.5rem;
    overflow: hidden;
  }
  .landing-bg {
    position: absolute;
    inset: 0;
  }
  .landing-bg picture {
    display: block;
    width: 100%;
    height: 100%;
  }
  .landing-bg img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0.45;
    transform: scale(1.08);
    animation: kenburns 32s ease-out forwards;
  }
  .landing-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(to bottom, #ffffff94, #fafafa66 45%, #ffffff9e);
  }
  .landing-card {
    position: relative;
    z-index: 1;
    width: min(46rem, 100%);
    padding: 2.75rem 2.75rem 2.35rem;
    background: #ffffffc7;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    border-radius: 0.75rem;
    box-shadow: 0 1px 2px #0000000a;
    text-align: center;
    animation: hero-rise 0.4s ease-out both;
  }
  .landing-card > :global(*) {
    animation: hero-fade 0.5s ease-out both;
  }
  .landing-wordmark {
    margin: 0 0 1.6rem;
    animation-delay: 0.14s;
  }
  .landing-wordmark img {
    display: block;
    margin: 0 auto;
    height: clamp(1.95rem, 4.2vw, 2.7rem);
    width: auto;
  }
  .landing-tagline {
    margin: 0 0 1.6rem;
    text-align: center;
    font-size: clamp(1.85rem, 4.2vw, 2.65rem);
    font-weight: 700;
    line-height: 1.15;
    letter-spacing: -0.02em;
    color: var(--text);
    text-wrap: balance;
    animation-delay: 0.22s;
  }
  .landing-stanza {
    margin: 0 auto 2rem;
    max-width: 32rem;
    font-size: 0.95rem;
    font-weight: 400;
    line-height: 1.65;
    text-align: center;
    color: var(--text-muted);
    animation-delay: 0.3s;
  }
  .landing-stanza p { margin: 0.15rem 0; }
  .landing-ctas {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 0.15rem 0.35rem;
    animation-delay: 0.38s;
  }
  .cta {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.95rem;
    font-weight: 600;
    text-decoration: none;
    transition: color 0.18s ease, background 0.18s ease, opacity 0.18s ease, border-color 0.18s ease;
    cursor: pointer;
  }
  .cta.primary {
    padding: 0.6rem 1.1rem;
    margin-left: 0.45rem;
    border-radius: 0.5rem;
    background: var(--primary);
    border: 1px solid var(--primary);
    color: #fff;
  }
  .cta.primary:hover {
    background: var(--primary-hover);
    border-color: var(--primary-hover);
  }
  .cta.ghost {
    padding: 0.6rem 0.95rem;
    border: none;
    background: none;
    color: var(--text-muted);
    font-weight: 600;
  }
  .cta.ghost:hover {
    color: var(--text);
    text-decoration: underline;
    text-underline-offset: 0.22em;
  }
  .landing-credit {
    position: absolute;
    z-index: 2;
    right: 1.5rem;
    bottom: 1.15rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin: 0;
    font-size: 0.7rem;
    font-weight: 400;
    color: var(--text-faint);
    letter-spacing: 0.01em;
    white-space: nowrap;
  }
  .landing-credit .swiss {
    flex: none;
    width: 0.82rem;
    height: 0.82rem;
    border-radius: 0.15rem;
    box-shadow: 0 1px 6px #00000059;
  }
  .scroll-flag {
    position: absolute;
    z-index: 2;
    left: 50%;
    bottom: 1.35rem;
    transform: translate(-50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.45rem;
    border: none;
    background: none;
    color: var(--text-muted);
    cursor: pointer;
    animation: scroll-fade 3.2s ease-in-out infinite;
  }
  .scroll-line {
    width: 1px;
    height: 1.65rem;
    background: currentColor;
  }
  .scroll-label {
    font-size: 0.62rem;
    font-weight: 500;
    letter-spacing: 0.22em;
    text-transform: uppercase;
  }
  .scroll-flag:hover { color: var(--text); }
  .trust {
    border-bottom: 1px solid var(--border);
    background: var(--surface);
  }
  .trust-inner {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1.5rem;
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 1.25rem 3.25rem;
  }
  .trust-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.15rem;
  }
  .trust-num {
    font-size: 1.45rem;
    font-weight: 600;
    letter-spacing: -0.03em;
    color: var(--text);
    font-variant-numeric: tabular-nums;
  }
  .trust-label {
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-faint);
  }
  @keyframes hero-fade {
    0% { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: none; }
  }
  @keyframes kenburns {
    0% { transform: scale(1.08); }
    to { transform: scale(1.16) translate(-1.2%, -0.8%); }
  }
  @keyframes hero-rise {
    0% { opacity: 0; transform: translateY(14px); }
    to { opacity: 1; transform: none; }
  }
  @keyframes scroll-fade {
    0%, to { opacity: 0.28; }
    50% { opacity: 0.9; }
  }
  @media (prefers-reduced-motion: reduce) {
    .landing-bg img,
    .landing-card,
    .landing-card > :global(*),
    .scroll-flag { animation: none; }
    .landing-bg img { transform: scale(1.06); }
  }
  .catalog {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2.5rem 1.5rem 0;
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
    .landing-card { padding: 1.85rem 1.25rem 1.6rem; width: min(64rem, 100%); }
    .cta.primary { margin-left: 0; flex: 1 1 100%; }
    .trust-inner { padding: 1.25rem 1rem; gap: 1rem 2.25rem; }
    .trust-num { font-size: 1.25rem; }
    .landing-credit {
      left: 50%;
      right: auto;
      bottom: 3.6rem;
      transform: translate(-50%);
      white-space: normal;
      text-align: center;
      max-width: calc(100% - 2rem);
    }
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
