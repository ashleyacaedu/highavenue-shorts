# 하이애비뉴 쇼츠 자동 제작

매주 일요일 밤 9시(한국시간)에 `content/queue/`의 대본 5개로 쇼츠를 만들어
이번 주 묶음(Releases)으로 올립니다. 업로드 예약은 Claude가 업리카로 걸어둡니다.

## 구조
- `content/queue/` 올라갈 대본 (파일 이름 순서대로 사용)
- `content/done/` 이미 만든 대본
- `pipeline/render.py` 대본 → 영상 (화면·목소리·배경음악)
- `pipeline/tts.py` 타입캐스트 목소리
- `pipeline/music.py` 저작권 없는 배경음악 직접 작곡
- `pipeline/clone_voice.py` 원장님 목소리 복제

## 대본 형식
```yaml
id: "011-example"
voice: ashley        # ashley(원장님 목소리) / narrator(AI 성우) / none(목소리 없음)
title: "유튜브 제목 (100자 이내)"
description: "쇼츠 설명 (100자 이내, 해시태그 포함)"
tags: [유튜브 태그들]
clip_description: "네이버 클립 설명"
clip_tags: [최대 5개]
outro_say: "하이애비뉴 애슐리박이었습니다."   # ashley일 때만
cards:
  - head: "작은 머리말 (선택)"
    lines: ["보통 줄", "*노란 강조 줄*"]
    say: "이 화면에서 읽을 문장"
```

## 비밀값 (Settings → Secrets and variables → Actions)
- `TYPECAST_API_KEY` 타입캐스트 API 키
- `TYPECAST_ASHLEY_VOICE_ID` 원장님 복제 목소리 id (목소리 복제 실행 후)
- `TYPECAST_NARRATOR_VOICE_ID` (선택) AI 성우 id. 비우면 자동 선택

## 수동 실행
Actions 탭 → "주간 쇼츠 제작" → Run workflow → preview 체크하면 대본을 쓰지 않고 결과만 받아볼 수 있습니다.
