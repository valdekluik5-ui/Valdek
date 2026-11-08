"""Adds classes.dex to the linked APK; resources.arsc stays uncompressed and every stored entry is 4-byte aligned."""
import sys, zipfile
src, dex, out = sys.argv[1:4]
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out, 'w') as zout:
    entries = [(i, zin.read(i.filename)) for i in zin.infolist()] + [(zipfile.ZipInfo('classes.dex'), open(dex, 'rb').read())]
    for info, data in entries:
        stored = info.filename == 'resources.arsc' or info.filename.endswith('.png')
        zi = zipfile.ZipInfo(info.filename, date_time=(2008, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
        if stored:  # pad the local header's extra field so the data starts on a 4-byte boundary
            offset = zout.fp.tell() + 30 + len(zi.filename.encode())
            zi.extra = b'\0' * ((4 - offset % 4) % 4)
        zout.writestr(zi, data)
