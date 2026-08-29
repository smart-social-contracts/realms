import React, { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Package,
  BookOpen,
  Bot,
  ExternalLink,
  Download,
  Heart,
  CheckCircle,
  Search,
  AlertTriangle,
} from 'lucide-react'
import SiteNav from '../components/SiteNav'
import { builtinExtensions, builtinCodices, builtinAssistants } from '../data/builtin-catalog'
import {
  ENVIRONMENTS,
  CATEGORY_KEYS,
  detectEnvironment,
  formatCategory,
  isItemVerified,
  itemCategories,
} from '../utils/environment'

const CATEGORY_LABELS = {
  all: 'All',
  administration: 'Administration',
  finances: 'Finances',
  governance: 'Governance',
  land_territory: 'Land Territory',
  public_services: 'Public Services',
  settings: 'Settings',
  other: 'Other',
}

const ENV_BANNER = {
  demo: 'bg-blue-100 text-blue-800 border-blue-200',
  staging: 'bg-amber-100 text-amber-800 border-amber-200',
  test: 'bg-red-100 text-red-800 border-red-200',
  production: 'bg-slate-100 text-slate-700 border-slate-200',
}

function resolveEnv(searchParams) {
  const envParam = searchParams.get('env')
  if (envParam && ENVIRONMENTS[envParam]) return envParam
  return detectEnvironment()
}

