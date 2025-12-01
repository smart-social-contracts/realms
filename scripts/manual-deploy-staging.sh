#!/bin/bash
# Manual staging deployment script
# Called from GitHub Actions workflow: manual-deploy-staging.yml

set -e
set -x

TYPE="${1:-realm}"      # realm, registry, or mundus
MODE="${2:-upgrade}"    # reinstall or upgrade
NETWORK="${3:-staging}"  # staging or ic

echo "╭────────────────────────────────────────╮"
echo "│ 🚀 Deployment                          │"
echo "╰────────────────────────────────────────╯"
echo "📦 Type: $TYPE"
echo "🔄 Mode: $MODE"
echo "📡 Network: $NETWORK"
echo ""

case "$TYPE" in
    realm)
        echo "🏛️  Deploying single realm..."
        if [ "$MODE" = "reinstall" ]; then
            echo "   Reinstall mode: deploying with fresh data"
            realms realm create --manifest examples/demo/realm1/manifest.json --random --network $NETWORK --mode reinstall --deploy
        else
            echo "   Upgrade mode: deploying without data changes"
            realms realm create --manifest examples/demo/realm1/manifest.json --network $NETWORK --mode upgrade --deploy
        fi
        ;;
    registry)
        echo "📋 Deploying registry..."
        if [ "$MODE" = "reinstall" ]; then
            echo "   Reinstall mode: deploying with fresh state"
            realms registry create --manifest examples/demo/registry/manifest.json --network $NETWORK --deploy --mode reinstall
        else
            echo "   Upgrade mode: preserving existing data"
            realms registry create --manifest examples/demo/registry/manifest.json --network $NETWORK --deploy --mode upgrade
        fi
        ;;
    mundus)
        echo "🌍 Deploying full mundus (registry + all realms)..."
        if [ "$MODE" = "reinstall" ]; then
            echo "   Reinstall mode: deploying with fresh data"
            realms mundus create --manifest examples/demo/manifest.json --network $NETWORK --deploy --mode reinstall
        else
            echo "   Upgrade mode: deploying without data changes"
            realms mundus create --manifest examples/demo/manifest.json --network $NETWORK --deploy --mode upgrade
        fi
        ;;
    *)
        echo "❌ Error: Unknown deployment type '$TYPE'"
        echo "   Valid types: realm, registry, mundus"
        exit 1
        ;;
esac

echo ""
echo "✅ Deployment completed successfully!"
