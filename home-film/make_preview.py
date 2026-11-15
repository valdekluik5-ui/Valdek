"""
Home - turn a scene's rendered frames into an mp4 with the captions from film.TIMELINE (Cormorant Garamond italic,
soft fade in/out), and optionally join several scenes and lay the song under them.

  python make_preview.py scene 01 renders/scene01 out/scene01.mp4 [--step 2]
  python make_preview.py film out/home_film.mp4 renders/ [--song path/to/song.mp3] [--step 1]

Needs: Python 3 with Pillow, and ffmpeg on the PATH. The font is fonts/CormorantGaramond-Italic.ttf next to this file
(download it once from Google Fonts: Cormorant Garamond, Italic 500). Frames are expected as NNNN.png (the scene's own
frame numbers). With --step 2 every second frame was rendered; each is shown twice so the timing stays exact.
"""
import glob, os, re, subprocess, sys, tempfile, shutil
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FPS = 24


def timeline():
    """Read TIMELINE from film.py without importing Blender."""
    src = open(os.path.join(HERE, 'film.py'), encoding='utf-8').read()
    a = src.index('TIMELINE = {'); b = src.index('\n}\n', a) + 2
    ns = {}
    exec(src[a:b], ns)
    return ns['TIMELINE']


def font(size):
    for p in (os.path.join(HERE, 'fonts', 'CormorantGaramond-Italic.ttf'), os.path.join(os.path.dirname(HERE), 'fonts', 'CormorantGaramond-Italic.ttf')):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def wrap(draw, text, f, width):
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if draw.textlength(t, font=f) > width and cur:
            lines.append(cur); cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def caption_frames(sid, src, dst, step=1, size=(720, 1280)):
    """Writes sequential frames 00000.png... into dst with captions burned in. Returns the frame count."""
    T = timeline()[sid]
    t0 = T['t'][0]
    W, H = size
    f = font(int(W * .062))
    os.makedirs(dst, exist_ok=True)
    files = sorted(glob.glob(os.path.join(src, '*.png')), key=lambda p: int(re.findall(r'(\d+)\.png$', p)[0]))
    n = 0
    for p in files:
        fr = int(re.findall(r'(\d+)\.png$', p)[0])
        im = Image.open(p).convert('RGB').resize(size, Image.LANCZOS)
        for k in range(step):
            t = t0 + (fr - 1 + k) / FPS
            layer = Image.new('RGBA', size, (0, 0, 0, 0)); shadow = Image.new('RGBA', size, (0, 0, 0, 0))
            dl, ds = ImageDraw.Draw(layer), ImageDraw.Draw(shadow)
            active = [(c, a, b) for c, a, b in T['captions'] if a - .8 <= t <= b + .8]
            y = H * .76
            for text, a, b in active:
                alpha = min(1, max(0, (t - a) / .8 + 1) if t < a else 1) if t <= b else max(0, 1 - (t - b) / .8)
                alpha = max(0.0, min(1.0, alpha))
                for line in wrap(dl, text, f, W * .84):
                    tw = dl.textlength(line, font=f); x = (W - tw) / 2
                    dl.text((x, y), line, font=f, fill=(255, 246, 236, int(255 * alpha)))
                    ds.text((x, y + 3), line, font=f, fill=(30, 15, 8, int(210 * alpha)))
                    y += f.size * 1.2
                y += f.size * .35
            shadow = shadow.filter(ImageFilter.GaussianBlur(5))
            out = Image.alpha_composite(Image.alpha_composite(im.convert('RGBA'), shadow), layer).convert('RGB')
            out.save(os.path.join(dst, f'{n:05d}.png')); n += 1
    return n


def encode(frames_dir, out, song=None, start=0.0, fade_in=True, fade_out=True):
    n = len(glob.glob(os.path.join(frames_dir, '*.png'))); dur = n / FPS
    vf = []
    if fade_in:
        vf.append('fade=t=in:st=0:d=0.8')
    if fade_out and dur > 2:
        vf.append(f'fade=t=out:st={dur - 1.0:.2f}:d=1.0')
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(frames_dir, '%05d.png')]
    if song:
        cmd += ['-ss', f'{start:.3f}', '-t', f'{dur:.3f}', '-i', song]
    cmd += ['-vf', ','.join(vf) or 'null', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-movflags', '+faststart']
    if song:
        cmd += ['-c:a', 'aac', '-b:a', '192k', '-shortest']
    cmd.append(out)
    subprocess.run(cmd, check=True)
    return dur


def main():
    a = sys.argv[1:]
    opt = {}
    for k in ('--step', '--song', '--size'):
        if k in a:
            i = a.index(k); opt[k] = a[i + 1]; del a[i:i + 2]
    step = int(opt.get('--step', 1))
    size = tuple(int(v) for v in opt.get('--size', '720x1280').split('x'))
    if a[0] == 'scene':
        sid, src, out = a[1], a[2], a[3]
        tmp = tempfile.mkdtemp()
        n = caption_frames(sid, src, tmp, step, size)
        T = timeline()[sid]
        dur = encode(tmp, out, opt.get('--song'), T['t'][0])
        shutil.rmtree(tmp)
        print(f'wrote {out}: {n} frames, {dur:.1f} s')
    elif a[0] == 'film':
        out, root = a[1], a[2]
        tmp = tempfile.mkdtemp(); n = 0
        for sid in sorted(timeline()):
            src = os.path.join(root, 'scene' + sid)
            if not glob.glob(os.path.join(src, '*.png')):
                print('missing scene', sid, '- skipped'); continue
            sub = os.path.join(tmp, sid); k = caption_frames(sid, src, sub, step, size)
            for i in range(k):
                os.rename(os.path.join(sub, f'{i:05d}.png'), os.path.join(tmp, f'{n:05d}.png')); n += 1
        dur = encode(tmp, out, opt.get('--song'), 0.0)
        shutil.rmtree(tmp)
        print(f'wrote {out}: {n} frames, {dur:.1f} s')


if __name__ == '__main__':
    main()
