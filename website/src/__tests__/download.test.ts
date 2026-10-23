import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { GET as downloadRoute, DEFAULT_DOWNLOAD_URL } from '@/app/api/download/route';
import { GET as statsRoute } from '@/app/api/stats/route';
import { siteConfig } from '@/config/site';

describe('Public Release & Distribution System', () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = { ...originalEnv };
  });

  it('1. /api/download redirects to default GitHub release URL with HTTP 307', async () => {
    delete process.env.DW_DOWNLOAD_URL;

    const response = await downloadRoute();
    assert.equal(response.status, 307);
    assert.equal(
      response.headers.get('location'),
      'https://github.com/princechouhan19/Digital-Wellbeing-PC/releases/latest/download/DigitalWellbeingSetup-4.1.0.exe'
    );
    assert.equal(
      DEFAULT_DOWNLOAD_URL,
      'https://github.com/princechouhan19/Digital-Wellbeing-PC/releases/latest/download/DigitalWellbeingSetup-4.1.0.exe'
    );
  });

  it('2. /api/download respects DW_DOWNLOAD_URL environment variable override', async () => {
    process.env.DW_DOWNLOAD_URL = 'https://custom-cdn.example.com/DigitalWellbeingSetup-4.1.0.exe';

    const response = await downloadRoute();
    assert.equal(response.status, 307);
    assert.equal(
      response.headers.get('location'),
      'https://custom-cdn.example.com/DigitalWellbeingSetup-4.1.0.exe'
    );
  });

  it('3. /api/stats returns accurate project metadata and Public Release stage', async () => {
    const response = await statsRoute();
    assert.equal(response.status, 200);

    const data = await response.json();
    assert.equal(data.project, 'Digital Wellbeing for Windows');
    assert.equal(data.version, '4.1.0');
    assert.equal(data.stage, 'Public Release');
    assert.equal(data.architecture, 'Local-First, Zero Cloud Sync, No Telemetry');
  });

  it('4. siteConfig is aligned with Public Release v4.1.0', () => {
    assert.equal(siteConfig.name, 'Digital Wellbeing');
    assert.equal(siteConfig.version, '4.1.0');
    assert.equal(siteConfig.stage, 'Public Release');
    assert.equal(
      siteConfig.links.releases,
      'https://github.com/princechouhan19/Digital-Wellbeing-PC/releases'
    );
  });

  it('5. Public download operates independently without external database or email dependencies', async () => {
    const response = await downloadRoute();
    assert.equal(response.status, 307);
    assert.equal(
      response.headers.get('location'),
      'https://github.com/princechouhan19/Digital-Wellbeing-PC/releases/latest/download/DigitalWellbeingSetup-4.1.0.exe'
    );
  });
});
