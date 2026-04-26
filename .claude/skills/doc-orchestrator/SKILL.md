---
name: doc-orchestrator
description: 회의록 기반으로 Confluence 문서를 자동 업데이트하는 AI 오케스트레이터
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
argument-hint: [회의 오디오/텍스트 파일 경로]
---

# Document Orchestrator

회의록을 입력받아, 업데이트가 필요한 Confluence 문서를 분석하고, 사용자 승인 후 자동으로 변경사항을 적용하는 에이전트.

## 언어 정책

- **사용자와의 모든 대화는 한국어로 진행한다.** AskUserQuestion, 확인 메시지, 보고서, Confluence 코멘트 등 사용자에게 보이는 모든 텍스트는 한국어로 작성한다.
- **기술 용어는 영어를 그대로 사용한다.** AI/SW 분야 용어(AQ, GQ, NPIR, SNR, Xnnpack, ExecuTorch 등)는 번역하지 않고 영어 원문 그대로 쓴다.
- **내부 데이터 구조(JSON 키, YAML 키)는 영어를 유지한다.** 코드 호환성을 위해 `decisions`, `action_items`, `keywords` 같은 키 이름은 영어로 둔다.
- **값(value)은 한국어로 작성한다.** `decisions: ["GQ calibration 로직을 observer 기반으로 변경"]` 처럼 기술 용어는 영어, 설명은 한국어로 섞어 쓴다.

## Execution Flow

### Step 0: 환경 설정

시작 전 아래 설정을 실행한다:
```
set -a && source .env && set +a && pip install -q openai
```
프로젝트의 `.env` 파일에서 환경 변수를 로드하고 의존성을 설치한다.
`.env`가 없으면 사용자에게 생성하라고 안내한다 (README.md 템플릿 참고).

**Required environment variables in `.env`:**
```
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_EMAIL=your-email@example.com
CONFLUENCE_TOKEN=your-api-token
OPENAI_API_KEY=your-openai-key
```

### Step 1: 사전 컨텍스트 수집 (선택)

회의록 처리 전, 사용자에게 관련 문서를 이미 알고 있는지 확인한다.

AskUserQuestion:
- "이 회의와 관련된 Confluence 페이지가 있으신가요?"
  - 네, 페이지 URL을 알려드릴게요 → 사용자로부터 Confluence 페이지 URL을 수집
  - 아니요, 자동으로 찾아주세요 → 회의록 입력 후 Step 2로 이동

사용자가 URL을 제공하면 page ID로 변환한다:

**처리해야 할 URL 형식:**
- 전체 URL: `https://nota-dev.atlassian.net/wiki/spaces/SPACE/pages/123456789/Page+Title` → page ID `123456789` 추출
- 단축 URL: `https://nota-dev.atlassian.net/wiki/x/GYHUdw` → confluence_search 또는 confluence_get_page로 해석

**단축 URL (`/wiki/x/...`) 처리:**
단축 URL은 base64 인코딩된 page ID를 포함한다. 해석 방법:
1. confluence_search에 단축 URL이나 페이지 제목으로 검색 시도
2. 또는 `Bash`로 디코딩: `/x/` 뒤의 경로가 base64url 인코딩된 32-bit big-endian page ID
   ```
   echo "GYHUdw" | base64 -d | od -An -tu4 | tr -d ' '
   ```
3. 디코딩된 page ID로 confluence_get_page 호출

URL을 page ID로 변환한 후:
- confluence_get_page로 각 페이지를 가져온다
- 이들을 **고정 문서(pinned documents)** 로 저장 — 검색 결과와 관계없이 항상 분석에 포함

### Step 2: 회의록 입력

AskUserQuestion:
- "회의록을 어떻게 제공하시겠어요?"
  - 오디오 파일 경로 → OpenAI GPT-4o audio API로 전사 후 분석 (아래 오디오 전사 섹션 참고)
  - 텍스트/트랜스크립트 파일 경로 → 파일 읽기
  - 텍스트 직접 붙여넣기

회의록을 읽은 후, 다음 단계의 분류를 위해 원본 트랜스크립트 텍스트를 저장한다.

### Step 2.5: 회의 분류

두 개의 경량 classifier를 사용해 회의 트랜스크립트를 분류한다. 순수 프롬프트 기반으로 페이지 조회 없음.

1. `domains/classifiers/topic.md` 읽기 (이 SKILL.md 파일 기준 상대 경로)
2. 원본 트랜스크립트에 topic classifier 적용 → `topics: [...]` 출력 (해당하는 모든 topic 선택, Weekly Progress / Sprint Planning / Scenario & Product / Technical Design / Experiment & Validation 중)
3. `domains/classifiers/part.md` 읽기
4. 원본 트랜스크립트에 part classifier 적용 → `parts: [...]` 출력 (해당하는 모든 part 선택, Q / GO / MR / ME / SWE 중)

