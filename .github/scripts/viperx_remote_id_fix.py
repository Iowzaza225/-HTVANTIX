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

# VIPERX branding changed the server-origin name, while PatchProjectLibrary
# still recognized only the legacy "HTVINTEX Server" value. That made the
# first remote package install, then rejected later packages that target the
# same game paths as targetOccupied, leaving their rows permanently pending.
lib = root / "ThreeOneOSFive/helpers/PatchProjectLibrary.swift"
ls = lib.read_text(encoding="utf-8")
old = 'let isServerManaged = origin?.repositoryName == "HTVINTEX Server"'
new = 'let isServerManaged = origin?.repositoryName == "HTVINTEX Server" || origin?.repositoryName == "VIPERX"'
if old in ls:
    ls = ls.replace(old, new)
    lib.write_text(ls, encoding="utf-8")
elif new not in ls:
    raise SystemExit("VIPERX server-managed origin guard not found")
print("VIPERX server-managed import compatibility applied:", lib)
