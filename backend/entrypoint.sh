#!/bin/sh
set -e

# Run Prisma database schema pushes before starting the API
echo "🔄 Synchronizing database schema with Prisma db push..."
prisma db push --accept-data-loss || echo "⚠️ Prisma db push skipped or failed, continuing..."

# Start the application
echo "🚀 Starting CekInvest API Server under Uvicorn (Port: ${PORT:-8000})..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
