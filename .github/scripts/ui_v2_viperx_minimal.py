from pathlib import Path
import json
import re
import shutil
import sys

root = Path(sys.argv[1])
project = root / "ThreeOneOSFive"
repo_assets = Path(__file__).resolve().parent.parent / "assets"

# IMPORTANT:
# Visual branding only. Do not touch patch/apply/restore/download/license logic.

red = "Color(red: 0.94, green: 0.04, blue: 0.06)"

def read(path):
    return path.read_text(encoding="utf-8")

def write(path, text):
    path.write_text(text, encoding="utf-8")

# 1) Global accent: keep the existing black/dark UI, change only the accent to red.
design = project / "views" / "DesignSystem.swift"
s = read(design)
pat = re.compile(
    r"static\s+let\s+accent\s*=\s*Color\(\s*uiColor:\s*UIColor\s*\{.*?\}\s*\)",
    re.S,
)
s, n = pat.subn("static let accent = " + red, s, count=1)
if n == 0:
    s, n = re.subn(
        r"static\s+let\s+accent\s*=\s*[^\n]+",
        "static let accent = " + red,
        s,
        count=1,
    )
if n == 0:
    raise RuntimeError("AppTheme.accent not found")

# Visible brand text only.
s = s.replace('Text("HTVINTEX")', 'Text("VIPERX")')
write(design, s)

# 2) Replace ONLY the in-app AppLogo used by the key/license screen.
# Do not alter the iOS AppIcon.
s = read(design)
start = s.find("struct AppLogo: View {")
if start < 0:
    raise RuntimeError("AppLogo view not found")
brace = s.find("{", start)
depth = 0
end = -1
for i in range(brace, len(s)):
    if s[i] == "{":
        depth += 1
    elif s[i] == "}":
        depth -= 1
        if depth == 0:
            end = i + 1
            break
if end < 0:
    raise RuntimeError("AppLogo closing brace not found")

replacement = '''struct AppLogo: View {
    let size: CGFloat

    var body: some View {
        Image("VIPERXKeyLogo")
            .resizable()
            .interpolation(.high)
            .scaledToFill()
            .frame(width: size, height: size)
            .clipped()
            .clipShape(RoundedRectangle(cornerRadius: size * 0.24, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: size * 0.24, style: .continuous)
                    .stroke(AppTheme.accent.opacity(0.55), lineWidth: 1)
            )
            .shadow(color: AppTheme.accent.opacity(0.28), radius: 14, y: 4)
    }
}
'''
s = s[:start] + replacement + s[end:]
write(design, s)

# Add the exact user-provided VIPERX image as a separate in-app asset.
asset_dir = project / "Assets.xcassets" / "VIPERXKeyLogo.imageset"
asset_dir.mkdir(parents=True, exist_ok=True)
for old in asset_dir.iterdir():
    if old.is_file():
        old.unlink()
shutil.copyfile(repo_assets / "VIPERXKeyLogo.jpg", asset_dir / "VIPERXKeyLogo.jpg")
(asset_dir / "Contents.json").write_text(
    json.dumps({
        "images": [
            {"filename": "VIPERXKeyLogo.jpg", "idiom": "universal", "scale": "1x"}
        ],
        "info": {"author": "xcode", "version": 1}
    }, indent=2) + "\n",
    encoding="utf-8",
)

# 3) Visible brand labels + black/red accent in UI files only.
for p in project.rglob("*.swift"):
    text = read(p)
    original = text

    # Exact visible strings only; internal HTVINTEX server/API identifiers remain unchanged.
    text = text.replace('"HTVINTEX พร้อมใช้งาน"', '"VIPERX พร้อมใช้งาน"')
    text = text.replace('"HTVINTEX Settings"', '"VIPERX Settings"')
    text = text.replace('"ตั้งค่า HTVINTEX"', '"ตั้งค่า VIPERX"')
    text = text.replace('"สมาชิก HTVINTEX"', '"สมาชิก VIPERX"')
    text = text.replace('Text("HTVINTEX")', 'Text("VIPERX")')

    # Visual-only cyan/blue accents become the shared red accent.
    text = text.replace('.tint(.cyan)', '.tint(AppTheme.accent)')
    text = text.replace('.foregroundStyle(.cyan)', '.foregroundStyle(AppTheme.accent)')
    text = text.replace('Color.cyan', red)

    if text != original:
        write(p, text)

print("VIPERX minimal branding applied: name text, black/red accent, key-screen image only")
