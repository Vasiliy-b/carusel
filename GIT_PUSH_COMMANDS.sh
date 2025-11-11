#!/bin/bash
# Commands to push ADK repo to GitHub as PUBLIC repository

echo "🚀 Pushing ADK Content Generator to GitHub"
echo "=========================================="
echo ""

# Step 1: Initialize git if needed
if [ ! -d ".git" ]; then
    echo "📦 Initializing git repository..."
    git init
else
    echo "✓ Git repository already initialized"
fi

# Step 2: Add all files (gitignore will exclude sensitive files)
echo ""
echo "📝 Adding files (respecting .gitignore)..."
git add .

# Step 3: Create initial commit
echo ""
echo "💾 Creating commit..."
git commit -m "Initial commit: Multi-agent content generator with Web UI

- Multi-agent system for Instagram carousel generation
- Random post selection from Google Sheets
- 10-image carousel with 3D plasticine style
- Flask web UI for SMM team
- RunPod deployment ready
- Cost-safe: only charges on manual trigger"

# Step 4: Create GitHub repo (you'll need to do this manually)
echo ""
echo "=========================================="
echo "📋 NEXT STEPS - Do these on GitHub:"
echo "=========================================="
echo ""
echo "1. Go to: https://github.com/new"
echo ""
echo "2. Create repository with these settings:"
echo "   - Name: ADK (or your preferred name)"
echo "   - Description: Multi-agent Instagram carousel generator"
echo "   - Visibility: ✓ PUBLIC (so you can clone without login)"
echo "   - ✗ Do NOT initialize with README, .gitignore, or license"
echo ""
echo "3. After creating, GitHub will show you a URL like:"
echo "   https://github.com/YOUR_USERNAME/ADK.git"
echo ""
echo "4. Copy that URL and run:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/ADK.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "=========================================="
echo "✓ Your files are staged and committed!"
echo "✓ Ready to push once you add the remote"
echo "=========================================="
