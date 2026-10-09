import { chromium, request } from '@playwright/test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
const endpoint = process.env.SERVICE_ENDPOINT;
const backend = process.env.BACKEND_ENDPOINT;
assert(endpoint && backend, 'SERVICE_ENDPOINT and BACKEND_ENDPOINT are required');
const stage = process.env.TEST_STAGE || 'functional';
assert(['functional', 'integration', 'extended'].includes(stage));
const runId = process.env.TEST_RUN_ID || randomUUID();
assert(/^[0-9a-f-]{36}$/.test(runId));
const prefix = `${stage}:${runId}:`;
const text = `${prefix}browser note`;
const unicode = prefix + '😀'.repeat(200 - [...prefix].length);
const api = await request.newContext({ baseURL: endpoint, timeout: 15000 });
const internal = await request.newContext({ baseURL: backend, timeout: 15000 });
let browser;
let success = false;
try {
  browser = await chromium.launch({ args: ['--disable-dev-shm-usage'] });
  const page = await browser.newPage();
  await page.goto(endpoint);
  if (process.env.TEST_MODE !== 'verify') {
    await page.getByLabel('Note (1–200 Unicode characters)').fill(text);
    await page.getByRole('button', { name: 'Save note', exact: true }).click();
    await page.getByRole('listitem').filter({ hasText: text }).waitFor();
    const accepted = await api.post('/api/notes', { data: { text: unicode } });
    assert.equal(accepted.status(), 201, '200 Unicode codepoints accepted');
    for (const invalid of ['', unicode + '😀']) {
      const response = await api.post('/api/notes', { data: { text: invalid } });
      assert.equal(response.status(), 400, 'invalid length rejected');
    }
  }
  await page.getByRole('button', { name: 'Refresh', exact: true }).click();
  await page.getByRole('listitem').filter({ hasText: text }).waitFor();
  await page.reload();
  await page.getByRole('listitem').filter({ hasText: text }).waitFor();
  const response = await api.get('/api/notes');
  assert.equal(response.status(), 200);
  const notes = await response.json();
  assert(notes.some(n => n.text === text));
  assert(notes.some(n => n.text === unicode));
  success = true;
  console.log(`${stage}: browser create/list/refresh/reload, API validation and persistence passed (${runId})`);
} finally {
  // Cleanup only UUID rows bearing this run's exact owned text, never bulk-delete.
  if (!(success && process.env.TEST_PRESERVE === 'true')) {
    const response = await api.get('/api/notes');
    assert.equal(response.status(), 200, 'list owned records for cleanup');
    for (const note of await response.json()) {
      if (note.text !== text && note.text !== unicode) continue;
      assert(/^[0-9a-f-]{36}$/.test(note.id));
      const removed = await internal.delete(`/notes/${note.id}`, { data: { text: note.text } });
      assert.equal(removed.status(), 204, 'delete exact owned UUID and text');
    }
  }
  await browser?.close();
  await api.dispose();
  await internal.dispose();
}
