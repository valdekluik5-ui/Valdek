"""Adds classes.dex and lib/<abi>/*.so to the linked APK; resources.arsc stays uncompressed and every stored entry is 4-byte aligned.
Usage: package.py <linked.apk> <classes.dex> <out.apk> [libs dir with <abi>/lib*.so]"""
import os, sys, zipfile
src, dex, out = sys.argv[1:4]
libs = sys.argv[4] if len(sys.argv) > 4 else None
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out, 'w') as zout:
    entries = [(i.filename, zin.read(i.filename)) for i in zin.infolist()] + [('classes.dex', open(dex, 'rb').read())]
    if libs:
        for abi in sorted(os.listdir(libs)):
            for so in sorted(os.listdir(os.path.join(libs, abi))):
                entries.append((f'lib/{abi}/{so}', open(os.path.join(libs, abi, so), 'rb').read()))
    for name, data in entries:
        stored = name == 'resources.arsc' or name.endswith('.png')
        zi = zipfile.ZipInfo(name, date_time=(2008, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
        if stored:  # pad the local header's extra field so the data starts on a 4-byte boundary
            offset = zout.fp.tell() + 30 + len(zi.filename.encode())
            zi.extra = b'\0' * ((4 - offset % 4) % 4)
        zout.writestr(zi, data, compresslevel=9) if not stored else zout.writestr(zi, data)
