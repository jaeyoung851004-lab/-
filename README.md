# ESG 마와리 MVP (Python)

초보자도 VS Code에서 실행할 수 있는 **최소 기능 버전**입니다.

## 기능
- 3개 외신 사이트에서 최신 기사 **제목 + 링크** 수집
  - ESG Today: https://www.esgtoday.com/
  - Carbon Herald: https://carbonherald.com/
  - The EV Report: https://theevreport.com/
- RSS 우선 수집
- RSS 실패 시 HTML 목록에서 수집
- 본문 수집 없음
- URL 중복 제거
- 제목 키워드 기반 `산업태그`, `이슈태그` 자동 분류
- 결과를 `mawari_YYYYMMDD.xlsx`로 저장

## 파일 구조
```bash
.
├─ scraper.py
├─ requirements.txt
└─ README.md
```

## 1) 가상환경 먼저 만들기 (권장)

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> VS Code에서 터미널은 `Terminal > New Terminal` 메뉴로 열 수 있습니다.

## 2) 패키지 설치
가상환경이 활성화된 상태에서 아래 명령을 실행하세요.

```bash
pip install -r requirements.txt
```

## 3) 왜 이 패키지들이 필요한가요?
- `feedparser`: RSS/Atom 피드를 읽어서 기사 제목/링크를 가져옵니다.
- `requests`: 웹 페이지와 RSS 주소에 HTTP 요청을 보냅니다.
- `beautifulsoup4`: RSS가 없을 때 HTML에서 기사 목록 링크/제목을 추출합니다.
- `pandas`: 수집 결과를 표(데이터프레임)로 정리합니다.
- `openpyxl`: `pandas`가 `.xlsx` 엑셀 파일을 저장할 때 사용합니다.

## 4) Codex 환경 설치 실패 안내
이 저장소의 Codex 실행 환경에서는 프록시 제한(403) 때문에 `pip install` 테스트가 실패했습니다.
하지만 **로컬 PC에서 인터넷이 연결된 상태**라면 위 명령으로 정상 설치할 수 있습니다.

## 5) 실행 방법
```bash
python scraper.py
```

실행이 끝나면 현재 폴더에 아래 형식 파일이 생성됩니다.
- `mawari_YYYYMMDD.xlsx` (예: `mawari_20260506.xlsx`)

## 출력 컬럼
- 날짜
- 매체명
- 기사명
- 링크
- 산업태그
- 이슈태그
- 담당자 (빈칸)
- 비고 (빈칸)

## 태그 분류 기준
- `scraper.py` 안의 아래 딕셔너리에서 키워드로 분류
  - `INDUSTRY_RULES`
  - `ISSUE_RULES`
- 어떤 키워드에도 해당하지 않으면 `기타`

## 참고
- 사이트 구조가 바뀌면 HTML 수집이 일부 실패할 수 있습니다.
- 이 경우 `collect_from_html()`의 CSS 선택자를 수정하면 됩니다.
