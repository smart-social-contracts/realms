import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import LanguageSwitcher from './components/LanguageSwitcher'
import { 
  Globe, 
  Shield, 
  Code, 
  Layers, 
  ArrowRight, 
  CheckCircle, 
  Terminal, 
  Github, 
  ExternalLink,
  Menu,
  X,
  Zap,
  Users,
  Building2,
  Vote,
  Wallet,
  Scale,
  BookOpen,
  ChevronRight
} from 'lucide-react'

function App() {
  const { t } = useTranslation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const features = [
    {
      icon: <Globe className="w-6 h-6" />,
      titleKey: "features.internetComputer.title",
      descKey: "features.internetComputer.description"
    },
    {
      icon: <Layers className="w-6 h-6" />,
      titleKey: "features.extensionSystem.title",
      descKey: "features.extensionSystem.description"
    },
    {
      icon: <Shield className="w-6 h-6" />,
      titleKey: "features.secure.title",
      descKey: "features.secure.description"
    },
    {
      icon: <Code className="w-6 h-6" />,
      titleKey: "features.developerFriendly.title",
      descKey: "features.developerFriendly.description"
    },
    {
      icon: <Users className="w-6 h-6" />,
      titleKey: "features.multiRealm.title",
      descKey: "features.multiRealm.description"
    },
    {
      icon: <Zap className="w-6 h-6" />,
      titleKey: "features.instantSetup.title",
      descKey: "features.instantSetup.description"
    }
  ]

  const extensions = [
    { nameKey: "extensions.adminDashboard.name", icon: <Building2 className="w-5 h-5" />, descKey: "extensions.adminDashboard.description" },
    { nameKey: "extensions.citizenDashboard.name", icon: <Users className="w-5 h-5" />, descKey: "extensions.citizenDashboard.description" },
    { nameKey: "extensions.vault.name", icon: <Wallet className="w-5 h-5" />, descKey: "extensions.vault.description" },
    { nameKey: "extensions.justice.name", icon: <Scale className="w-5 h-5" />, descKey: "extensions.justice.description" },
    { nameKey: "extensions.landRegistry.name", icon: <BookOpen className="w-5 h-5" />, descKey: "extensions.landRegistry.description" },
    { nameKey: "extensions.voting.name", icon: <Vote className="w-5 h-5" />, descKey: "extensions.voting.description" },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-primary-50 text-slate-900">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass-dark shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <img src="/logo_horizontal.svg" alt="Realms" className="h-10" />
            </div>
            
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-slate-600 hover:text-slate-900 transition-colors">For people</a>
              <a href="#features" className="text-slate-600 hover:text-slate-900 transition-colors">For developers</a>
              <LanguageSwitcher />
            </div>

            <button 
              className="md:hidden p-2"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="md:hidden glass-dark border-t border-slate-200">
            <div className="px-4 py-4 space-y-4">
              <a href="#features" className="block text-slate-600 hover:text-slate-900">For people</a>
              <a href="#features" className="block text-slate-600 hover:text-slate-900">For developers</a>
              <LanguageSwitcher />
            </div>
          </div>
        )}
      </nav>

      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
        {/* Background image */}
        <div className="absolute inset-0">
          <img 
            src="/hero-bg.jpg" 
            alt="Background" 
            className="w-full h-full object-cover opacity-40"
          />
          <div className="absolute inset-0 bg-gradient-to-br from-slate-50/60 via-white/50 to-primary-50/60"></div>
        </div>
        
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="bg-white/90 backdrop-blur-sm rounded-3xl shadow-xl p-8 sm:p-12 max-w-5xl mx-auto text-left">
            <div className="mb-8 flex justify-center">
              <img src="/logo_horizontal.svg" alt="Realms" className="h-20 sm:h-24 lg:h-28" />
            </div>
            
            <h1 className="text-lg sm:text-xl lg:text-2xl font-bold mb-6 text-center">
              <span className="text-slate-800">{t('hero.title')}</span>
            </h1>
            
            <div className="text-base sm:text-lg text-slate-600 mb-8 space-y-2">
              <p className="break-words">{t('hero.subtitle1')}</p>
              <p className="break-words">{t('hero.subtitle2')}</p>
              <p className="break-words">{t('hero.subtitle3')}</p>
            </div>
            
            <div className="flex justify-center">
              <a href="https://demo.realmsgos.org" target="_blank" rel="noopener noreferrer"
                 className="inline-flex items-center justify-center px-8 py-4 bg-primary-900 text-white rounded-xl font-semibold text-lg hover:bg-primary-800 transition-colors">
                {t('hero.tryDemo')}
              </a>
            </div>
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
          <ChevronRight className="w-6 h-6 rotate-90 text-slate-500" />
        </div>
      </section>

      {/* Mission Section */}
      <section className="py-24 bg-primary-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold mb-8 text-slate-800">
            {t('mission.title')}
          </h2>
          <p className="text-base text-slate-600 leading-relaxed text-justify" dangerouslySetInnerHTML={{ __html: t('mission.description') }} />
        </div>
      </section>

      {/* Design Principles Section */}
      <section className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4 text-center text-slate-800">
            {t('principles.title')}
          </h2>
          <p className="text-base text-slate-600 text-center mb-16 max-w-3xl mx-auto">
            {t('principles.intro')}
          </p>
          
          <div className="grid md:grid-cols-2 gap-8">
            <div className="bg-primary-50 rounded-2xl p-8">
              <div className="text-primary-500 font-semibold mb-2">01</div>
              <h3 className="text-lg sm:text-xl font-bold mb-4 text-slate-800">{t('principles.transparency.title')}</h3>
              <p className="text-base text-slate-600">
                {t('principles.transparency.description')}
              </p>
            </div>
            
            <div className="bg-primary-50 rounded-2xl p-8">
              <div className="text-primary-500 font-semibold mb-2">02</div>
              <h3 className="text-lg sm:text-xl font-bold mb-4 text-slate-800">{t('principles.efficiency.title')}</h3>
              <p className="text-base text-slate-600">
                {t('principles.efficiency.description')}
              </p>
            </div>
            
            <div className="bg-primary-50 rounded-2xl p-8">
              <div className="text-primary-500 font-semibold mb-2">03</div>
              <h3 className="text-lg sm:text-xl font-bold mb-4 text-slate-800">{t('principles.diversity.title')}</h3>
              <p className="text-base text-slate-600">
                {t('principles.diversity.description')}
              </p>
            </div>
            
            <div className="bg-primary-50 rounded-2xl p-8">
              <div className="text-primary-500 font-semibold mb-2">04</div>
              <h3 className="text-lg sm:text-xl font-bold mb-4 text-slate-800">{t('principles.resilience.title')}</h3>
              <p className="text-base text-slate-600">
                {t('principles.resilience.description')}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-24 relative">
        <div className="absolute inset-0 bg-dots opacity-30"></div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4 text-slate-800">
              {t('features.title')}
            </h2>
            <p className="text-base text-slate-600 max-w-2xl mx-auto">
              {t('features.subtitle')}
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div 
                key={index}
                className="glass-dark rounded-2xl p-8 hover:border-primary-400 transition-colors group"
              >
                <div className="w-12 h-12 rounded-xl bg-primary-100 flex items-center justify-center text-primary-700 mb-6 group-hover:scale-110 transition-transform">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-semibold mb-3 text-slate-800">{t(feature.titleKey)}</h3>
                <p className="text-base text-slate-600">{t(feature.descKey)}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Extensions Section */}
      <section id="extensions" className="py-24 relative bg-primary-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-3xl sm:text-4xl font-bold mb-6 text-slate-800">
                {t('extensions.title')}
              </h2>
              <p className="text-base text-slate-600 mb-8">
                {t('extensions.subtitle')}
              </p>
              
              <div className="space-y-4">
                {extensions.map((ext, index) => (
                  <div key={index} className="flex items-center gap-4 glass-dark rounded-xl p-4">
                    <div className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center text-primary-700">
                      {ext.icon}
                    </div>
                    <div>
                      <div className="font-semibold text-slate-800">{t(ext.nameKey)}</div>
                      <div className="text-base text-slate-600">{t(ext.descKey)}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative">
              <div className="absolute inset-0 bg-primary-200/40 rounded-3xl blur-3xl"></div>
              <div className="relative bg-slate-900 rounded-3xl p-8 shadow-2xl">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-white">
                  <Code className="w-5 h-5 text-primary-300" />
                  {t('extensions.architecture.title')}
                </h3>
                <pre className="text-sm text-slate-300 overflow-x-auto">
{`my-extension/
├── backend/
│   ├── __init__.py
│   └── entry.py        # Entry points
├── frontend/
│   ├── lib/extensions/
│   └── routes/
├── manifest.json       # Metadata
└── requirements.txt    # Dependencies`}
                </pre>
                <div className="mt-6 pt-6 border-t border-slate-700">
                  <div className="flex items-center gap-2 text-sm text-slate-400">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    {t('extensions.architecture.noOverhead')}
                  </div>
                  <div className="flex items-center gap-2 text-sm text-slate-400 mt-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    {t('extensions.architecture.atomicOps')}
                  </div>
                  <div className="flex items-center gap-2 text-sm text-slate-400 mt-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    {t('extensions.architecture.cliFirst')}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Quick Start Section */}
      <section id="quickstart" className="py-24 relative">
        <div className="absolute inset-0 bg-grid opacity-30"></div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4 text-slate-800">
              <span className="text-gradient">{t('quickStart.title')}</span>
            </h2>
            <p className="text-base text-slate-600 max-w-2xl mx-auto">
              {t('quickStart.subtitle')}
            </p>
          </div>

          <div className="max-w-3xl mx-auto space-y-6">
            {[
              { step: "1", titleKey: "quickStart.step1.title", codeKey: "quickStart.step1.code" },
              { step: "2", titleKey: "quickStart.step2.title", codeKey: "quickStart.step2.code" },
              { step: "3", titleKey: "quickStart.step3.title", codeKey: "quickStart.step3.code" },
            ].map((item, index) => (
              <div key={index} className="glass-dark rounded-2xl p-6">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-10 h-10 rounded-full bg-primary-900 flex items-center justify-center font-bold text-white">
                    {item.step}
                  </div>
                  <h3 className="text-xl font-semibold text-slate-800">{t(item.titleKey)}</h3>
                </div>
                <div className="bg-slate-900 rounded-xl p-4 font-mono text-sm">
                  <span className="text-slate-500">$ </span>
                  <span className="text-primary-300">{t(item.codeKey)}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Multi-realm option */}
          <div className="mt-12 max-w-3xl mx-auto">
            <div className="glass-dark rounded-2xl p-8 text-center">
              <p className="text-base text-slate-600 mb-6">
                {t('quickStart.mundus.description')}
              </p>
              <div className="bg-slate-900 rounded-xl p-4 font-mono text-sm text-left">
                <span className="text-slate-500">$ </span>
                <span className="text-primary-300">{t('quickStart.mundus.code')}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-slate-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <img src="/logo_horizontal.svg" alt="Realms GOS" className="h-12" />
            </div>
            
            <div className="flex items-center gap-6">
              <a href="https://github.com/smart-social-contracts/realms" target="_blank" rel="noopener noreferrer"
                 className="text-slate-500 hover:text-slate-900 transition-colors">
                <Github className="w-6 h-6" />
              </a>
              <a href="/docs"
                 className="text-slate-500 hover:text-slate-900 transition-colors flex items-center gap-2">
                <BookOpen className="w-5 h-5" />
                {t('footer.docs')}
              </a>
            </div>
          </div>
          
          <div className="mt-8 pt-8 border-t border-slate-200 text-center text-slate-500 text-sm">
            <a href="https://internetcomputer.org" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 hover:text-slate-700 transition-colors">
              {t('footer.builtOn')} <img src="/images/internet-computer-icp-logo.svg" alt="Internet Computer" className="inline h-4 w-4 mx-1" /> {t('footer.withLove')}
            </a>
            <div className="mt-2">{t('footer.openSource')}</div>
            <div className="mt-2 text-xs text-slate-400">
              Realms GOS {typeof __BUILD_VERSION__ !== 'undefined' ? __BUILD_VERSION__ : 'dev'} ({typeof __BUILD_COMMIT__ !== 'undefined' ? __BUILD_COMMIT__ : 'local'}) - {typeof __BUILD_TIME__ !== 'undefined' ? __BUILD_TIME__ : new Date().toISOString().replace('T', ' ').substring(0, 19)}{window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? ' - Local deployment' : ''}
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
