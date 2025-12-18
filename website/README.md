# Realms GOS Website

A modern website for Realms GOS - the Governance Operating System for the Internet Computer.

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Deployment to ICP

This website is configured as an ICP frontend canister.

```bash
# Start local replica
dfx start --background

# Deploy locally
dfx deploy website

# Deploy to mainnet
dfx deploy website --network ic
```

## Tech Stack

- **React** - UI framework
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **Lucide React** - Icons
- **Internet Computer** - Hosting platform
