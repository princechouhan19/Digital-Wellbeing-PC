import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { site } from '@/data/site';
import { siteConfig } from '@/config/site';
import robots from '@/app/robots';
import nextConfig from '../../next.config';

/**
 * The canonical host is one fact. These checks fail if a second source of truth
 * drifts away from it, or if a retired host stops redirecting.
 */
const CANONICAL = 'https://digital-wellbeing-pc.vercel.app';

describe('Canonical domain', () => {
  it('1. every site config value agrees on the canonical host', () => {
    assert.equal(site.url, CANONICAL);
    assert.equal(siteConfig.url, CANONICAL);
  });

  it('2. the sitemap advertised by robots.txt follows the canonical host', () => {
    assert.equal(robots().sitemap, `${CANONICAL}/sitemap.xml`);
  });

  it('3. both retired hosts answer with a permanent 301 to the canonical host', async () => {
    const redirects = (await nextConfig.redirects!()) ?? [];
    const byHost = new Map(redirects.map((rule) => [rule.has?.[0]?.value as string, rule]));

    for (const host of ['digitalwellbeing.vercel.app', 'notyourwellbeing.vercel.app']) {
      const rule = byHost.get(host);
      assert.ok(rule, `missing redirect for ${host}`);
      assert.equal(rule.statusCode, 301);
      assert.equal(rule.destination, `${CANONICAL}/:path*`);
    }
  });
});
