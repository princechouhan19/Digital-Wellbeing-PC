import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export const DEFAULT_DOWNLOAD_URL =
  'https://github.com/princechouhan19/Digital-Wellbeing-PC/releases/latest/download/DigitalWellbeingSetup-4.3.1.exe';

export async function GET() {
  const downloadUrl = (process.env.DW_DOWNLOAD_URL || DEFAULT_DOWNLOAD_URL).trim();
  return NextResponse.redirect(downloadUrl, 307);
}
