from pathlib import Path
import json, plistlib, re, shutil, subprocess, sys

root = Path(sys.argv[1])
project = root / "ThreeOneOSFive"
repo_assets = Path(__file__).resolve().parent.parent / "assets"

BRAND = "VIPERX"
VERSION = "1.1.9"
BUILD = "57"

def read(path: Path):
    return path.read_text(encoding="utf-8")

def write(path: Path, s: str):
    path.write_text(s, encoding="utf-8")

# ------------------------------------------------------------------
# 1) Global black/red theme. Keep the existing dark surfaces and replace
#    the cyan accent block with VIPERX red.
# ------------------------------------------------------------------
design = project / "views" / "DesignSystem.swift"
s = read(design)

red_expr = 'Color(red: 0.94, green: 0.055, blue: 0.075)'

# AppTheme.accent in the UI V2 source is a multi-line dynamic Color(uiColor:)
# declaration. Replace the WHOLE declaration; replacing just its first line
# leaves "uiColor: UIColor { ... }" orphaned and breaks Swift compilation.
accent_pat = re.compile(
    r'static\\s+let\\s+accent\\s*=\\s*Color\\(\\s*uiColor:\\s*UIColor\\s*\\{.*?\\}\\s*\\)',
    re.S,
)
s, accent_count = accent_pat.subn('static let accent = ' + red_expr, s, count=1)
if accent_count == 0:
    # Fallback for a future one-line AppTheme accent definition.
    s, accent_count = re.subn(
        r'static\\s+let\\s+accent\\s*=\\s*[^\\n]+',
        'static let accent = ' + red_expr,
        s,
        count=1,
    )
if accent_count == 0:
    raise RuntimeError("AppTheme.accent declaration not found")

# Any explicit cyan/blue design-system accent is also converted to red.
s = s.replace('Color.cyan', red_expr)
s = s.replace('.foregroundStyle(.cyan)', '.foregroundStyle(AppTheme.accent)')
s = s.replace('.tint(.cyan)', '.tint(AppTheme.accent)')

# Brand visible logo text.
s = s.replace('Text("HTVINTEX")', 'Text("VIPERX")')
s = s.replace('Text("PREMIUM CONTROL")', 'Text("VIPERX CONTROL")')
write(design, s)

# ------------------------------------------------------------------
# 2) Visible brand strings only. Do not touch backend/server IDs.
# ------------------------------------------------------------------
for rel in [
    "views/RepositoryHomeView.swift",
    "views/SettingsView.swift",
    "ContentView.swift",
]:
    p = project / rel
    if not p.exists():
        continue
    s = read(p)
    s = s.replace('Text("HTVINTEX")', 'Text("VIPERX")')
    s = s.replace('"HTVINTEX พร้อมใช้งาน"', '"VIPERX พร้อมใช้งาน"')
    s = s.replace('"HTVINTEX Settings"', '"VIPERX Settings"')
    s = s.replace('"ตั้งค่า HTVINTEX"', '"ตั้งค่า VIPERX"')
    s = s.replace('"สมาชิก HTVINTEX"', '"สมาชิก VIPERX"')
    s = s.replace('"HTVINTEX CONTROL"', '"VIPERX CONTROL"')
    s = s.replace('"HTVINTEX PREMIUM CONTROL"', '"VIPERX PREMIUM CONTROL"')
    write(p, s)

# Patch-list section label only; preserve HTVINTEX Server as internal origin key.
patch = project / "views" / "PatchProjectsView.swift"
if patch.exists():
    s = read(patch)
    s = s.replace('Text("HTVINTEX")', 'Text("VIPERX")')
    s = s.replace('Text("HTVINTEX SERVER")', 'Text("VIPERX")')
    write(patch, s)

