# Realms gOS - Dev Dummy Mode

This is a development-only version of the Realms frontend that enables fast UI development with hot reloading. It uses static dummy data instead of connecting to Internet Computer canisters, making it perfect for rapid UI iteration.

## Features

- ⚡ **Fast Hot Reloading**: Changes appear in browser within seconds
- 🎨 **Pure UI Development**: Focus on styling and components without backend dependencies
- 📊 **Static Dummy Data**: Pre-populated with realistic sample data
- 🔄 **Shared Components**: UI components are shared with the main dfx mode
- 🚫 **No IC Dependencies**: Completely independent of Internet Computer infrastructure

## Quick Start

1. **Install dependencies:**
   ```bash
   cd dev-dummy
   npm install
   ```

2. **Start development server:**
   ```bash
   npm run dev
   ```

3. **Open browser:**
   The app will automatically open at `http://localhost:3001`

## What's Included

### Extensions
- **Vault Manager**: Cryptocurrency wallet interface with transaction history
- **Citizen Dashboard**: Public services, personal data, and tax information
- **Notifications**: System notifications and alerts
- **Justice & Litigation**: Legal case management
- **Land Registry**: Property ownership and transfer management

### Features
- **Dashboard**: Overview with statistics and quick actions
- **Organizations**: Entity management and member tracking
- **Settings**: User preferences and system configuration
- **Multi-language Support**: English and Spanish translations

## Development Workflow

1. **Make UI changes** in shared components or dummy-specific files
2. **See changes instantly** in the browser (hot reloading)
3. **Test styling and interactions** without waiting for canister deployments
4. **Shared components automatically update** in both dummy and dfx modes

## File Structure

```
dev-dummy/
├── src/
│   ├── routes/                 # Page components
│   ├── lib/
│   │   ├── dummy-data/        # Static data for development
│   │   └── i18n/              # Internationalization
│   └── app.pcss               # Tailwind CSS styles
├── package.json               # Dependencies (no IC libraries)
├── vite.config.js            # Optimized for fast dev
└── README.md                  # This file
```

## Shared Components

The dummy mode is designed to share UI components with the main dfx mode. When you make styling changes to shared components, they automatically appear in both modes.

## Notes

- This is a development-only tool - not for production use
- All data is static and reset on page refresh
- Authentication is bypassed - all features are accessible
- No Internet Computer dependencies required
- Perfect for UI/UX development and testing
