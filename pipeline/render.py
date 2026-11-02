"""대본(yaml) → 세로 쇼츠 mp4.

사용법
  python pipeline/render.py --count 5 --consume   # 대기열 앞에서 5개 만들고 done/으로 옮김
  python pipeline/render.py content/queue/001.yaml  # 특정 대본만
"""
import argparse, glob, json, os, shutil, subprocess, sys
import yaml
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import tts, music

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1080, 1920
FPS = 30

FONT_DIRS = ["/usr/share/fonts/opentype/noto/", "/usr/share/fonts/truetype/noto/", "/usr/share/fonts/noto-cjk/"]


def font(weight, size):
    for d in FONT_DIRS:
        p = os.path.join(d, f"NotoSansCJK-{weight}.ttc")
        if os.path.exists(p):
            return ImageFont.truetype(p, size, index=1)  # index 1 = KR
    raise FileNotFoundError("Noto Sans CJK 폰트가 없습니다 (fonts-noto-cjk 설치 필요)")


BG = (14, 16, 32)
WHITE = (245, 245, 250)
GRAY = (150, 155, 180)
ACC = (255, 214, 64)
PUR = (150, 110, 255)


def center(d, y, text, f, fill):
    w = d.textlength(text, font=f)
    d.text(((W - w) / 2, y), text, font=f, fill=fill)


def base(progress):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 14], fill=PUR)
    center(d, 150, "HIGH AVENUE", font("Bold", 34), GRAY)
    center(d, H - 260, "하이애비뉴 애슐리박 원장T", font("Bold", 44), WHITE)
    center(d, H - 195, "특목고 면접 · 자소서", font("Medium", 32), GRAY)
    if progress is not None:
        d.rectangle([80, H - 110, 80 + (W - 160) * progress, H - 100], fill=ACC)
    return im, d


def parse_line(s):
    s = str(s)
    if s.startswith("*") and s.endswith("*") and len(s) > 2:
        return s[1:-1], True
    return s, False


def draw_card(card, progress, path):
    im, d = base(progress)
    lines = [parse_line(x) for x in card["lines"]]
    size = 112
    while size > 60 and max(d.textlength(t, font=font("Black", size)) for t, _ in lines) > W - 120:
        size -= 6
    big = font("Black", size)
    lh = int(size * 1.34)
    head = card.get("head")
    block = len(lines) * lh + (90 if head else 0)
    y = (H - block) / 2 - 40
    if head:
        center(d, y, head, font("Medium", 42), PUR); y += 90
    for t, hl in lines:
        if hl:
            tw = d.textlength(t, font=big); x0 = (W - tw) / 2
            d.rectangle([x0 - 10, y + size * 0.62, x0 + tw + 10, y + size * 1.14], fill=(90, 70, 20))
            center(d, y, t, big, ACC)
        else:
            center(d, y, t, big, WHITE)
        y += lh
    im.save(path)


def draw_outro(path):
    im, d = base(None)
    center(d, 640, "9년 특목입시 현장", font("Medium", 54), GRAY)
    center(d, 740, "명덕외고", font("Black", 130), WHITE)
    center(d, 900, "5년 연속 수석", font("Black", 130), ACC)
    center(d, 1100, "2026학년도 85명 중 72명 합격", font("Bold", 52), WHITE)
    d.rounded_rectangle([290, 1260, 790, 1370], radius=55, fill=PUR)
    center(d, 1278, "구독하고 면접 준비", font("Bold", 50), WHITE)
    im.save(path)


def run(cmd):
    subprocess.run(cmd, check=True)


def clip(img, dur, out):
    fr = int(dur * FPS)
    vf = (f"scale=1188:2112,zoompan=z='1+0.0006*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d={fr}:s={W}x{H}:fps={FPS},fade=t=in:st=0:d=0.2,fade=t=out:st={dur-0.2:.2f}:d=0.2,format=yuv420p")
    run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", img, "-t", f"{dur:.3f}",
         "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", out])


def silence(dur, out):
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-t", f"{dur:.3f}", out])


