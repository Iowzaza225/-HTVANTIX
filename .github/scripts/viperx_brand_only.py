from pathlib import Path
import json, re, shutil, sys

root = Path(sys.argv[1])
project = root / "ThreeOneOSFive"
assets_src = Path(__file__).resolve().parent.parent / "assets" / "VIPERXIcon.jpg"

RED = "Color(red: 0.94, green: 0.04, blue: 0.06)"

def read(p):
    return p.read_text(encoding="utf-8")

def write(p, s):
    p.write_text(s, encoding="utf-8")

# 1) Theme only: keep layout and logic untouched.
design = project / "views" / "DesignSystem.swift"
s = read(design)
s, n = re.subn(
    r"static\s+let\s+accent\s*=\s*Color\(\s*uiColor:\s*UIColor\s*\{.*?\}\s*\)",
    "static let accent = " + RED,
    s,
    count=1,
    flags=re.S,
)
if n == 0:
    s, n = re.subn(
        r"static\s+let\s+accent\s*=\s*[^\n]+",
        "static let accent = " + RED,
        s,
        count=1,
    )
if n == 0:
    raise RuntimeError("AppTheme.accent not found")

# Only change visible cyan/blue accent usages; semantic green/orange/red remain.
s = s.replace("Color.cyan", RED)
s = s.replace(".foregroundStyle(.cyan)", ".foregroundStyle(AppTheme.accent)")
s = s.replace(".tint(.cyan)", ".tint(AppTheme.accent)")
write(design, s)

# 2) Visible brand text only. Never touch internal HTVINTEX Server identifiers.
for p in project.rglob("*.swift"):
    s = read(p)
    old = s
    s = s.replace('Text("HTVINTEX")', 'Text("VIPERX")')
    s = s.replace('"HTVINTEX พร้อมใช้งาน"', '"VIPERX พร้อมใช้งาน"')
    s = s.replace('"HTVINTEX Settings"', '"VIPERX Settings"')
    s = s.replace('"HTVINTEX PREMIUM CONTROL"', '"VIPERX PREMIUM CONTROL"')
    if s != old:
        write(p, s)

# 3) Install the exact user-provided VIPERX SHOP artwork as a normal image asset.
imageset = project / "Assets.xcassets" / "VIPERXLicense.imageset"
imageset.mkdir(parents=True, exist_ok=True)
for f in imageset.iterdir():
    if f.is_file():
        f.unlink()
shutil.copyfile(assets_src, imageset / "VIPERXLicense.jpg")
(imageset / "Contents.json").write_text(json.dumps({
    "images": [{"filename": "VIPERXLicense.jpg", "idiom": "universal", "scale": "1x"}],
    "info": {"author": "xcode", "version": 1}
}, indent=2) + "\n", encoding="utf-8")

# 4) Change ONLY the logo on the key/license page.
license_files = []
for p in project.rglob("*.swift"):
    s = read(p)
    if "SECURE ACCESS" in s and ("License Key" in s or "license" in s.lower()):
        license_files.append(p)

if not license_files:
    raise RuntimeError("License/SECURE ACCESS view not found")

for p in license_files:
    s = read(p)
    old = s

    # Current UI uses AppLogo(size: ...). Replace that call only on this page.
    s, count = re.subn(
        r"AppLogo\s*\(\s*size:\s*([^\)]+)\)",
        r'''Image("VIPERXLicense")
                    .resizable()
                    .interpolation(.high)
                    .scaledToFill()
                    .frame(width: \1, height: \1)
                    .clipped()
                    .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 22, style: .continuous)
                            .stroke(AppTheme.accent.opacity(0.6), lineWidth: 1)
                    )
                    .shadow(color: AppTheme.accent.opacity(0.3), radius: 14, y: 4)''',
        s,
        count=1,
    )

    if count == 0:
        # Fallback for a zero-argument AppLogo.
        s, count = re.subn(
            r"AppLogo\s*\(\s*\)",
            '''Image("VIPERXLicense")
                    .resizable()
                    .interpolation(.high)
                    .scaledToFill()
                    .frame(width: 118, height: 118)
                    .clipped()
                    .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 22, style: .continuous)
                            .stroke(AppTheme.accent.opacity(0.6), lineWidth: 1)
                    )
                    .shadow(color: AppTheme.accent.opacity(0.3), radius: 14, y: 4)''',
            s,
            count=1,
        )

    if count == 0:
        marker = s.find("SECURE ACCESS")
        start = max(0, marker - 5000)
        end = min(len(s), marker + 9000)
        print("===== LICENSE VIEW SOURCE:", p, "=====")
        print(s[start:end])
        raise RuntimeError(f"License logo expression not matched in: {p}")

    write(p, s)
    print("VIPERX license logo patched:", p)

print("VIPERX branding-only patch complete")
