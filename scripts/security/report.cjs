// Scanner output is untrusted. Export only explicit fields; never persist raw secrets.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const ignores = require('./vendor/p2p-security-ignore.cjs');
const rank = { UNKNOWN: 0, LOW: 1, MEDIUM: 2, HIGH: 3, CRITICAL: 4 };

function normalize(trivy, secretLines, options) {
  if (!trivy || trivy.SchemaVersion !== 2 || (trivy.Results !== undefined && !Array.isArray(trivy.Results))) {
    throw new Error('Invalid or incomplete Trivy report');
  }
  const threshold = options.threshold;
  if (!['off', 'low', 'medium', 'high', 'critical'].includes(threshold)) throw new Error('Invalid blocking severity');
  const blocking = severity => threshold !== 'off' && rank[severity] >= rank[threshold.toUpperCase()];
  const vulnerabilities = [], licenses = [];
  for (const result of trivy.Results || []) {
    if (!result || typeof result !== 'object' ||
        (result.Vulnerabilities !== undefined && !Array.isArray(result.Vulnerabilities)) ||
        (result.Licenses !== undefined && !Array.isArray(result.Licenses))) throw new Error('Invalid Trivy result');
    for (const v of result.Vulnerabilities || []) {
      if (!v || typeof v.VulnerabilityID !== 'string' || typeof v.PkgName !== 'string') throw new Error('Invalid vulnerability');
      const severity = Object.hasOwn(rank, v.Severity) ? v.Severity : 'UNKNOWN';
      vulnerabilities.push({ id: v.VulnerabilityID, package: v.PkgName, installed: v.InstalledVersion,
        fixed: v.FixedVersion || '', severity, source: result.Target, blocking: blocking(severity) });
    }
    for (const l of result.Licenses || []) {
      licenses.push({ package: l.PkgName, license: l.Name, category: l.Category, severity: l.Severity,
        source: result.Target, blocking: false });
    }
  }
  const secrets = secretLines.filter(Boolean).map(line => {
    let f;
    try { f = JSON.parse(line); } catch { throw new Error('Invalid TruffleHog JSON (content withheld)'); }
    if (!f || typeof f !== 'object' || (!f.DetectorName && f.DetectorType === undefined)) {
      throw new Error('Invalid TruffleHog finding');
    }
    const detector = String(f.DetectorName || f.DetectorType);
    const data = f.SourceMetadata?.Data || {};
    const meta = options.image ? data.Docker || {} : data.Git || data.Filesystem || {};
    let file = String(meta.file || '');
    if (!options.image && path.isAbsolute(file)) file = path.relative(options.workspace, file);
    const identity = f.RawV2 || f.Raw || f.Redacted || `${detector}:${file}:${meta.line || '-'}:${meta.commit || '-'}`;
    const id = options.image ? ignores.p2pRedactedSecretId(identity)
      : crypto.createHash('sha256').update(`${detector}\0${identity}`).digest('hex');
    const status = f.Verified === true ? 'verified' : (f.VerificationError ? 'unknown' : 'unverified');
    return { id, detector, status, file, path: file, line: meta.line || null, commit: meta.commit || null,
      blocking: status === 'verified' && blocking('CRITICAL') };
  });
  let imageName = options.image;
  if (imageName && fs.existsSync(path.join(options.workspace, 'Makefile'))) {
    const match = fs.readFileSync(path.join(options.workspace, 'Makefile'), 'utf8').match(/^P2P_APP_NAME\s*\?=\s*([a-z0-9-]+)\s*$/m);
    if (!match) throw new Error('Missing rendered P2P application name');
    imageName = match[1] + (options.image === 'app' ? '' : '-' + (options.image === 'extended-test' ? 'extended' : options.image));
  }
  const ignore = options.image ? ignores.loadSecurityIgnore(options.workspace)
    : ignores.loadSourceSecurityIgnores(options.workspace);
  const splitV = options.image ? ignores.splitImageVulnerabilities(vulnerabilities, ignore, imageName)
    : ignores.splitSourceVulnerabilities(vulnerabilities, ignore);
  const splitS = options.image ? ignores.splitImageSecrets(secrets, ignore, imageName)
    : ignores.splitSourceSecrets(secrets, ignore);
  return { status: 'complete', threshold, vulnerabilities: splitV.active, licenses, secrets: splitS.active,
    ignored: { vulnerabilities: splitV.ignored, secrets: splitS.ignored },
    blocking: splitV.active.filter(v => v.blocking).length + splitS.active.filter(s => s.blocking).length };
}

if (require.main === module) {
  try {
    const [trivyFile, secretsFile, output, optionsFile] = process.argv.slice(2);
    const result = normalize(JSON.parse(fs.readFileSync(trivyFile, 'utf8')),
      fs.readFileSync(secretsFile, 'utf8').split('\n'), JSON.parse(fs.readFileSync(optionsFile, 'utf8')));
    fs.writeFileSync(output, JSON.stringify(result, null, 2) + '\n');
  } catch {
    // Do not echo parser exceptions: they can include raw scanner output.
    console.error('Security report validation failed; no raw secret output was retained.');
    process.exitCode = 2;
  }
}
module.exports = { normalize };
