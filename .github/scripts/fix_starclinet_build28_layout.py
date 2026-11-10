#!/usr/bin/env python3
"""Presentation-only iPhone layout fix for STARCLINET Build 28."""
from pathlib import Path
import json, shutil, sys

root=Path(sys.argv[1]).resolve()
art=Path(sys.argv[2]).resolve()
catalog=root/"ThreeOneOSFive/Assets.xcassets"
p=root/"ThreeOneOSFive/views/RepositoryHomeView.swift"
assert p.is_file() and catalog.is_dir()

for name,src in [
    ("Star28FreeFireBanner",art/"FreeFireBanner.png"),
    ("Star28FreeFireMaxBanner",art/"FreeFireMaxBanner.png"),
]:
    assert src.stat().st_size>100000,src
    dest=catalog/(name+".imageset")
    dest.mkdir(parents=True,exist_ok=True)
    fn=name+".png"
    shutil.copy2(src,dest/fn)
    (dest/"Contents.json").write_text(json.dumps({
        "images":[{"filename":fn,"idiom":"universal"}],
        "info":{"author":"xcode","version":1}
    }),encoding="utf-8")

s=p.read_text(encoding="utf-8")
changes=[
('''                    .frame(maxWidth: 650)
                    .frame(maxWidth: .infinity)
                    .padding(.horizontal, 18)''',
 '''                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 18)'''),
('''            Image("StarclinetWordmark")
                .resizable()
                .scaledToFit()
                .frame(width: 205, height: 54)''',
 '''            Image("StarclinetWordmark")
                .resizable()
                .scaledToFit()
                .frame(maxWidth: 174, maxHeight: 48)'''),
('''gameCard(title: "Free Fire", game: "ff", image: "FreeFireArtwork", count: freeFireCount)''',
 '''gameCard(title: "Free Fire", game: "ff", image: "Star28FreeFireBanner", count: freeFireCount)'''),
('''gameCard(title: "Free Fire MAX", game: "ffmax", image: "StarclinetFFMaxBanner", count: freeFireMaxCount)''',
 '''gameCard(title: "Free Fire MAX", game: "ffmax", image: "Star28FreeFireMaxBanner", count: freeFireMaxCount)'''),
('''            Image("FreeFireArtwork")
                .resizable()
                .scaledToFill()
                .frame(height: 178)
                .frame(maxWidth: .infinity)
                .clipped()''',
 '''            Star28ResponsiveBanner(image: "Star28FreeFireBanner", height: 178)'''),
('''                    Image(image)
                        .resizable()
                        .scaledToFill()
                        .frame(height: 126)
                        .frame(maxWidth: .infinity)
                        .clipped()''',
 '''                    Star28ResponsiveBanner(image: image, height: 126)'''),
('''                        Image(image)
                            .resizable()
                            .scaledToFill()
                            .frame(height: 190)
                            .frame(maxWidth: .infinity)
                            .clipped()''',
 '''                        Star28ResponsiveBanner(image: image, height: 190)'''),
('''                            .italic()
                            .shadow(color: .black, radius: 5)''',
 '''                            .italic()
                            .lineLimit(1)
                            .minimumScaleFactor(0.7)
                            .shadow(color: .black, radius: 5)'''),
('''            Text(detail).font(.caption2).foregroundStyle(.secondary)''',
 '''            Text(detail).font(.caption2).foregroundStyle(.secondary)
                .lineLimit(1).minimumScaleFactor(0.7)''')
]
for old,new in changes:
    n=s.count(old)
    assert n==1,(old[:50],n)
    s=s.replace(old,new,1)

helper='''
// Width-safe 3:1 image rendering: fixes unwanted horizontal expansion.
private struct Star28ResponsiveBanner: View {
    let image: String
    let height: CGFloat

    var body: some View {
        GeometryReader { geometry in
            Image(image)
                .resizable()
                .scaledToFill()
                .frame(width: max(geometry.size.width, 1), height: height, alignment: .center)
                .clipped()
        }
        .frame(height: height)
        .clipped()
        .accessibilityHidden(true)
    }
}
'''
marker='private enum StarStyle {'
assert s.count(marker)==1
s=s.replace(marker,helper+'\n'+marker,1)
assert s.count('Star28ResponsiveBanner(image:')==3
assert s.count('image: "Star28FreeFireBanner"')==2
assert s.count('image: "Star28FreeFireMaxBanner"')==1
assert 'gameFilter: game' in s
assert 'Star28ResponsiveBanner(image: image, height: 190)' in s
p.write_text(s,encoding="utf-8")
print("STARCLINET Build28: responsive image widths; FF/FF MAX artwork correctly assigned")
