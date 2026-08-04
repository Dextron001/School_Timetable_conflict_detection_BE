#!/usr/bin/env bash
set -e

echo "==> Building frontend..."
cd frontend
npm install
VITE_API_URL= npm run build

echo "==> Copying frontend build to backend/static..."
rm -rf ../backend/static
mkdir -p ../backend/static
cp -r dist/. ../backend/static/

echo "==> Installing backend dependencies..."
cd ../backend
pip install -r requirements.txt

echo "==> Build complete!"