분류 결과를 다음 단계를 위해 저장한다.

### Step 2.6: 도메인 인식 분석

분류된 각 part에 대해 전문 agent를 로드하고 트랜스크립트를 분석한다.

1. `domains/cross-cut/scenarios.md` 읽기 — 공유 S0-S3 컨텍스트, 항상 로드
2. 분류 결과의 각 part에 대해:
   a. 해당 agent 파일 읽기: `domains/agents/{part_code}.md` (part_code: q, go, mr, me, swe 중 하나, 소문자)
   b. 해당 part 관점에서 트랜스크립트 분석:
      - Agent의 **내장 도메인 용어집**으로 용어를 정확히 해석
      - 분류된 topic과 매칭되는 **topic별 분석 포커스** 지시 적용
      - scenarios.md의 **S0-S3 cross-cut 컨텍스트** 활용
   c. 분류된 topic 기반으로 agent의 reference 테이블에서 조회할 **reference page** 식별
   d. `confluence_get_page`로 관련 reference page 조회 (agent 파일에 page ID 명시)
   e. Reference page 내용을 분석에 활용 (문서 현재 상태 확인, 의사결정과 비교)
   f. Part별 출력 생성: 의사결정, 액션 아이템, 키워드, reference page, cross-cut 영향

### Step 2.7: 통합 및 Cross-Cut 확인

활성화된 모든 part agent의 출력을 통합 분석으로 병합한다.

1. **의사결정 병합**: 모든 part별 의사결정을 합치고, 어느 part가 식별했는지 표기
2. **액션 아이템 병합**: 합치고 중복 제거 (같은 액션이 여러 part에서 감지될 수 있음)
3. **키워드 병합**: 모든 part의 도메인별 검색 키워드 결합
4. **Reference page 병합**: 조회되었거나 추천된 모든 reference page ID 수집
5. **Cross-cut 확인**: 모든 part agent의 `cross_cut_impacts` 검토:
   - S0-S3 시나리오 정의에 영향을 주는 의사결정이 있으면 → 시나리오 문서 업데이트 플래그
   - 공유 pipeline 흐름에 영향을 주는 의사결정이 있으면 → pipeline 문서 업데이트 플래그
   - 여러 part에 영향을 주는 의사결정이 있으면 → cross-part 조율 플래그
6. 통합 출력 생성:
   - 통합 의사결정 목록
   - 통합 액션 아이템 목록
   - 통합 검색 키워드 (도메인 인식, 범용 키워드 아님)
   - 통합 reference page ID (이미 조회 완료)
   - Cross-cut 영향 요약

### Step 3: 관련 Confluence 문서 검색

도메인 인식 분석에서 결합된 키워드로 Confluence 문서를 검색한다. 모든 검색은 **NPP02** (NetsPresso Platform Team) space로 범위를 한정한다.

1. `space=NPP02`로 범위를 지정하여 confluence_search로 키워드 기반 검색:
   - Step 2.7의 도메인별 키워드 사용 (범용 회의 키워드가 아님)
   - 의사결정 주제별로 여러 쿼리 실행
   - Part agent의 reference page ID를 이미 관련된 페이지로 포함
2. 검색 결과 병합:
   - Step 1의 고정 문서 (있는 경우)
   - Step 2.6에서 이미 조회한 reference page
   - Page ID 기준 중복 제거
3. 결합된 결과에서 가장 관련성 높은 문서 선별 (최대 10개)
4. 확인 링크와 함께 문서 목록을 사용자에게 제시

각 문서는 다음 형식으로 표시:
```
1. [페이지 제목](https://nota-dev.atlassian.net/wiki/spaces/.../pages/PAGE_ID)
   작성자: {owner} | 최종 수정: {date} | Space: {space_name}
   관련성: {이 페이지가 회의와 관련된 이유 간략 설명}
```

AskUserQuestion (multiSelect):
- "회의 내용을 기반으로 아래 문서들의 업데이트가 필요할 수 있습니다. 검토할 문서를 선택해주세요."
- 사용자가 선택 전에 링크를 클릭하여 각 페이지를 확인할 수 있음

### Step 4: 문서 내용 분석

confluence_get_page로 선택된 문서를 가져온 후:
1. 각 문서의 현재 내용 요약
2. 회의 의사결정과 문서 내용 비교
3. 변경이 필요한 **특정 섹션** 식별 (전체 페이지가 아님)

분류 기준:
- **필수(REQUIRED)**: 회의에서 명시적으로 결정된 사항이 현재 문서 내용과 직접 충돌 (예: 문서에는 "session 기반 인증"이지만 회의에서 "JWT 인증"으로 결정)
- **권장(RECOMMENDED)**: 문서 내용이 직접 충돌하지는 않지만 일관성을 위해 업데이트가 유익한 경우 (예: 이전 인증 흐름을 참조하는 온보딩 가이드)

