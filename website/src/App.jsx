import { useState } from 'react'
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const features = [
    {
      icon: <Globe className="w-6 h-6" />,
      title: "Internet Computer Native",
      description: "Deploy fully on-chain governance systems on the Internet Computer blockchain with seamless integration."
    },
    {
      icon: <Layers className="w-6 h-6" />,
      title: "Extension System",
      description: "Powerful modular architecture allowing custom extensions for voting, treasury, identity, and more."
    },
    {
      icon: <Shield className="w-6 h-6" />,
      title: "Secure & Transparent",
      description: "Built-in security with transparent governance rules enforced by smart contracts."
    },
    {
      icon: <Code className="w-6 h-6" />,
      title: "Developer Friendly",
      description: "Python/Kybra backend with SvelteKit frontend. Simple CLI for rapid development and deployment."
    },
    {
      icon: <Users className="w-6 h-6" />,
      title: "Multi-Realm Support",
      description: "Deploy multiple interconnected governance systems with shared registry via Mundus."
    },
    {
      icon: <Zap className="w-6 h-6" />,
      title: "Instant Setup",
      description: "Get a full governance system running with a single command. Demo data included."
    }
  ]

  const extensions = [
    { name: "Admin Dashboard", icon: <Building2 className="w-5 h-5" />, desc: "Realm management & configuration" },
    { name: "Citizen Dashboard", icon: <Users className="w-5 h-5" />, desc: "Member-facing interface" },
    { name: "Vault", icon: <Wallet className="w-5 h-5" />, desc: "Treasury & ICRC-1 tokens" },
    { name: "Justice System", icon: <Scale className="w-5 h-5" />, desc: "Legal & dispute resolution" },
    { name: "Land Registry", icon: <BookOpen className="w-5 h-5" />, desc: "Property management" },
    { name: "Voting", icon: <Vote className="w-5 h-5" />, desc: "Proposals & governance" },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-primary-50 text-slate-900">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass-dark shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <img src="/logo_sphere_only.svg" alt="Realms" className="h-10 w-10" />
              <span className="text-xl font-bold">Realms GOS</span>
            </div>
            
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-slate-600 hover:text-slate-900 transition-colors">Features</a>
              <a href="#extensions" className="text-slate-600 hover:text-slate-900 transition-colors">Extensions</a>
              <a href="#quickstart" className="text-slate-600 hover:text-slate-900 transition-colors">Quick Start</a>
              <a href="https://github.com/smart-social-contracts/realms" target="_blank" rel="noopener noreferrer" 
                 className="flex items-center gap-2 text-slate-600 hover:text-slate-900 transition-colors">
                <Github className="w-5 h-5" />
                GitHub
              </a>
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
              <a href="#features" className="block text-slate-600 hover:text-slate-900">Features</a>
              <a href="#extensions" className="block text-slate-600 hover:text-slate-900">Extensions</a>
              <a href="#quickstart" className="block text-slate-600 hover:text-slate-900">Quick Start</a>
              <a href="https://github.com/smart-social-contracts/realms" target="_blank" rel="noopener noreferrer"
                 className="flex items-center gap-2 text-slate-600 hover:text-slate-900">
                <Github className="w-5 h-5" />
                GitHub
              </a>
            </div>
          </div>
        )}
      </nav>

      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
        {/* Background effects */}
        <div className="absolute inset-0 bg-grid opacity-30"></div>
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary-300/30 rounded-full blur-3xl"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent-300/30 rounded-full blur-3xl"></div>
        
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="mb-8">
            <img src="/logo_horizontal.svg" alt="Realms" className="h-20 sm:h-24 lg:h-28 mx-auto" />
          </div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-8">
            <span className="text-slate-800">The Governance Operating System</span>
          </h1>
          
          <div className="text-xl sm:text-2xl text-slate-600 max-w-3xl mx-auto mb-10 space-y-2">
            <p>• Launch a full public administration in seconds</p>
            <p>• Fully auditable. Fully transparent. AI-powered</p>
            <p>• Engineered to eliminate corruption and inefficiencies</p>
          </div>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a href="https://demo.realmsgos.org" target="_blank" rel="noopener noreferrer"
               className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-primary-900 text-white rounded-xl font-semibold text-lg hover:bg-primary-800 transition-colors">
              Try Demo
              <ArrowRight className="w-5 h-5" />
            </a>
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
          <h2 className="text-4xl sm:text-5xl font-bold mb-8 text-slate-800">
            Governance as It Should Be
          </h2>
          <p className="text-xl text-slate-600 leading-relaxed">
            <strong>Realms</strong> is a decentralized software platform for public administration — a Governance Operating System (GOS) 
            designed to deliver essential public services such as justice, social welfare, property registries, and more. 
            From small towns to entire nations, it empowers communities to design, run, and evolve their own governance systems — 
            free from the corruption and inefficiencies of traditional bureaucracy.
          </p>
        </div>
      </section>

      {/* Design Principles Section */}
      <section className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-4xl sm:text-5xl font-bold mb-16 text-center text-slate-800">
            Design Principles
          </h2>
          
          <div className="grid md:grid-cols-2 gap-8">
            <div className="bg-primary-50 rounded-2xl p-8">
              <div className="text-primary-500 font-semibold mb-2">01</div>
              <h3 className="text-xl font-bold mb-4 text-slate-800">Transparency</h3>
              <p className="text-base text-slate-600">
                Transparency builds trust between the government and the public, as users can see how processes are executed 
                and where resources, such as tax money, are allocated. Transparency also helps prevent corruption and 
                strengthens the legitimacy of institutions.
              </p>
            </div>
            
            <div className="bg-primary-50 rounded-2xl p-8">
              <div className="text-primary-500 font-semibold mb-2">02</div>
              <h3 className="text-xl font-bold mb-4 text-slate-800">Efficiency</h3>
              <p className="text-base text-slate-600">
                Efficiency involves delivering services effectively while minimizing costs and reducing waste. 
                This fosters a strong sense of fairness, reinforcing public confidence in the governance system. 
                As a result, users are more likely to support and comply with tax obligations.
              </p>
            </div>
            
            <div className="bg-primary-50 rounded-2xl p-8">
              <div className="text-primary-500 font-semibold mb-2">03</div>
              <h3 className="text-xl font-bold mb-4 text-slate-800">Diversity</h3>
              <p className="text-base text-slate-600">
                Diversity in governance ensures that a wide range of perspectives are represented. 
                This leads to more inclusive and equitable policies that cater to different societal needs, 
                fostering social cohesion and reducing marginalization.
              </p>
            </div>
            
            <div className="bg-primary-50 rounded-2xl p-8">
              <div className="text-primary-500 font-semibold mb-2">04</div>
              <h3 className="text-xl font-bold mb-4 text-slate-800">Resilience</h3>
              <p className="text-base text-slate-600">
                Resilience enables governance systems to respond to crises, adapt to changes, and recover from setbacks. 
                A resilient governance system ensures stability and continuity, even in times of stress, 
                protecting long-term societal wellbeing.
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
            <h2 className="text-4xl sm:text-5xl font-bold mb-4 text-slate-800">
              Why <span className="text-gradient">Realms</span>?
            </h2>
            <p className="text-xl text-slate-600 max-w-2xl mx-auto">
              Everything you need to build modern governance infrastructure
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
                <h3 className="text-xl font-semibold mb-3 text-slate-800">{feature.title}</h3>
                <p className="text-base text-slate-600">{feature.description}</p>
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
              <h2 className="text-4xl sm:text-5xl font-bold mb-6 text-slate-800">
                Modular <span className="text-gradient">Extensions</span>
              </h2>
              <p className="text-xl text-slate-600 mb-8">
                Realms comes with a powerful extension system. Add features like treasury management, 
                voting systems, identity verification, and more. Build your own or use community extensions.
              </p>
              
              <div className="space-y-4">
                {extensions.map((ext, index) => (
                  <div key={index} className="flex items-center gap-4 glass-dark rounded-xl p-4">
                    <div className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center text-primary-700">
                      {ext.icon}
                    </div>
                    <div>
                      <div className="font-semibold text-slate-800">{ext.name}</div>
                      <div className="text-base text-slate-600">{ext.desc}</div>
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
                  Extension Architecture
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
                    No inter-canister overhead
                  </div>
                  <div className="flex items-center gap-2 text-sm text-slate-400 mt-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    Atomic operations with shared memory
                  </div>
                  <div className="flex items-center gap-2 text-sm text-slate-400 mt-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    CLI-first development workflow
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
            <h2 className="text-4xl sm:text-5xl font-bold mb-4 text-slate-800">
              <span className="text-gradient">Quick Start</span>
            </h2>
            <p className="text-xl text-slate-600 max-w-2xl mx-auto">
              Get your governance system running in minutes
            </p>
          </div>

          <div className="max-w-3xl mx-auto space-y-6">
            {[
              { step: "1", title: "Install the CLI", code: "pip install realms-cli" },
              { step: "2", title: "Create a Realm", code: "realms realm create --random --citizens 50 --deploy" },
              { step: "3", title: "Access Your Realm", code: "# Frontend: http://<canister_id>.localhost:8000" },
            ].map((item, index) => (
              <div key={index} className="glass-dark rounded-2xl p-6">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-10 h-10 rounded-full bg-primary-900 flex items-center justify-center font-bold text-white">
                    {item.step}
                  </div>
                  <h3 className="text-xl font-semibold text-slate-800">{item.title}</h3>
                </div>
                <div className="bg-slate-900 rounded-xl p-4 font-mono text-sm">
                  <span className="text-slate-500">$ </span>
                  <span className="text-primary-300">{item.code}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Multi-realm option */}
          <div className="mt-12 max-w-3xl mx-auto">
            <div className="glass-dark rounded-2xl p-8 text-center">
              <h3 className="text-xl font-bold mb-4 text-slate-800">Need Multiple Realms?</h3>
              <p className="text-base text-slate-600 mb-6">
                Deploy a multi-realm ecosystem with shared registry using Mundus
              </p>
              <div className="bg-slate-900 rounded-xl p-4 font-mono text-sm text-left">
                <span className="text-slate-500">$ </span>
                <span className="text-primary-300">realms mundus create --deploy</span>
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
              <img src="/logo_sphere_only.svg" alt="Realms" className="h-10 w-10" />
              <div>
                <div className="font-bold">Realms GOS</div>
                <div className="text-sm text-slate-500">Governance Operating System</div>
              </div>
            </div>
            
            <div className="flex items-center gap-6">
              <a href="https://github.com/smart-social-contracts/realms" target="_blank" rel="noopener noreferrer"
                 className="text-slate-500 hover:text-slate-900 transition-colors">
                <Github className="w-6 h-6" />
              </a>
              <a href="https://docs.realms.dev" target="_blank" rel="noopener noreferrer"
                 className="text-slate-500 hover:text-slate-900 transition-colors flex items-center gap-2">
                <BookOpen className="w-5 h-5" />
                Docs
              </a>
            </div>
          </div>
          
          <div className="mt-8 pt-8 border-t border-slate-200 text-center text-slate-500 text-sm">
            Built for the Internet Computer • Open Source • MIT License
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
