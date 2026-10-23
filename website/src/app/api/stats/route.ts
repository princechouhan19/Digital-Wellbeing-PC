import { NextResponse } from 'next/server';

export const revalidate = 86400; // Cache for 24 hours

export async function GET() {
  return NextResponse.json({
    project: 'Digital Wellbeing for Windows',
    version: '4.2.0',
    stage: 'Public Release',
    architecture: 'Local-First, Zero Cloud Sync, No Telemetry',
  });
}

