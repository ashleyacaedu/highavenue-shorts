"""타입캐스트 TTS 호출.

환경변수
  TYPECAST_API_KEY            타입캐스트 API 키 (없으면 목소리 없이 자막만)
  TYPECAST_ASHLEY_VOICE_ID    원장님 복제 목소리 id (uc_...)
  TYPECAST_NARRATOR_VOICE_ID  기본 AI 성우 id (tc_...). 비워두면 한국어 여성 보이스 자동 선택
  MOCK_TTS=1                  테스트용: 실제 호출 대신 무음 음성 생성
"""
import json, os, subprocess, urllib.request, urllib.error

API = "https://api.typecast.ai"
_auto_narrator = None


def _req(method, path, body=None, timeout=120):
    key = os.environ["TYPECAST_API_KEY"]
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(API + path, data=data, method=method,
                               headers={"X-API-KEY": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return resp.read(), resp.headers.get("Content-Type", "")


def list_voices():
    raw, _ = _req("GET", "/v1/voices?model=ssfm-v30")
    data = json.loads(raw)
    return data if isinstance(data, list) else data.get("voices", data.get("result", []))


def _pick_narrator():
    global _auto_narrator
    if _auto_narrator:
        return _auto_narrator
    voices = list_voices()
    def score(v):
        txt = json.dumps(v, ensure_ascii=False).lower()
        s = 0
        if "female" in txt: s += 2
        if "narrat" in txt or "conversational" in txt: s += 1
        if "kor" in txt or "ko" in txt: s += 1
        return s
    voices.sort(key=score, reverse=True)
    _auto_narrator = voices[0]["voice_id"]
    print(f"[tts] 기본 성우 자동 선택: {_auto_narrator}")
    return _auto_narrator


def voice_id_for(voice):
    if voice == "ashley":
        vid = os.environ.get("TYPECAST_ASHLEY_VOICE_ID", "").strip()
        if vid:
            return vid
        print("[tts] 원장님 목소리 id가 아직 없어서 기본 성우로 대신 읽습니다")
    vid = os.environ.get("TYPECAST_NARRATOR_VOICE_ID", "").strip()
    return vid or _pick_narrator()


def enabled():
    return bool(os.environ.get("TYPECAST_API_KEY")) or os.environ.get("MOCK_TTS") == "1"


def synth(text, voice, out_path, tempo=1.08):
    """text를 out_path(wav)로. 길이(초) 반환."""
    if os.environ.get("MOCK_TTS") == "1":
        dur = max(1.6, len(text) * 0.13)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                        "-i", f"sine=frequency=220:duration={dur}", "-af", "volume=0.15",
                        "-ar", "44100", "-ac", "2", out_path], check=True)
        return duration(out_path)

    body = {"voice_id": voice_id_for(voice), "text": text, "model": "ssfm-v30",
            "language": "kor", "output": {"audio_format": "wav", "audio_tempo": tempo}}
    try:
        audio, ctype = _req("POST", "/v1/text-to-speech", body)
    except urllib.error.HTTPError as e:
        if e.code in (400, 422):  # 옵션 형식이 바뀐 경우 최소 요청으로 재시도
            body.pop("output", None)
            audio, ctype = _req("POST", "/v1/text-to-speech", body)
        else:
            raise RuntimeError(f"타입캐스트 오류 {e.code}: {e.read()[:300]!r}")
    if "json" in ctype:  # 일부 응답은 base64 json
        import base64
        audio = base64.b64decode(json.loads(audio)["audio"])
    raw = out_path + ".raw"
    with open(raw, "wb") as f:
        f.write(audio)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-ar", "44100", "-ac", "2", out_path], check=True)
    os.remove(raw)
    return duration(out_path)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())
