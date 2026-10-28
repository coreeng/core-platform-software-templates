const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { normalize } = require('../../scripts/security/report.cjs');

function fixture(fn) {
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'security-policy-'));
  try { fn(workspace); } finally { fs.rmSync(workspace, { recursive: true, force: true }); }
}
const report = { SchemaVersion: 2, Results: [{ Target: 'yarn.lock', Vulnerabilities: [
  { VulnerabilityID: 'CVE-2026-1234', PkgName: 'example', InstalledVersion: '1', Severity: 'HIGH' },
  { VulnerabilityID: 'CVE-2026-5678', PkgName: 'another', InstalledVersion: '1', FixedVersion: '2', Severity: 'LOW' }
]}] };

test('unfixed high vulnerabilities block, off remains an explicit report-only policy', () => fixture(workspace => {
  assert.equal(normalize(report, [], { workspace, threshold: 'high' }).blocking, 1);
  const result = normalize(report, [], { workspace, threshold: 'off' });
  assert.equal(result.blocking, 0);
  assert.equal(result.vulnerabilities.length, 2);
}));

test('P2P ignores retain evidence, expired and mismatched package ignores cannot suppress', () => fixture(workspace => {
  const file = path.join(workspace, '.p2p-security-ignore.yaml');
  for (const [extra, expected] of [['', 0], ['    expires: 2000-01-01\n', 1], ['    package: other\n', 1]]) {
    fs.writeFileSync(file, 'version: 1\nsource:\n  vulnerabilities:\n  - id: CVE-2026-1234\n    reason: fixture\n' + extra);
    const result = normalize(report, [], { workspace, threshold: 'high' });
    assert.equal(result.blocking, expected);
    assert.equal(result.ignored.vulnerabilities.length, 1 - expected);
  }
}));

test('image ignores apply only to the named image', () => fixture(workspace => {
  fs.writeFileSync(path.join(workspace, '.p2p-security-ignore.yaml'),
    'version: 1\nimages:\n- name: app\n  vulnerabilities:\n  - id: CVE-2026-1234\n    reason: fixture\n');
  assert.equal(normalize(report, [], { workspace, threshold: 'high', image: 'app' }).blocking, 0);
  assert.equal(normalize(report, [], { workspace, threshold: 'high', image: 'functional' }).blocking, 1);
}));

test('secrets expose only allowlisted metadata; verified secrets use critical policy', () => fixture(workspace => {
  const secret = JSON.stringify({ DetectorName: 'fixture', Verified: true, Raw: 'SENSITIVE_RAW',
    Redacted: 'SENSITIVE_REDACTED', ExtraData: { token: 'SENSITIVE_EXTRA' },
    SourceMetadata: { Data: { Filesystem: { file: path.join(workspace, 'config'), line: 2 } } } });
  const result = normalize({ SchemaVersion: 2 }, [secret], { workspace, threshold: 'high' });
  assert.equal(result.blocking, 1);
  assert.equal(result.secrets[0].file, 'config');
  assert.doesNotMatch(JSON.stringify(result), /SENSITIVE/);
  const unverified = secret.replace('"Verified":true', '"Verified":false');
  assert.equal(normalize({ SchemaVersion: 2 }, [unverified], { workspace, threshold: 'high' }).blocking, 0);
}));

test('malformed scanner output and invalid policy fail closed', () => fixture(workspace => {
  assert.throws(() => normalize({}, [], { workspace, threshold: 'high' }));
  assert.throws(() => normalize(report, ['SENSITIVE invalid json'], { workspace, threshold: 'high' }), /content withheld/);
  assert.throws(() => normalize(report, [], { workspace, threshold: 'typo' }));
}));

test('real rendered application names match P2P app and extended image suppressions', () => fixture(workspace => {
  fs.writeFileSync(path.join(workspace, 'Makefile'), 'P2P_APP_NAME ?= security-example\n');
  fs.writeFileSync(path.join(workspace, '.p2p-security-ignore.yaml'),
    'version: 1\nimages:\n- name: security-example\n  vulnerabilities:\n  - id: CVE-2026-1234\n    reason: app-only\n' +
    '- name: security-example-extended\n  vulnerabilities:\n  - id: CVE-2026-1234\n    reason: extended-only\n');
  for (const image of ['app', 'extended-test']) {
    assert.equal(normalize(report, [], { workspace, threshold: 'high', image }).blocking, 0);
  }
  assert.equal(normalize(report, [], { workspace, threshold: 'high', image: 'functional' }).blocking, 1);
}));
