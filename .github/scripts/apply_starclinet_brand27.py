#!/usr/bin/env python3
import json, pathlib, shutil, sys
root=pathlib.Path(sys.argv[1]).resolve()
art=pathlib.Path(sys.argv[2]).resolve()
assets=root/'ThreeOneOSFive/Assets.xcassets'
app=root/'ThreeOneOSFive/App.swift'
home=root/'ThreeOneOSFive/views/RepositoryHomeView.swift'
assert assets.is_dir() and app.is_file() and home.is_file()
def img(name,filename):
    p=assets/(name+'.imageset')
    p.mkdir(parents=True,exist_ok=True)
    shutil.copy2(art/filename,p/filename)
    (p/'Contents.json').write_text(json.dumps({'images':[{'filename':filename,'idiom':'universal'}],'info':{'author':'xcode','version':1}}),encoding='utf-8')
img('HTVLogo','StarclinetAppIcon.png')
img('StarclinetWordmark','StarclinetWordmark.png')
img('StarclinetLoginConcept','StarclinetLoginConcept.png')
img('FreeFireArtwork','FreeFireBanner.png')
img('StarclinetFFMaxBanner','FreeFireMaxBanner.png')
d=assets/'AppIcon.appiconset'
assert d.is_dir()
icons=list(d.glob('AppIcon*.png'))
assert icons
for f in icons: shutil.copyfile(art/'StarclinetAppIcon.png',f)
login=app.read_text()
assert '"appId": "starclinet"' in login
st=login.find('struct HTVLicenseGateView: View {')
ed=login.find('\nclass AppState:',st)
assert st>=0 and ed>st
piece=login[st:ed]
assert 'Image("FreeFireArtwork")' in piece
piece=piece.replace('Image("FreeFireArtwork")','Image("StarclinetLoginConcept")',1)
piece=piece.replace('.blur(radius: 36)','.blur(radius: 45)',1)
piece=piece.replace('.opacity(0.11)','.opacity(0.16)',1)
if 'RuizenBrandTitle(size: 35)' in piece:
    piece=piece.replace('RuizenBrandTitle(size: 35)','Image("StarclinetWordmark")\n                        .resizable()\n                        .scaledToFit()\n                        .frame(width: 285, height: 95)\n                        .accessibilityLabel("STARCLINET")',1)
app.write_text(login[:st]+piece+login[ed:])
screen=home.read_text()
assert 'FreeFireArtwork' in screen and 'FreeFireMaxIcon' in screen
screen=screen.replace('game: "ffmax", image: "FreeFireMaxIcon"','game: "ffmax", image: "StarclinetFFMaxBanner"',1)
original='''            AppLogo(size: 42)
            VStack(alignment: .leading, spacing: 2) {
                Text("STARCLINET")
                    .font(.system(size: 21, weight: .black, design: .rounded))
                    .italic()
                    .foregroundStyle(.white)
                Text("GAME PANEL")
                    .font(.system(size: 9, weight: .black, design: .monospaced))
                    .tracking(3)
                    .foregroundStyle(StarStyle.orange)
            }'''
new='''            Image("StarclinetWordmark")
                .resizable()
                .scaledToFit()
                .frame(width: 205, height: 54)
                .accessibilityLabel("STARCLINET Game Panel")'''
if original in screen: screen=screen.replace(original,new,1)
assert 'StarclinetFFMaxBanner' in screen
home.write_text(screen)
print('Brand27 assets applied. License appId occurrences:',login.count('"appId": "starclinet"'))
