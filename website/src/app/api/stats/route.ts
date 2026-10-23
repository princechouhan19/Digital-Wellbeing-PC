import { NextResponse } from 'next/server';

export const revalidate = 86400; // Cache for 24 hours

export async function GET() {
  return NextResponse.json({
    project: 'Digital Wellbeing for Windows',
    version: '3.1.6',
    stage: 'Public Beta',
    architecture: 'Local-First, Zero Cloud Sync, No Telemetry',
  });
}

