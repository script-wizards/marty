#!/bin/bash

# Railway Deployment Script for Marty
set -e

echo "🚂 Deploying Marty to Railway..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    npm install -g @railway/cli
fi

# Check if logged in
if ! railway whoami &> /dev/null; then
    echo "🔐 Please login to Railway..."
    railway login
fi

# Link project if not already linked
if [ ! -f ".railway" ]; then
    echo "🔗 Linking project to Railway..."
    railway link
fi

# Deploy
echo "🚀 Deploying to Railway..."
railway up

# Get deployment URL
echo "📋 Getting deployment URL..."
railway status

echo "✅ Deployment complete!"
echo "🔍 Check your deployment at the URL above"
echo "📊 Monitor logs with: railway logs"