# ------------------------------------------------------------------
# 3) License/key UI: force dark surface + red accents without changing logic.
# ------------------------------------------------------------------
for p in project.rglob("*.swift"):
    name = p.name.lower()
    s = read(p)
    if "license" not in name and "requiresLicenseGate" not in s and "licenseManager" not in s:
        continue

    original = s
    s = s.replace('Color.cyan', red_expr)
    s = s.replace('Color.blue', red_expr)
    s = s.replace('.tint(.blue)', '.tint(AppTheme.accent)')
    s = s.replace('.tint(.cyan)', '.tint(AppTheme.accent)')
    s = s.replace('.foregroundStyle(.blue)', '.foregroundStyle(AppTheme.accent)')
    s = s.replace('.foregroundStyle(.cyan)', '.foregroundStyle(AppTheme.accent)')
    s = s.replace('"HTVINTEX"', '"VIPERX"')
    s = s.replace('"3105"', '"VIPERX"')

    # Add dark appearance to the root app chain where safe.
    if p.name == "App.swift":
        if '.preferredColorScheme(.dark)' not in s:
            marker = '.environmentObject(licenseManager)'
            if marker in s:
                s = s.replace(marker, marker + '\n            .preferredColorScheme(.dark)\n            .tint(AppTheme.accent)', 1)

    if s != original:
        write(p, s)

# ------------------------------------------------------------------
# 4) Force iOS dark appearance and product version metadata.
# ------------------------------------------------------------------
plist_path = project / "Info.plist"
with plist_path.open("rb") as fh:
    plist = plistlib.load(fh)
plist["UIUserInterfaceStyle"] = "Dark"
plist["CFBundleDisplayName"] = BRAND
plist["CFBundleName"] = BRAND
plist["CFBundleShortVersionString"] = VERSION
plist["CFBundleVersion"] = BUILD
with plist_path.open("wb") as fh:
    plistlib.dump(plist, fh, fmt=plistlib.FMT_XML, sort_keys=False)

# ------------------------------------------------------------------
# 5) Install VIPERX artwork as the actual app icon.
#    Generate all legacy/modern sizes from the supplied user artwork.
# ------------------------------------------------------------------
src = repo_assets / "VIPERXIcon.jpg"
appicon = project / "Assets.xcassets" / "AppIcon.appiconset"
appicon.mkdir(parents=True, exist_ok=True)
for old in appicon.iterdir():
    if old.is_file():
        old.unlink()

sizes = [
    ("iphone", "20x20", "2x", 40),
    ("iphone", "20x20", "3x", 60),
    ("iphone", "29x29", "2x", 58),
    ("iphone", "29x29", "3x", 87),
    ("iphone", "40x40", "2x", 80),
    ("iphone", "40x40", "3x", 120),
    ("iphone", "60x60", "2x", 120),
    ("iphone", "60x60", "3x", 180),
    ("ipad", "20x20", "1x", 20),
    ("ipad", "20x20", "2x", 40),
    ("ipad", "29x29", "1x", 29),
    ("ipad", "29x29", "2x", 58),
    ("ipad", "40x40", "1x", 40),
    ("ipad", "40x40", "2x", 80),
    ("ipad", "76x76", "1x", 76),
    ("ipad", "76x76", "2x", 152),
    ("ipad", "83.5x83.5", "2x", 167),
    ("ios-marketing", "1024x1024", "1x", 1024),
]

images = []
for idiom, logical, scale, px in sizes:
    filename = f"VIPERX-{px}.png"
    dst = appicon / filename
    subprocess.run(
        ["/usr/bin/sips", "-s", "format", "png", "-z", str(px), str(px), str(src), "--out", str(dst)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    images.append({
        "idiom": idiom,
        "size": logical,
        "scale": scale,
        "filename": filename,
    })

(appicon / "Contents.json").write_text(
    json.dumps({"images": images, "info": {"author": "xcode", "version": 1}}, indent=2) + "\n"
)

print(f"VIPERX branding applied — {VERSION} build {BUILD}, black/red theme, app icon installed")
