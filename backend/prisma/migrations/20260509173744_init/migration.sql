-- CreateEnum
CREATE TYPE "InputType" AS ENUM ('CHAT', 'SCREENSHOT', 'URL');

-- CreateEnum
CREATE TYPE "RiskLevel" AS ENUM ('SAFE', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL');

-- CreateEnum
CREATE TYPE "FlagSeverity" AS ENUM ('LOW', 'MEDIUM', 'HIGH');

-- CreateEnum
CREATE TYPE "EmotionSignalType" AS ENUM ('URGENCY', 'FAKE_SCARCITY', 'FAKE_AUTHORITY', 'UNREALISTIC_RETURN', 'EMOTIONAL_PRESSURE', 'SOCIAL_PROOF_MANIPULATION');

-- CreateTable
CREATE TABLE "analyses" (
    "id" TEXT NOT NULL,
    "inputType" "InputType" NOT NULL,
    "rawInput" TEXT NOT NULL,
    "extractedText" TEXT,
    "riskScore" INTEGER NOT NULL DEFAULT 0,
    "riskLevel" "RiskLevel" NOT NULL DEFAULT 'SAFE',
    "summary" TEXT,
    "safeToInvest" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "analyses_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "red_flags" (
    "id" TEXT NOT NULL,
    "analysisId" TEXT NOT NULL,
    "category" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "severity" "FlagSeverity" NOT NULL,
    "confidence" DOUBLE PRECISION NOT NULL,
    "excerpt" TEXT,

    CONSTRAINT "red_flags_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "emotion_signals" (
    "id" TEXT NOT NULL,
    "analysisId" TEXT NOT NULL,
    "signalType" "EmotionSignalType" NOT NULL,
    "detected" BOOLEAN NOT NULL DEFAULT false,
    "description" TEXT,
    "examples" TEXT[],

    CONSTRAINT "emotion_signals_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "scam_patterns" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "category" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "keywords" TEXT[],
    "riskWeight" DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    "reportCount" INTEGER NOT NULL DEFAULT 0,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "scam_patterns_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_reports" (
    "id" TEXT NOT NULL,
    "inputType" "InputType" NOT NULL,
    "rawInput" TEXT NOT NULL,
    "isScam" BOOLEAN NOT NULL,
    "notes" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "user_reports_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "scam_patterns_name_key" ON "scam_patterns"("name");

-- AddForeignKey
ALTER TABLE "red_flags" ADD CONSTRAINT "red_flags_analysisId_fkey" FOREIGN KEY ("analysisId") REFERENCES "analyses"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "emotion_signals" ADD CONSTRAINT "emotion_signals_analysisId_fkey" FOREIGN KEY ("analysisId") REFERENCES "analyses"("id") ON DELETE CASCADE ON UPDATE CASCADE;
