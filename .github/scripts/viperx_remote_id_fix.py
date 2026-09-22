from pathlib import Path
import sys

root = Path(sys.argv[1])
p = root / "ThreeOneOSFive/views/PatchProjectsView.swift"
s = p.read_text(encoding="utf-8")

# The uploaded source already contains the remote-ID isolation implementation.
# Make this build step idempotent: validate the exact invariants instead of
# trying to apply the same textual patch a second time.
checks = [
    'let serverID: String',
    '.appendingPathComponent(item.serverID)',
    'guard let serverID = stringValue(object["id"] ?? object["packageId"] ?? object["_id"])',
    'id: clientID,',
    'serverID: serverID,',
]
missing = [x for x in checks if x not in s]
if missing:
    raise SystemExit("VIPERX remote ID fix incomplete; missing: " + " | ".join(missing))

print("VIPERX remote ID isolation is already present and validated:", p)
