#!/usr/bin/env bash
set -e

echo "==> Starting build..."
echo "==> Current directory: $(pwd)"
echo "==> Files here: $(ls -la)"

echo "==> Building frontend..."
cd frontend
npm install
VITE_API_URL= npm run build

echo "==> Frontend build output:"
ls -la dist/

echo "==> Copying frontend build to backend/static..."
rm -rf ../backend/static
mkdir -p ../backend/static
cp -r dist/. ../backend/static/

echo "==> backend/static contents:"
ls -la ../backend/static/

echo "==> Installing backend dependencies..."
cd ../backend
pip install -r requirements.txt

echo "==> Build complete!"