#!/bin/bash
# Manual staging deployment script
# Called from GitHub Actions workflow: manual-deploy-staging.yml

set -e
set -x

TYPE="${1:-realm}"        # realm, registry, or mundus
MODE="${2:-upgrade}"      # reinstall or upgrade
DEMO_DATA="${3:-no}"      # yes or no - populate with demo/fake data
NETWORK="${4:-staging}"   # staging or ic

# Build --no-demo-data flag if demo data is not requested
DEMO_FLAG=""
if [ "$DEMO_DATA" = "no" ]; then
    DEMO_FLAG="--no-demo-data"
fi

echo "╭────────────────────────────────────────╮"
echo "│ 🚀 Deployment                          │"
echo "╰────────────────────────────────────────╯"
echo "📦 Type: $TYPE"
echo "🔄 Mode: $MODE"
echo "📊 Demo data: $DEMO_DATA"
echo "📡 Network: $NETWORK"
echo ""

case "$TYPE" in
    realm)
        echo "🏛️  Deploying single realm..."
        if [ "$MODE" = "reinstall" ]; then
            echo "   Reinstall mode: deploying with fresh data"
            realms realm create --manifest examples/demo/realm1/manifest.json --random --network $NETWORK --mode reinstall --deploy $DEMO_FLAG
        else
            echo "   Upgrade mode: deploying without data changes"
            realms realm create --manifest examples/demo/realm1/manifest.json --network $NETWORK --mode upgrade --deploy $DEMO_FLAG
        fi
        ;;
    registry)
        echo "📋 Deploying registry..."
        if [ "$MODE" = "reinstall" ]; then
            echo "   Reinstall mode: deploying with fresh state"
            realms registry create --network $NETWORK --deploy --mode reinstall $DEMO_FLAG
        else
            echo "   Upgrade mode: preserving existing data"
            realms registry create --network $NETWORK --deploy --mode upgrade $DEMO_FLAG
        fi
        ;;
    mundus)
        echo "🌍 Deploying full mundus (registry + all realms)..."
        if [ "$MODE" = "reinstall" ]; then
            echo "   Reinstall mode: deploying with fresh data"
            realms mundus create --manifest examples/demo/manifest.json --network $NETWORK --deploy --mode reinstall $DEMO_FLAG
        else
            echo "   Upgrade mode: deploying without data changes"
            realms mundus create --manifest examples/demo/manifest.json --network $NETWORK --deploy --mode upgrade $DEMO_FLAG
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
