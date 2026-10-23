import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export const DEFAULT_DOWNLOAD_URL =
  'https://github.com/digital-wellbeing/digital-wellbeing/releases/latest/download/DigitalWellbeingSetup-4.1.0.exe';

export async function GET() {
  const downloadUrl = (process.env.DW_DOWNLOAD_URL || DEFAULT_DOWNLOAD_URL).trim();
  return NextResponse.redirect(downloadUrl, 307);
}
