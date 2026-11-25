#!/usr/bin/env python3
"""Install supplied VIPERX SHOP art in the app icon and license screen only."""
import json, pathlib, re, shutil, subprocess, sys
assert len(sys.argv) == 3, 'usage: apply_viperxshop_art.py <Xcode-project-parent> <art.jpg>'
root=pathlib.Path(sys.argv[1]).resolve()
art=pathlib.Path(sys.argv[2]).resolve()
assets=root/'ThreeOneOSFive'/'Assets.xcassets'
appfile=root/'ThreeOneOSFive'/'App.swift'
assert art.is_file() and art.stat().st_size > 100_000
assert assets.is_dir() and appfile.is_file(), (assets,appfile)

source=appfile.read_text(encoding='utf-8')
login_start=source.find('struct HTVLicenseGateView: View {')
assert login_start>=0, 'license view not located'
login_end=source.find('\nclass AppState:',login_start)
if login_end<0: login_end=min(len(source),login_start+24000)
login=source[login_start:login_end]
references=re.findall(r'Image\("([^"]+)"\)',login)
print('License-screen image references:',references)
choices=['VIPERXLicense','VIPERXMODS','HTVLogo','StarclinetWordmark','StarclinetLoginConcept']
selection=next((x for x in choices if x in references),None)
assert selection, 'No known existing license-screen artwork reference found'
# A brand-specific art asset prevents modifying a shared asset used elsewhere.
new_asset='VIPERXShopArtwork'
login_new=login.replace('Image("'+selection+'")','Image("'+new_asset+'")',1)
assert login_new!=login,selection
appfile.write_text(source[:login_start]+login_new+source[login_end:],encoding='utf-8')
folder=assets/(new_asset+'.imageset')
folder.mkdir(parents=True,exist_ok=True)
filename='VIPERX_SHOP.jpg'
shutil.copyfile(art,folder/filename)
(folder/'Contents.json').write_text(json.dumps({'images':[{'filename':filename,'idiom':'universal'}],'info':{'author':'xcode','version':1}},indent=2),encoding='utf-8')
print('Updated license screen',selection,'=>',new_asset)

# Keep existing AppIcon filenames, image dimensions, and asset-catalog mapping.
appicons=list(assets.glob('*.appiconset'))
assert appicons, 'AppIcon asset folder absent'
changed=0
for folder in appicons:
  contents=folder/'Contents.json'
  if not contents.is_file():continue
  manifest=json.loads(contents.read_text())
  sizes={}
  for item in manifest.get('images',[]):
    fn=item.get('filename')
    if not fn:continue
    nominal=item.get('size','')
    scale=item.get('scale','1x')
    m=re.fullmatch(r'(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)',nominal)
    if m:
      multiplier=float(scale[:-1]) if scale.endswith('x') else 1
      width=round(float(m.group(1))*multiplier)
      height=round(float(m.group(2))*multiplier)
    else:
      width=height=1024
    width=max(width,1); height=max(height,1)
    target=folder/fn
    target.parent.mkdir(parents=True,exist_ok=True)
    # Write the format corresponding to the existing asset filename.
    ext=target.suffix.lower()
    fmt='png' if ext=='.png' else 'jpeg'
    subprocess.run(['sips','-s','format',fmt,'-z',str(height),str(width),str(art),'--out',str(target)],stdout=subprocess.DEVNULL,check=True)
    assert target.stat().st_size>100
    changed+=1
assert changed>0,'No valid app icon outputs found'
# Strong QA checks: both key screen and home icon now use this artwork.
final=appfile.read_text()
assert 'Image("VIPERXShopArtwork")' in final
assert (assets/'VIPERXShopArtwork.imageset/VIPERX_SHOP.jpg').stat().st_size>100_000
print('PASS: replaced login artwork and',changed,'app icon files')
