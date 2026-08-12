// Environment detection from hostname and per-env portal/canister config.

export const ENVIRONMENTS = {
  demo: {
    name: 'Demo',
    marketplace: 'ehyfg-wyaaa-aaaae-qg3qq-cai',
    fileRegistry: 'vi64l-3aaaa-aaaae-qj4va-cai',
    portal: 'https://demo.gos.earth',
  },
  staging: {
    name: 'Staging',
    marketplace: 'jji3o-uyaaa-aaaah-qreja-cai',
    fileRegistry: 'iebdk-kqaaa-aaaau-agoxq-cai',
    portal: 'https://staging.gos.earth',
  },
  test: {
    name: 'Test',
    marketplace: '2wldc-niaaa-aaaad-qlxga-cai',
    fileRegistry: 'uq2mu-kaaaa-aaaah-avqcq-cai',
    portal: 'https://test.gos.earth',
  },
  production: {
    name: 'Production',
    marketplace: null,
    fileRegistry: null,
    portal: null,
  },
}

export const CATEGORY_KEYS = [
  'all',
  'administration',
  'finances',
  'governance',
  'land_territory',
  'public_services',
  'settings',
  'other',
]

/** Detect deployment environment from hostname (or optional ?env=). */
export function detectEnvironment(searchParams) {
  const envParam =
    searchParams?.get?.('env') ||
    (typeof window !== 'undefined'
      ? new URLSearchParams(window.location.search).get('env')
      : null)
  if (envParam && ENVIRONMENTS[envParam]) return envParam

  const hostname = typeof window !== 'undefined' ? window.location.hostname : ''

  if (hostname.startsWith('demo.')) return 'demo'
  if (hostname.startsWith('test.')) return 'test'
  if (hostname.startsWith('staging.')) return 'staging'
  if (hostname === 'localhost' || hostname === '127.0.0.1') return 'demo'

  // realmsgos.org, www.realmsgos.org, and any other non-env hostname
  return 'production'
}

export function getEnvironmentConfig() {
  const env = detectEnvironment()
  return { key: env, ...ENVIRONMENTS[env] }
}

export function isItemVerified(item) {
  return Boolean(item?.verified || item?.verification_status === 'verified')
}

export function formatCategory(category) {
  if (!category || category === 'all') return ''
  return category.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function itemCategories(item) {
  const raw = item?.categories ?? ''
  return raw
    .split(',')
    .map((c) => c.trim().toLowerCase())
    .filter(Boolean)
}