### Step 5: 변경사항 제안

각 변경 제안에 대해 다음을 표시:
- 대상 문서 링크 + 구체적 섹션명
- 현재 내용 (인용 발췌)
- 제안 새 내용 (정확한 텍스트)
- 변경 사유 (어떤 회의 의사결정이 이 변경을 유발하는지)
- 분류: 필수(REQUIRED) 또는 권장(RECOMMENDED)

AskUserQuestion (multiSelect):
- "어떤 변경사항을 적용할까요?"
  - 필수 변경만 (N건)
  - 필수 + 권장 모두 (N건)
  - 개별 선택 모드

개별 선택 모드를 선택한 경우, AskUserQuestion으로 각 변경사항을 하나씩 확인한다.

### Step 6: 대상 페이지 최종 확인

업데이트를 적용하기 전, 직접 링크와 함께 최종 확인을 보여준다:

```
아래 페이지들이 수정됩니다:
1. [Authentication Policy](https://nota-dev.atlassian.net/wiki/...) — 3개 섹션 변경
2. [API Reference](https://nota-dev.atlassian.net/wiki/...) — 2개 섹션 변경

정확한 페이지인지 확인해주세요. 진행할까요?
```

AskUserQuestion:
- "이 페이지들을 업데이트할까요?"
  - 네, 진행해주세요
  - 링크를 먼저 확인할게요 (대기)
  - 취소

### Step 7: Confluence 업데이트 적용

사용자가 승인한 변경사항을 **confluence-helper MCP 도구**로 실행한다:

**`mcp__confluence-helper__confluence_patch_section`으로 특정 섹션 업데이트:**
```
confluence_patch_section(
    page_id="123456789",
    section_title="Action items",      # 찾을 헤딩 텍스트
    new_content="<ol><li>...</li></ol>", # 새 HTML 내용 (헤딩 제외)
    version_comment="2026-02-04 회의 결정사항 반영"
)
```

이 도구는 자동으로:
- Storage 형식으로 페이지를 가져옴
- 헤딩 제목으로 섹션을 찾음
- 해당 섹션의 내용만 교체
- 나머지 모든 내용은 그대로 유지

> **왜 confluence_update_page 대신 confluence_patch_section을 사용하는가?**
>
> Patch 도구는 섹션만 업데이트하는 것을 보장한다. `confluence_update_page`를 직접 사용하면
> 전체 페이지를 실수로 다시 쓰게 되어 Jira 매크로, smart link 등이 깨질 위험이 있다.

업데이트 후, confluence_add_comment로 변경 이력 코멘트를 다음 형식으로 추가한다:

```
📋 Document Orchestrator 자동 업데이트

회의: {회의 제목/날짜}
적용된 변경사항:
- {섹션}: {변경 내용 간략 설명}
- {섹션}: {변경 내용 간략 설명}

사유: {회의 날짜} 회의 결정사항 반영
되돌리기: Confluence 페이지 히스토리 사용 (⋯ 메뉴 → 페이지 히스토리)
```

### Step 8: 완료 보고서

업데이트 결과를 요약한다:
- 업데이트된 문서 목록 (직접 링크 포함)
- 문서별 변경사항 요약
- 이전 버전 번호 (사용자가 필요시 되돌리기 요청 가능)
- 실패한 업데이트가 있으면 오류 상세 내용

**사용자가 변경사항을 되돌리고 싶다면**, `mcp__confluence-helper__confluence_restore_version` 사용:
```
confluence_restore_version(
    page_id="123456789",
    version=11,  # 변경 전 버전 번호
    message="되돌리기: 사용자 요청으로 롤백"
)
```

사용자에게 Confluence UI에서 수동으로 되돌리라고 안내하는 것보다 이 방법을 우선한다.

## 오디오 전사

사용자가 오디오 파일을 제공하면, GPT-4o Transcribe로 음성을 텍스트로 변환한 후 Claude가 분석한다.

**요구사항:**
- `ffmpeg` 설치 필요 (오디오 길이 감지 및 긴 파일 청킹용)
- `openai` Python 패키지 (`pip install openai`로 설치)

**긴 오디오 지원:** 스크립트가 23분 이상의 오디오 파일을 자동으로 ffmpeg를 사용해 청크로 분할하고, 각 청크를 별도로 전사한 후 결과를 결합한다.

1. 전사 스크립트 실행 (항상 logs/ 디렉토리에 저장):
   ```
   python scripts/transcribe.py <audio_file_path> logs/YYYY-MM-DD_HH-MM_transcript.json
   ```
