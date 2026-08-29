<script lang="ts">
import { _, json } from "svelte-i18n";

const DEMO_URL = "https://demo.gos.earth";
const INVITE_URL = "https://tally.so/r/GxQ8QL";
const CONTACT_MAIL = "mailto:contact@realmsgos.org";
const DOCS_URL = "https://github.com/smart-social-contracts/realms/tree/main/docs";

const FEATURES = [
  { icon: "ti-world", title: "about.features.internetComputer.title", desc: "about.features.internetComputer.description" },
  { icon: "ti-shield", title: "about.features.secure.title", desc: "about.features.secure.description" },
  { icon: "ti-code", title: "about.features.developerFriendly.title", desc: "about.features.developerFriendly.description" },
  { icon: "ti-users", title: "about.features.multiRealm.title", desc: "about.features.multiRealm.description" },
  { icon: "ti-layers-intersect", title: "about.features.extensionSystem.title", desc: "about.features.extensionSystem.description" },
  { icon: "ti-bolt", title: "about.features.instantSetup.title", desc: "about.features.instantSetup.description" },
  { icon: "ti-robot", title: "about.features.aiGovernors.title", desc: "about.features.aiGovernors.description" },
];

const PRINCIPLES = [
  { n: "01", title: "about.principles.transparency.title", desc: "about.principles.transparency.description" },
  { n: "02", title: "about.principles.efficiency.title", desc: "about.principles.efficiency.description" },
  { n: "03", title: "about.principles.diversity.title", desc: "about.principles.diversity.description" },
  { n: "04", title: "about.principles.resilience.title", desc: "about.principles.resilience.description" },
];

$: identityFeatures = (Array.isArray($json("about.forPeople.identity.features"))
  ? $json("about.forPeople.identity.features")
  : []) as string[];
$: govBenefits = (Array.isArray($json("about.forInstitutions.governments.benefits"))
  ? $json("about.forInstitutions.governments.benefits")
  : []) as string[];
</script>

