from pathlib import Path
import base64, json, re, shutil, subprocess, sys, tempfile

root = Path(sys.argv[1])
project = root / "ThreeOneOSFive"
assets = project / "Assets.xcassets"
repo_assets = Path(__file__).resolve().parent.parent / "assets"

def install_imageset(name: str, source_name: str):
    target = assets / f"{name}.imageset"
    target.mkdir(parents=True, exist_ok=True)

    # Copy the verified square artwork byte-for-byte. Do not run it through
    # sips/ImageIO; that conversion caused the lower half of the icon to render
    # as a gray placeholder on-device.
    src = repo_assets / source_name
    dst_name = f"{name}.jpg"
    dst = target / dst_name
    shutil.copyfile(src, dst)

    contents = {
        "images": [
            {"filename": dst_name, "idiom": "universal", "scale": "1x"},
        ],
        "info": {"author": "xcode", "version": 1},
    }
    (target / "Contents.json").write_text(json.dumps(contents, indent=2) + "\n")

install_imageset("FreeFireIcon", "FreeFireIcon.jpg")
install_imageset("FreeFireMaxIcon", "FreeFireMaxIcon.jpg")

# Free Fire normal has shown a partial/gray decode when compiled through
# Assets.xcassets on-device. Re-encode that source as PNG and embed the bytes
# directly in Swift so this one icon bypasses Asset Catalog decoding entirely.
with tempfile.TemporaryDirectory() as tmpdir:
    ff_png = Path(tmpdir) / "FreeFireIcon.inline.png"
    subprocess.run(
        ["/usr/bin/sips", "-s", "format", "png", "-z", "160", "160",
         str(repo_assets / "FreeFireIcon.jpg"), "--out", str(ff_png)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    ff_inline_b64 = base64.b64encode(ff_png.read_bytes()).decode("ascii")

# Shared game artwork view.
design = project / "views" / "DesignSystem.swift"
s = design.read_text()
if "struct HTVGameIcon: View" not in s:
    if "import UIKit" not in s:
        s = s.replace("import SwiftUI", "import SwiftUI\nimport UIKit", 1)

    insert = f'''
private enum HTVGameArtwork {{
    static let freeFireBase64 = "{ff_inline_b64}"
}}

struct HTVGameIcon: View {{
    let game: String
    var size: CGFloat = 44

    private var isMax: Bool {{
        game.lowercased().contains("max")
    }}

    @ViewBuilder
    private var artwork: some View {{
        if isMax {{
            Image("FreeFireMaxIcon")
                .resizable()
        }} else if let data = Data(base64Encoded: HTVGameArtwork.freeFireBase64),
                  let image = UIImage(data: data) {{
            Image(uiImage: image)
                .resizable()
        }} else {{
            Image("FreeFireIcon")
                .resizable()
        }}
    }}

    var body: some View {{
        artwork
            .interpolation(.high)
            .antialiased(true)
            .scaledToFill()
            .frame(width: size, height: size)
            .clipped()
            .clipShape(RoundedRectangle(cornerRadius: size * 0.24, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: size * 0.24, style: .continuous)
                    .stroke(AppTheme.accent.opacity(0.26), lineWidth: 1)
            )
            .shadow(color: AppTheme.accent.opacity(0.14), radius: 8, y: 3)
            .accessibilityHidden(true)
    }}
}}

'''
    anchor = "struct AppLogo: View {"
    if anchor not in s:
        raise RuntimeError("DesignSystem AppLogo anchor not found")
    s = s.replace(anchor, insert + anchor, 1)
design.write_text(s)

# Home game cards: use the supplied game artwork instead of SF Symbols.
home = project / "views" / "RepositoryHomeView.swift"
s = home.read_text()
s = s.replace('''                                systemImage: "scope",\n                                game: "ff",''',
              '''                                game: "ff",''', 1)
s = s.replace('''                                systemImage: "bolt.shield.fill",\n                                game: "ffmax",''',
              '''                                game: "ffmax",''', 1)
s = s.replace('''        systemImage: String,\n        game: String,''',
              '''        game: String,''', 1)

pattern = re.compile(r'''                    ZStack \{\n                        RoundedRectangle\(cornerRadius: 18, style: \.continuous\)\n                            \.fill\(\n                                LinearGradient\(\n                                    colors: \[AppTheme\.accent\.opacity\(0\.22\), AppTheme\.accent\.opacity\(0\.07\)\],\n                                    startPoint: \.topLeading,\n                                    endPoint: \.bottomTrailing\n                                \)\n                            \)\n                            \.frame\(width: 62, height: 62\)\n                        Image\(systemName: systemImage\)\n                            \.font\(\.system\(size: 26, weight: \.black\)\)\n                            \.foregroundStyle\(AppTheme\.accent\)\n                    \}''')
s, n = pattern.subn('                    HTVGameIcon(game: game, size: 62)', s, count=1)
if n == 0 and "HTVGameIcon(game: game, size: 62)" not in s:
    raise RuntimeError("Home game icon block not found")
home.write_text(s)

# Patch list cards: show the actual game artwork on both pending and ready rows.
patch = project / "views" / "PatchProjectsView.swift"
s = patch.read_text()

# Pending row may be base UI V2 or the retry/error UI generated by another build patch.
pending_start = s.find("    private func serverPendingRow")
pending_end = s.find("    @ViewBuilder\n    private func serverPatchRow", pending_start)
if pending_start < 0 or pending_end < 0:
    raise RuntimeError("serverPendingRow range not found")
pending = s[pending_start:pending_end]
pending = re.sub(
    r'''            AppRowIcon\(\n                systemName: failure == nil \? "arrow\.down\.circle\.fill" : "exclamationmark\.triangle\.fill",\n                tint: failure == nil \? AppTheme\.accent : \.orange,\n                frameSize: 42\n            \)''',
    '            HTVGameIcon(game: remote.game ?? "ff", size: 42)',
    pending,
    count=1,
)
pending = pending.replace('            AppRowIcon(systemName: "arrow.down.circle.fill", frameSize: 42)',
                          '            HTVGameIcon(game: remote.game ?? "ff", size: 42)', 1)
s = s[:pending_start] + pending + s[pending_end:]

row_start = s.find("    private func serverPatchRow")
row_end = s.find("\n    @ViewBuilder", row_start + 20)
if row_start < 0:
    raise RuntimeError("serverPatchRow not found")
if row_end < 0:
    row_end = s.find("\n    private func", row_start + 20)
row = s[row_start:row_end]
row = re.sub(
    r'''                AppRowIcon\(\n                    systemName: isActive \? "bolt\.shield\.fill" : "shippingbox\.fill",\n                    tint: isActive \? \.green : AppTheme\.accent,\n                    symbolSize: 19,\n                    frameSize: 44\n                \)''',
    '                HTVGameIcon(game: remote.game ?? "ff", size: 44)',
    row,
    count=1,
)
if 'HTVGameIcon(game: remote.game ?? "ff", size: 44)' not in row:
    raise RuntimeError("serverPatchRow icon block not found")
s = s[:row_start] + row + s[row_end:]
patch.write_text(s)

print("UI V2 game artwork installed with automatic Free Fire / MAX mapping")