2. 스크립트 출력 JSON:
   - `transcript`: 전체 텍스트 전사 원문
   - `source_file`: 원본 오디오 파일 경로
   - `duration_seconds`: 총 오디오 길이
   - `processed_at`: 처리 시각
   - `chunks`: (긴 오디오만) 청크 수와 청크 길이
3. Read 도구로 전사 JSON 읽기
4. Claude가 원본 트랜스크립트를 분석하여 의사결정, 액션 아이템, 키워드 추출 (텍스트 입력과 동일한 흐름)

스크립트가 없거나 실패하면, 사용자에게 텍스트 트랜스크립트를 대신 제공해달라고 요청한다.

## 로깅

모든 업데이트 활동을 프로젝트의 logs/ 디렉토리에 기록한다:
- 파일명: YYYY-MM-DD_HH-MM_update.json
- 내용:
  ```json
  {
    "timestamp": "ISO 8601",
    "meeting_source": "file path or 'pasted text'",
    "meeting_title": "Meeting title or date",
    "meeting_summary": "2-3 sentence summary of the meeting",
    "attendees": ["Name (Role)", ...],
    "decisions": [
      "Decision 1 description",
      "Decision 2 description"
    ],
    "documents_analyzed": [
      {
        "page_id": "123456789",
        "title": "Page Title",
        "url": "https://nota-dev.atlassian.net/wiki/...",
        "owner": "Owner name",
        "last_updated": "ISO 8601"
      }
    ],
    "changes_proposed": [
      {
        "page_id": "123456789",
        "title": "Page Title",
        "url": "https://nota-dev.atlassian.net/wiki/...",
        "section": "Section name",
        "classification": "REQUIRED or RECOMMENDED",
        "description": "What was changed and why"
      }
    ],
    "changes_applied": [
      {
        "page_id": "123456789",
        "title": "Page Title",
        "url": "https://nota-dev.atlassian.net/wiki/...",
        "section": "Section name",
        "description": "What was changed",
        "version": "1 -> 2"
      }
    ],
    "changes_skipped": [
      {
        "page_id": "123456789",
        "title": "Page Title",
        "section": "Section name",
        "reason": "Why it was skipped"
      }
    ],
    "errors": [
      {
        "page_id": "123456789",
        "title": "Page Title",
        "error": "Error description"
      }
    ]
  }
  ```

## 중요 제약사항

- **섹션 단위 수정만 허용**: 전체 페이지를 교체하지 않는다. 변경이 필요한 특정 섹션만 수정한다.
- **항상 링크 표시**: Confluence 페이지를 참조할 때 항상 전체 클릭 가능 URL을 포함한다.
- **사용자 확인 필수**: 명시적인 사용자 승인 없이 페이지를 업데이트하지 않는다.
- **서식 유지**: 섹션 업데이트 시 기존 페이지 서식(헤딩, 테이블 등)을 유지한다.

## 핵심: Confluence 업데이트 규칙

> **참고:** `confluence_patch_section` helper 도구가 이를 자동으로 처리한다.
> 이 섹션은 맥락을 위해 근본적인 문제를 설명한다.

**페이지를 다시 쓰지 말 것. 특정 섹션만 패치할 것.**

Confluence 페이지에는 복잡한 XML 구조가 포함되어 있다:
- Jira 티켓 매크로 (`<ac:structured-macro ac:name="jira">`)
- Card appearance의 smart link
- 이모지 매크로 (`<ac:emoticon>`)
- 공동 편집을 위한 local ID
- 보존된 ID가 있는 중첩 리스트 구조

**왜 중요한가:** 변경 의도가 없는 섹션을 다시 쓰면 Jira 매크로가 일반 텍스트가 되고, smart link이 깨지며, 공동 편집 메타데이터가 유실된다.

**해결책:** 이를 모두 자동으로 처리하는 `confluence_patch_section`을 사용한다.

## Helper MCP 도구 (confluence-helper)

표준 `mcp-atlassian` 도구 외에, 이 스킬은 **confluence-helper** MCP 서버 (`scripts/helper_mcp.py`)를 사용한다:

| 도구 | 설명 |
|------|------|
| `confluence_patch_section` | 헤딩 제목으로 특정 섹션만 업데이트 |
| `confluence_get_history` | 페이지 버전 히스토리 조회 |
| `confluence_get_version_content` | 특정 버전의 내용 조회 |
| `confluence_restore_version` | 페이지를 이전 버전으로 복원 |

**항상 수동 작업보다 이 도구들을 우선 사용한다:**
- 더 안전한 업데이트를 위해 `confluence_update_page` 대신 `confluence_patch_section` 사용
- 사용자에게 수동 되돌리기를 안내하는 대신 `confluence_restore_version` 사용