<article class="about">
  <header class="about-hero">
    <img class="mark" src="/images/logo_sphere_only.svg" alt="" width="72" height="80" />
    <p class="product">{$_('about.product_name')}</p>
    <h1>{$_('about.hero.title')}</h1>
    <ul class="bullets">
      <li>{$_('about.hero.subtitle1')}</li>
      <li>{$_('about.hero.subtitle2')}</li>
      <li>{$_('about.hero.subtitle3')}</li>
    </ul>
    <div class="ctas">
      <a class="cta primary" href={DEMO_URL} target="_blank" rel="noreferrer">{$_('about.hero.tryDemo')}</a>
      <a class="cta secondary" href={INVITE_URL} target="_blank" rel="noreferrer">{$_('about.hero.requestInvite')}</a>
    </div>
    <p class="alpha">{$_('about.hero.alphaBadge')}</p>
  </header>

  <section class="block" aria-labelledby="mission-title">
    <h2 id="mission-title">{$_('about.mission.title')}</h2>
    <p class="prose">{@html $_('about.mission.description')}</p>
  </section>

  <section class="block" aria-labelledby="principles-title">
    <h2 id="principles-title">{$_('about.principles.title')}</h2>
    <p class="lede">{$_('about.principles.intro')}</p>
    <div class="grid-2">
      {#each PRINCIPLES as p}
        <div class="card">
          <div class="num">{p.n}</div>
          <h3>{$_(p.title)}</h3>
          <p>{$_(p.desc)}</p>
        </div>
      {/each}
    </div>
  </section>

  <section class="block" id="features" aria-labelledby="features-title">
    <h2 id="features-title">{$_('about.features.title')}</h2>
    <p class="lede">{$_('about.features.subtitle')}</p>
    <div class="feature-list">
      {#each FEATURES as f}
        <div class="feature">
          <div class="icon" aria-hidden="true"><i class="ti {f.icon}"></i></div>
          <div>
            <h3>{$_(f.title)}</h3>
            <p>{$_(f.desc)}</p>
          </div>
        </div>
      {/each}
    </div>
  </section>

  <section class="block" id="forpeople" aria-labelledby="people-title">
    <h2 id="people-title">{$_('about.forPeople.title')}</h2>
    <p class="lede">{$_('about.forPeople.subtitle')}</p>
    <div class="grid-3">
      <div class="card">
        <div class="icon" aria-hidden="true"><i class="ti ti-fingerprint"></i></div>
        <h3>{$_('about.forPeople.identity.title')}</h3>
        <p>{$_('about.forPeople.identity.description')}</p>
        <ul class="checks">
          {#each identityFeatures as item}
            <li><i class="ti ti-circle-check" aria-hidden="true"></i><span>{item}</span></li>
          {/each}
        </ul>
      </div>
      <div class="card">
        <div class="icon" aria-hidden="true"><i class="ti ti-checkbox"></i></div>
        <h3>{$_('about.forPeople.participate.title')}</h3>
        <p>{$_('about.forPeople.participate.description')}</p>
      </div>
      <div class="card">
        <div class="icon" aria-hidden="true"><i class="ti ti-user-plus"></i></div>
        <h3>{$_('about.forPeople.create.title')}</h3>
        <p>{$_('about.forPeople.create.description')}</p>
      </div>
    </div>
  </section>

  <section class="block" id="forinstitutions" aria-labelledby="institutions-title">
    <h2 id="institutions-title">{$_('about.forInstitutions.title')}</h2>
    <p class="lede">{$_('about.forInstitutions.subtitle')}</p>
    <div class="card wide">
      <div class="icon" aria-hidden="true"><i class="ti ti-building-bank"></i></div>
      <h3>{$_('about.forInstitutions.governments.title')}</h3>
      <p>{$_('about.forInstitutions.governments.description')}</p>
      <h4>{$_('about.forInstitutions.benefits_heading')}</h4>
      <ul class="checks">
        {#each govBenefits as item}
          <li><i class="ti ti-circle-check" aria-hidden="true"></i><span>{item}</span></li>
        {/each}
      </ul>
    </div>
    <div class="ctas">
      <a class="cta primary" href={CONTACT_MAIL}>{$_('about.forInstitutions.cta')}</a>
    </div>
  </section>

  <section class="block" id="getstarted" aria-labelledby="started-title">
    <h2 id="started-title">{$_('about.getStarted.title')}</h2>
    <p class="lede">{$_('about.getStarted.subtitle')}</p>
    <div class="grid-3">
      <div class="card">
        <div class="icon" aria-hidden="true"><i class="ti ti-bolt"></i></div>
        <h3>{$_('about.getStarted.demo.title')}</h3>
        <p>{$_('about.getStarted.demo.description')}</p>
        <a class="cta primary" href={DEMO_URL} target="_blank" rel="noreferrer">{$_('about.getStarted.demo.button')}</a>
      </div>
      <div class="card">
        <div class="icon" aria-hidden="true"><i class="ti ti-mail"></i></div>
        <h3>{$_('about.getStarted.contact.title')}</h3>
        <p>{$_('about.getStarted.contact.description')}</p>
        <a class="cta secondary" href={CONTACT_MAIL}>{$_('about.getStarted.contact.button')}</a>
      </div>
      <div class="card">
        <div class="icon" aria-hidden="true"><i class="ti ti-code"></i></div>
        <h3>{$_('about.getStarted.developers.title')}</h3>
        <p>{$_('about.getStarted.developers.description')}</p>
        <a class="cta secondary" href={DOCS_URL} target="_blank" rel="noreferrer">{$_('about.getStarted.developers.button')}</a>
      </div>
    </div>
  </section>
</article>

<style>
  .about { display: flex; flex-direction: column; gap: 2.5rem; }
  .about-hero, .block {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0.75rem;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    padding: 2rem 2.25rem;
  }
  .about-hero { text-align: center; }
  .mark {
    display: block;
    margin: 0 auto 0.85rem;
    height: 72px;
    width: auto;
  }
  .product {
    margin: 0 0 0.35rem;
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  .about-hero h1, .block h2 {
    margin: 0 0 0.75rem;
    letter-spacing: -0.02em;
  }
  .about-hero h1 { font-size: clamp(1.5rem, 3vw, 2rem); }
  .block h2 { font-size: 1.45rem; }
  .bullets {
    list-style: none;
    margin: 0 auto 1.5rem;
    padding: 0;
    max-width: 40rem;
    text-align: left;
    color: var(--text-muted);
  }
  .bullets li { margin: 0.25rem 0; }
  .lede, .prose {
    color: var(--text-muted);
    max-width: 46rem;
    margin: 0 0 1.5rem;
  }
  .prose :global(strong) { color: var(--text); }
  .ctas {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
    justify-content: center;
  }
  .block .ctas { justify-content: flex-start; margin-top: 1.25rem; }
  .cta {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.6rem 1.1rem;
    border-radius: 0.5rem;
    font-size: 0.9rem;
    font-weight: 600;
    text-decoration: none;
  }
  .cta.primary { background: var(--primary); border: 1px solid var(--primary); color: #fff; }
  .cta.primary:hover { background: var(--primary-hover); }
  .cta.secondary { background: var(--surface); border: 1px solid var(--border); color: var(--text); }
  .cta.secondary:hover { background: var(--surface-2); border-color: var(--border-strong); }
  .alpha {
    display: inline-block;
    margin: 1rem 0 0;
    padding: 0.2rem 0.7rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    background: #FEF3C7;
    color: #92400E;
    border: 1px solid #FDE68A;
  }
  .grid-2, .grid-3 {
    display: grid;
    gap: 1rem;
  }
  .grid-2 { grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
  .grid-3 { grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
  .card {
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 0.65rem;
    padding: 1.25rem 1.35rem;
  }
  .card.wide { max-width: 46rem; }
  .card h3, .feature h3 { margin: 0 0 0.45rem; font-size: 1.05rem; }
  .card h4 { margin: 1rem 0 0.5rem; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-faint); }
  .card p, .feature p { margin: 0; color: var(--text-muted); }
  .num { font-weight: 700; color: var(--text-faint); margin-bottom: 0.35rem; }
  .feature-list { display: flex; flex-direction: column; gap: 1.25rem; }
  .feature { display: flex; gap: 1rem; align-items: flex-start; }
  .icon {
    width: 42px;
    height: 42px;
    border-radius: 0.6rem;
    background: var(--surface);
    border: 1px solid var(--border);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    color: var(--text);
  }
  .icon .ti { font-size: 1.2rem; }
  .checks { list-style: none; margin: 0.85rem 0 0; padding: 0; }
  .checks li {
    display: flex;
    gap: 0.45rem;
    align-items: flex-start;
    margin: 0.35rem 0;
    color: var(--text-muted);
    font-size: 0.9rem;
  }
  .checks .ti { color: var(--success); margin-top: 0.15rem; }
  .card .cta { margin-top: 1.1rem; }

  @media (max-width: 600px) {
    .about-hero, .block { padding: 1.5rem 1.25rem; }
    .ctas .cta { flex: 1 1 100%; }
  }
</style>
