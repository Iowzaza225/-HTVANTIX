#!/usr/bin/env python3
"""Targeted VIPERXMODS license-identity repair; does not touch other app features.

Usage:
  python3 fix_viperx_license_appid.py /path/to/ThreeOneOSFive/App.swift

The source is intentionally edited only when all preflight assertions match.
"""
from pathlib import Path
import sys

assert len(sys.argv) == 2, "Pass path to the ORIGINAL App.swift from the ZIP"
p = Path(sys.argv[1])
if p.is_dir():
    p = p / "ThreeOneOSFive" / "App.swift"
assert p.name == "App.swift" and p.is_file(), p

s = p.read_text(encoding="utf-8")
old = '"appId": "starclinet"'
assert s.count(old) == 2, "Expected exactly two server-request appId fields"
assert s.count('prepareStarclinetLicenseScope') == 3, "Unexpected old license method shape"
assert 'defaults.string(forKey: scopeKey) != "starclinet"' in s
assert 'defaults.set("starclinet", forKey: scopeKey)' in s

s = s.replace(old, '"appId": "viperxmods"')
s = s.replace('prepareStarclinetLicenseScope', 'prepareViperxLicenseScope')
s = s.replace('defaults.string(forKey: scopeKey) != "starclinet"',
              'defaults.string(forKey: scopeKey) != "viperxmods"')
s = s.replace('defaults.set("starclinet", forKey: scopeKey)',
              'defaults.set("viperxmods", forKey: scopeKey)')

assert '"appId": "starclinet"' not in s
assert s.count('"appId": "viperxmods"') == 2
assert s.count('prepareViperxLicenseScope') == 3
assert 'defaults.string(forKey: scopeKey) != "viperxmods"' in s
assert 'defaults.set("viperxmods", forKey: scopeKey)' in s
p.write_text(s, encoding="utf-8")
print("PASS: VIPERX license request identity and local license scope repaired.")
