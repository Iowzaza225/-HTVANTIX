#!/usr/bin/env python3
"""STARCLINET Build 29: install full-resolution imagery, preserve app logic.

The hero uses a separately cropped 2:1 photo without baked text: all copy and
server-status labels continue to be native SwiftUI, not embedded in a JPEG.
"""
from pathlib import Path
import json
import shutil
import sys

if len(sys.argv) != 3:
    raise SystemExit('usage: apply_starclinet_hires29.py <xcode-source-root> <artwork-folder>')
root = Path(sys.argv[1]).resolve()
art = Path(sys.argv[2]).resolve()
app_dir = root / 'ThreeOneOSFive'
assets = app_dir / 'Assets.xcassets'
source = app_dir / 'views/RepositoryHomeView.swift'
assert source.is_file() and assets.is_dir(), 'Missing STARCLINET project source'

mappings = [
    ('Star29Hero', 'Star29Hero.jpg', 480_000),
    ('Star29FreeFire', 'Star29FreeFire.jpg', 800_000),
    ('Star29FreeFireMax', 'Star29FreeFireMax.jpg', 750_000),
]
for name, filename, min_bytes in mappings:
    src = art / filename
    assert src.is_file() and src.stat().st_size >= min_bytes, f'High resolution source absent/degraded: {src}'
    dest = assets / (name + '.imageset')
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest / filename)
    manifest = {'images': [{'filename': filename, 'idiom': 'universal'}],
                'info': {'author': 'xcode', 'version': 1}}
    (dest / 'Contents.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    assert (dest / filename).stat().st_size == src.stat().st_size

swift = source.read_text(encoding='utf-8')
replacements = [
    ('Star28ResponsiveBanner(image: "Star28FreeFireBanner", height: 178)',
     'Star28ResponsiveBanner(image: "Star29Hero", height: 178)'),
    ('gameCard(title: "Free Fire", game: "ff", image: "Star28FreeFireBanner", count: freeFireCount)',
     'gameCard(title: "Free Fire", game: "ff", image: "Star29FreeFire", count: freeFireCount)'),
    ('gameCard(title: "Free Fire MAX", game: "ffmax", image: "Star28FreeFireMaxBanner", count: freeFireMaxCount)',
     'gameCard(title: "Free Fire MAX", game: "ffmax", image: "Star29FreeFireMax", count: freeFireMaxCount)'),
]
for old, new in replacements:
    count = swift.count(old)
    assert count == 1, f'Cannot unambiguously locate screen asset reference {old!r} (count={count})'
    swift = swift.replace(old, new, 1)

# Use high quality downsampling for Retina iPhones. Keep finite-width clipping
# implemented in Build 28 to prevent any horizontal expansion on narrow phones.
needle = '''            Image(image)
                .resizable()
                .scaledToFill()
                .frame(width: max(geometry.size.width, 1), height: height, alignment: .center)'''
needle_alt = needle.replace('geometry.', 'proxy.')
if needle in swift:
    swift = swift.replace(needle, needle.replace('                .scaledToFill()', '                .interpolation(.high)\n                .scaledToFill()'), 1)
elif needle_alt in swift:
    swift = swift.replace(needle_alt, needle_alt.replace('                .scaledToFill()', '                .interpolation(.high)\n                .scaledToFill()'), 1)
else:
    raise AssertionError('Cannot verify responsive finite-width banner helper')

assert swift.count('Star28ResponsiveBanner(image:') == 3
assert 'Star29Hero' in swift and 'Star29FreeFireMax' in swift
assert 'gameFilter: game' in swift
assert 'serverCatalog.errorMessage == nil' in swift, 'Real-time connection status missing'
assert 'Text("WELCOME TO")' in swift and 'Text("STARCLINET")' in swift, 'Expected native title labels missing'
assert 'case .versions: versionContent' in swift and 'case .security: securityContent' in swift
# No changes to license/authentication, network transport, or game filters.
source.write_text(swift, encoding='utf-8')
print('Build29 high-resolution UI applied: 2:1 hero and distinct FF / FF MAX assets')
for name, fn, _ in mappings:
    p = assets / (name + '.imageset') / fn
    print(name, p.stat().st_size, 'bytes')