function MarketplacePage() {
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [tab, setTab] = useState('extensions')
  const [category, setCategory] = useState('all')
  // Default checked. Only ?verified=0 unchecks; no localStorage.
  const verifiedOnly = searchParams.get('verified') !== '0'
  const [searchQuery, setSearchQuery] = useState('')

  function setVerifiedOnly(checked) {
    const next = new URLSearchParams(searchParams)
    if (checked) next.set('verified', '1')
    else next.set('verified', '0')
    setSearchParams(next, { replace: true })
  }

  const envKey = useMemo(() => resolveEnv(searchParams), [searchParams])
  const config = ENVIRONMENTS[envKey]
  const showEnvBanner = envKey !== 'production'
  const isProductionComingSoon = envKey === 'production'

  const items = useMemo(() => {
    let data = []
    if (tab === 'extensions') data = builtinExtensions
    else if (tab === 'codices') data = builtinCodices
    else data = builtinAssistants

    if (category !== 'all') {
      data = data.filter((item) => itemCategories(item).includes(category))
    }
    if (verifiedOnly) {
      data = data.filter((item) => isItemVerified(item))
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      data = data.filter(
        (item) =>
          item.name.toLowerCase().includes(q) ||
          item.description.toLowerCase().includes(q) ||
          (item.categories || '').toLowerCase().includes(q),
      )
    }
    return data
  }, [tab, category, verifiedOnly, searchQuery])

  const tabs = [
    { id: 'extensions', label: t('marketplace.tabs.extensions', 'Extensions'), icon: Package, count: builtinExtensions.length },
    { id: 'codices', label: t('marketplace.tabs.codices', 'Codices'), icon: BookOpen, count: builtinCodices.length },
    { id: 'assistants', label: t('marketplace.tabs.assistants', 'Assistants'), icon: Bot, count: builtinAssistants.length },
  ]

  if (isProductionComingSoon) {
    return (
      <div className="min-h-screen">
        <SiteNav active="marketplace" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 pt-28">
          <div className="text-center">
            <h1 className="text-3xl sm:text-4xl font-bold mb-4 text-slate-800">
              {t('marketplace.title', 'Marketplace')}
            </h1>
            <p className="text-xl font-semibold text-primary-700 mb-4">
              {t('marketplace.comingSoon', 'Coming soon')}
            </p>
            <p className="text-base text-slate-600 max-w-2xl mx-auto">
              {t(
                'marketplace.comingSoonDescription',
                'Extensions, codices, and AI assistants for your realm will be available here soon.',
              )}
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <SiteNav active="marketplace" />

      {showEnvBanner && (
        <div className={`${ENV_BANNER[envKey] || ENV_BANNER.demo} border-b px-4 py-2 mt-16`}>
          <div className="max-w-7xl mx-auto flex items-center justify-center gap-2 text-sm font-medium">
            <AlertTriangle className="w-4 h-4" />
            <span>
              {t('marketplace.envBanner', 'You are viewing the {{env}} environment', { env: config.name })}
            </span>
            <span className="text-xs opacity-75">({config.marketplace})</span>
          </div>
        </div>
      )}

      <div className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 ${showEnvBanner ? '' : 'pt-28'}`}>
        <div className="text-center mb-12">
          <h1 className="text-3xl sm:text-4xl font-bold mb-4 text-slate-800">
            {t('marketplace.title', 'Marketplace')}
          </h1>
          <p className="text-base text-slate-600 max-w-2xl mx-auto">
            {t('marketplace.subtitle', 'Extensions, codices, and AI assistants to enhance your realm')}
          </p>
        </div>

        <div className="max-w-xl mx-auto mb-8">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              placeholder={t('marketplace.searchPlaceholder', 'Search extensions, codices, assistants...')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
        </div>

        <div className="flex justify-center gap-1 mb-8 border-b border-slate-200">
          {tabs.map(({ id, label, icon: Icon, count }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                tab === id
                  ? 'border-primary-600 text-primary-700'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
              <span className="ml-1 px-2 py-0.5 rounded-full text-xs bg-slate-100 text-slate-600">{count}</span>
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
          <div className="flex flex-wrap gap-2">
            {CATEGORY_KEYS.map((key) => (
              <button
                key={key}
                onClick={() => setCategory(key)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                  category === key
                    ? 'bg-primary-900 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {t(`marketplace.categories.${key}`, CATEGORY_LABELS[key] || key)}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
            <input
              type="checkbox"
              checked={verifiedOnly}
              onChange={(e) => setVerifiedOnly(e.target.checked)}
              className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
            />
            {t('marketplace.verifiedOnly', 'Verified only')}
          </label>
        </div>

        <div className="mb-6 text-sm text-slate-500">
          {t('marketplace.showing', 'Showing {{count}} {{type}}', { count: items.length, type: tab })}
        </div>

        {items.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            {t('marketplace.empty', 'No items found')}
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {items.map((item) => (
              <div
                key={item.extension_id || item.codex_id || item.assistant_id || item.name}
                className="glass-dark rounded-2xl p-6 hover:shadow-lg transition-all hover:scale-[1.02]"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="w-12 h-12 rounded-xl bg-primary-100 flex items-center justify-center text-2xl">
                    {item.icon || (tab === 'extensions' ? '📦' : tab === 'codices' ? '📜' : '🤖')}
                  </div>
                  {isItemVerified(item) && (
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                      <CheckCircle className="w-3 h-3" />
                      {t('marketplace.verified', 'Verified')}
                    </span>
                  )}
                </div>
                <h3 className="text-lg font-semibold text-slate-800 mb-2">{item.name}</h3>
                <p className="text-sm text-slate-600 mb-4 line-clamp-2">{item.description}</p>
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span className="px-2 py-1 bg-slate-100 rounded capitalize">
                    {formatCategory(item.categories) || 'General'}
                  </span>
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1">
                      <Download className="w-3 h-3" />
                      {item.installs || 0}
                    </span>
                    <span className="flex items-center gap-1">
                      <Heart className="w-3 h-3" />
                      {item.likes || 0}
                    </span>
                  </div>
                </div>
                <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-xs text-slate-400">v{item.version}</span>
                  <span className="text-xs text-slate-400">{item.developer}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-16 text-center">
          <a
            href={config.portal}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center px-8 py-4 bg-primary-900 text-white rounded-xl font-semibold text-lg hover:bg-primary-800 transition-colors"
          >
            {t('marketplace.launchRealm', 'Launch a realm')}
            <ExternalLink className="w-5 h-5 ml-2" />
          </a>
          <p className="mt-4 text-sm text-slate-500">
            {t('marketplace.fullExperience', 'Full marketplace experience available in the realm portal')}
          </p>
        </div>
      </div>
    </div>
  )
}

export default MarketplacePage
