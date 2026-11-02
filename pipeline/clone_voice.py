"""유튜브 영상(또는 오디오 파일 주소)의 일부 구간으로 원장님 목소리를 타입캐스트에 복제.
녹음 파일은 깃허브에 저장되지 않고 실행이 끝나면 사라짐.

python pipeline/clone_voice.py --youtube URL --start 2:10 --end 3:05
python pipeline/clone_voice.py --audio-url https://.../sample.mp3
"""
import argparse, json, os, subprocess, sys, urllib.request, uuid

API = "https://api.typecast.ai"


def run(cmd):
    print("+", " ".join(cmd)); subprocess.run(cmd, check=True)


def multipart(path, fields, file_path):
    b = uuid.uuid4().hex
    body = b""
    for k, v in fields.items():
        body += f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    with open(file_path, "rb") as f:
        body += (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"sample.mp3\"\r\n"
                 f"Content-Type: audio/mpeg\r\n\r\n").encode() + f.read() + b"\r\n"
    body += f"--{b}--\r\n".encode()
    r = urllib.request.Request(API + path, data=body, method="POST", headers={
        "X-API-KEY": os.environ["TYPECAST_API_KEY"], "Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(r, timeout=180) as resp:
        return json.loads(resp.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--youtube"); ap.add_argument("--audio-url")
    ap.add_argument("--start", default="0:00"); ap.add_argument("--end", default="")
    ap.add_argument("--name", default="ashley-park")
    a = ap.parse_args()

    if a.youtube:
        run(["yt-dlp", "-f", "bestaudio", "-x", "--audio-format", "wav", "-o", "src.%(ext)s", a.youtube])
        src = "src.wav"
    elif a.audio_url:
        urllib.request.urlretrieve(a.audio_url, "src.bin"); src = "src.bin"
    else:
        sys.exit("--youtube 또는 --audio-url 이 필요합니다")

    cut = ["-ss", a.start] + (["-to", a.end] if a.end else [])
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, *cut, "-af",
         "highpass=f=80,lowpass=f=11000,afftdn=nf=-25,loudnorm=I=-18", "-ac", "1", "-ar", "44100",
         "-b:a", "192k", "sample.mp3"])

    res = None
    for path in ("/v1/custom-voices/instant-clone", "/v1/voices/clone"):
        try:
            res = multipart(path, {"name": a.name, "model": "ssfm-v30"}, "sample.mp3"); break
        except urllib.error.HTTPError as e:
            print(f"{path} → {e.code} {e.read()[:300]!r}")
    for f in ("src.wav", "src.bin", "sample.mp3"):
        if os.path.exists(f): os.remove(f)
    if not res:
        sys.exit("복제 실패")
    vid = res.get("voice_id") or res.get("id")
    msg = (f"## 원장님 목소리 복제 완료\n\n`{vid}`\n\n이 값을 저장소 Settings → Secrets and variables → Actions 에서 "
           f"`TYPECAST_ASHLEY_VOICE_ID` 라는 이름으로 저장하세요.\n")
    print(msg)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f: f.write(msg)


if __name__ == "__main__":
    main()
