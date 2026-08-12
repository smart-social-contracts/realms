import React from 'react'
import { Routes, Route } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import MarketplacePage from './pages/MarketplacePage'

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-primary-50 text-slate-900">
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/marketplace" element={<MarketplacePage />} />
      </Routes>
    </div>
  )
}

export default App
