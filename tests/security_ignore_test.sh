#!/usr/bin/env bash
set -euo pipefail

ignore_files=()
while IFS= read -r file; do
  ignore_files+=("$file")
done < <(find . -name .p2p-security-ignore.yaml -not -path './.git/*' | sort)

if (( ${#ignore_files[@]} == 0 )); then
  echo "No P2P security ignore files found" >&2
  exit 1
fi

ruby -ryaml -rdate - "${ignore_files[@]}" <<'RUBY'
ARGV.each do |path|
  document = YAML.safe_load(File.read(path), permitted_classes: [Date], aliases: false)
  raise "#{path}: version must be 1" unless document['version'] == 1

  image_entries = Array(document['images']).flat_map do |image|
    Array(image['vulnerabilities']) + Array(image['secrets'])
  end
  source = document.fetch('source', {})
  entries = image_entries + Array(source['vulnerabilities']) + Array(source['secrets'])

  entries.each do |entry|
    raise "#{path}: ignore entry is missing an id" if entry['id'].to_s.empty?
    raise "#{path}: #{entry['id']} is missing a reason" if entry['reason'].to_s.empty?

    expiry = entry['expires']
    next if expiry.nil?

    expiry = Date.iso8601(expiry) if expiry.is_a?(String)
    raise "#{path}: #{entry['id']} expired on #{expiry}" if expiry < Date.today
  end
end
RUBY

echo "P2P security ignore validation passed"