def render(script_path, out_dir, seed=0):
    with open(script_path, encoding="utf-8") as f:
        s = yaml.safe_load(f)
    sid = str(s["id"])
    work = os.path.join(out_dir, f"_work_{sid}")
    os.makedirs(work, exist_ok=True)
    cards = s["cards"]
    voice = s.get("voice", "none")
    use_voice = voice != "none" and tts.enabled()

    seg_v, seg_a = [], []
    total = len(cards) + 1
    for i, c in enumerate(cards):
        img = os.path.join(work, f"c{i:02d}.png")
        draw_card(c, (i + 1) / total, img)
        say = c.get("say")
        if use_voice and say:
            wav = os.path.join(work, f"v{i:02d}.wav")
            d = tts.synth(say, voice, wav) + 0.35
            padded = os.path.join(work, f"a{i:02d}.wav")
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-af", f"apad=whole_dur={d:.3f}", padded])
        else:
            txt = "".join(parse_line(x)[0] for x in c["lines"])
            d = float(c.get("sec", max(2.6, 1.2 + len(txt) * 0.11)))
            padded = os.path.join(work, f"a{i:02d}.wav"); silence(d, padded)
        mp4 = os.path.join(work, f"p{i:02d}.mp4"); clip(img, d, mp4)
        seg_v.append(mp4); seg_a.append(padded)

    outro_img = os.path.join(work, "outro.png"); draw_outro(outro_img)
    od = 3.6
    if use_voice and s.get("outro_say"):
        wav = os.path.join(work, "vout.wav")
        od = max(od, tts.synth(s["outro_say"], voice, wav) + 0.6)
        padded = os.path.join(work, "aout.wav")
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-af", f"apad=whole_dur={od:.3f}", padded])
    else:
        padded = os.path.join(work, "aout.wav"); silence(od, padded)
    mp4 = os.path.join(work, "pout.mp4"); clip(outro_img, od, mp4)
    seg_v.append(mp4); seg_a.append(padded)

    def concat(files, out, extra=()):
        lst = out + ".txt"
        with open(lst, "w") as f:
            for x in files: f.write(f"file '{os.path.abspath(x)}'\n")
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, *extra, out])

    video = os.path.join(work, "video.mp4"); concat(seg_v, video, ["-c", "copy"])
    voice_wav = os.path.join(work, "voice.wav"); concat(seg_a, voice_wav)
    dur = tts.duration(video)
    bgm = os.path.join(work, "bgm.wav"); music.make(bgm, dur, seed=seed)
    bgm_vol = 0.13 if use_voice else 0.9
    final = os.path.join(out_dir, f"{sid}.mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", voice_wav, "-i", bgm,
         "-filter_complex", f"[2:a]volume={bgm_vol}[m];[1:a][m]amix=inputs=2:duration=first:normalize=0,"
                            f"loudnorm=I=-15:TP=-1.5:LRA=11[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", final])
    shutil.rmtree(work)
    return {
        "id": sid, "file": f"{sid}.mp4", "voice": voice if use_voice else "none",
        "title": s["title"], "description": s["description"], "tags": s.get("tags", []),
        "clip_description": s.get("clip_description", s["description"]),
        "clip_tags": s.get("clip_tags", [])[:5], "duration": round(dur, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scripts", nargs="*")
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--consume", action="store_true", help="만든 대본을 content/done/으로 옮김")
    ap.add_argument("--out", default=os.path.join(ROOT, "out"))
    a = ap.parse_args()
    files = a.scripts or sorted(glob.glob(os.path.join(ROOT, "content/queue/*.yaml")))[: a.count]
    if not files:
        print("대기열에 대본이 없습니다."); sys.exit(0)
    os.makedirs(a.out, exist_ok=True)
    manifest = []
    for k, p in enumerate(files):
        print(f"[render] {os.path.basename(p)}")
        manifest.append(render(p, a.out, seed=k))
        if a.consume:
            os.makedirs(os.path.join(ROOT, "content/done"), exist_ok=True)
            shutil.move(p, os.path.join(ROOT, "content/done", os.path.basename(p)))
    with open(os.path.join(a.out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
