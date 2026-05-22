#!/bin/sh
set -e

# Run Prisma database schema migration/synchronization before starting the API
if [ "$DEBUG" != "true" ]; then
  echo "🚀 [Prod] Running database migrations with Prisma migrate deploy..."
  prisma migrate deploy || echo "⚠️ Prisma migrate deploy failed, trying db push..."
else
  echo "🔄 [Staging/Dev] Synchronizing database schema with Prisma db push..."
  prisma db push --accept-data-loss || echo "⚠️ Prisma db push skipped or failed, continuing..."
fi

# Start the application
echo "🚀 Starting CekInvest API Server under Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
