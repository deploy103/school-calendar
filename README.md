# School Calendar

학급 일정, 수행평가, 특수수업, 행사를 등록하고 수정/삭제할 수 있는 다크모드 캘린더입니다. Python 백엔드가 정적 페이지와 JSON API를 함께 제공합니다.

## 기능

- 월별 캘린더 보기
- 일정 추가, 수정, 삭제
- 교시 선택: 조회, 1교시부터 7교시, 방과후, 종례
- 일정 종류 선택: 수행평가, 특수수업, 학급행사, 기타
- JSON 파일 기반 데이터 저장
- `today-rice` 서비스로 이동하는 링크 지원

## 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn school_cal.main:app --reload --host 0.0.0.0 --port 8000
```

브라우저에서 `http://localhost:8000`으로 접속합니다.

## 환경 변수

| 이름 | 기본값 | 설명 |
| --- | --- | --- |
| `SCHOOL_CAL_DATA_FILE` | `data/events.json` | 일정 데이터 JSON 파일 경로 |
| `SCHOOL_CAL_TODAY_RICE_URL` | `/today-rice` | 오늘 급식 서비스 링크 |

## 테스트

```bash
pytest
```
