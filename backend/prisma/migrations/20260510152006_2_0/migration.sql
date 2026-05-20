/*
  Warnings:

  - A unique constraint covering the columns `[shareSlug]` on the table `analyses` will be added. If there are existing duplicate values, this will fail.

*/
-- CreateEnum
CREATE TYPE "OjkStatus" AS ENUM ('TERDAFTAR', 'TIDAK_TERDAFTAR', 'TERINDIKASI_ILEGAL', 'TIDAK_DITEMUKAN');

-- CreateEnum
CREATE TYPE "MessageRole" AS ENUM ('USER', 'ASSISTANT');

-- AlterTable
ALTER TABLE "analyses" ADD COLUMN     "domainAgeDays" INTEGER,
ADD COLUMN     "domainCountry" TEXT,
ADD COLUMN     "explanation" TEXT,
ADD COLUMN     "inputHash" TEXT,
ADD COLUMN     "mediaHitCount" INTEGER DEFAULT 0,
ADD COLUMN     "ojkEntityName" TEXT,
ADD COLUMN     "ojkStatus" "OjkStatus" DEFAULT 'TIDAK_DITEMUKAN',
ADD COLUMN     "shareSlug" TEXT,
ADD COLUMN     "trapQuestions" TEXT[];

-- CreateTable
CREATE TABLE "ojk_entity_cache" (
    "id" TEXT NOT NULL,
    "entityName" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "detail" TEXT,
    "sourceUrl" TEXT,
    "cachedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "ojk_entity_cache_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "chat_sessions" (
    "id" TEXT NOT NULL,
    "analysisId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "chat_sessions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "chat_messages" (
    "id" TEXT NOT NULL,
    "sessionId" TEXT NOT NULL,
    "role" "MessageRole" NOT NULL,
    "content" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "chat_messages_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "phone_reports" (
    "id" TEXT NOT NULL,
    "phoneNumber" TEXT NOT NULL,
    "reportCount" INTEGER NOT NULL DEFAULT 1,
    "lastSeen" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "notes" TEXT,

    CONSTRAINT "phone_reports_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "bank_account_reports" (
    "id" TEXT NOT NULL,
    "bankName" TEXT NOT NULL,
    "accountNumber" TEXT NOT NULL,
    "reportCount" INTEGER NOT NULL DEFAULT 1,
    "lastSeen" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "notes" TEXT,

    CONSTRAINT "bank_account_reports_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "ojk_entity_cache_entityName_key" ON "ojk_entity_cache"("entityName");

-- CreateIndex
CREATE UNIQUE INDEX "phone_reports_phoneNumber_key" ON "phone_reports"("phoneNumber");

-- CreateIndex
CREATE UNIQUE INDEX "bank_account_reports_bankName_accountNumber_key" ON "bank_account_reports"("bankName", "accountNumber");

-- CreateIndex
CREATE UNIQUE INDEX "analyses_shareSlug_key" ON "analyses"("shareSlug");

-- CreateIndex
CREATE INDEX "analyses_inputHash_idx" ON "analyses"("inputHash");

-- AddForeignKey
ALTER TABLE "chat_sessions" ADD CONSTRAINT "chat_sessions_analysisId_fkey" FOREIGN KEY ("analysisId") REFERENCES "analyses"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "chat_messages" ADD CONSTRAINT "chat_messages_sessionId_fkey" FOREIGN KEY ("sessionId") REFERENCES "chat_sessions"("id") ON DELETE CASCADE ON UPDATE CASCADE;
