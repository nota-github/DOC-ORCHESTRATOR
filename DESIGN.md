# Design: Agent & Classifier Flow

이 문서는 doc-orchestrator의 내부 동작 방식 — **Classifier로 회의 내용을 분류**하고, **Domain Agent가 전문 분석**을 수행하는 구조 — 을 설명합니다.

## Overview

```
Meeting Transcript
       │
       ▼
┌─────────────┐
│ Classifiers │  ← Topic + Part 동시 분류
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ Domain Agents (1~N) │  ← 분류된 Part별 전문 에이전트 실행
└──────┬──────────────┘
       │
       ▼
┌──────────────────┐
│ Integrate & Merge│  ← 에이전트 결과 통합 + Cross-cut 체크
└──────┬───────────┘
       │
       ▼
  Confluence Search & Update
```

## Classifiers

회의록이 입력되면 **2개의 Classifier**가 동시에 실행됩니다. 둘 다 프롬프트 기반이며, 외부 API 호출 없이 빠르게 동작합니다.

### Topic Classifier

회의의 **성격**을 분류합니다. 하나의 회의에 여러 Topic이 해당될 수 있습니다 (non-exclusive).

| Topic | 설명 | 키워드 예시 |
|-------|------|------------|
| Weekly Progress | 주간 진행 상황 공유 | weekly, 주간, 완료, status |
| Sprint Planning | 스프린트 계획 수립 | sprint, planning, backlog, 계획 |
| Scenario & Product | 제품 시나리오/기능 논의 | S0, S1, CLI, user flow |
| Technical Design | 설계/아키텍처 결정 | architecture, API, schema, 설계 |
| Experiment & Validation | 실험/검증 결과 | SNR, benchmark, latency, 검증 |

**출력:** `{ "topics": ["Weekly Progress", "Technical Design"] }`

### Part Classifier

회의에서 논의된 **엔지니어링 도메인**을 분류합니다. 역시 non-exclusive입니다.

| Part | 코드 | 담당 영역 |
|------|------|----------|
| Quantization | `Q` | 양자화 알고리즘 (AQ, GQ, observer, calibration) |
| Graph Optimization | `GO` | 그래프 최적화 (operator fusion, decomposition, backend lowering) |
| Model Representation | `MR` | 내부 IR 관리 (NPIR, EXIR, 변환, 텐서) |
| Model Engineering | `ME` | 벤치마크, 프로파일링, 디바이스 통합 |
| Software Engineering | `SWE` | CLI, workspace, 대시보드, 인프라 |

**출력:** `{ "parts": ["Q", "GO"] }`

**모호한 용어 처리 규칙:**
- "backend" → IR 변환 맥락이면 `MR`, 서버/API 맥락이면 `SWE`
- "experiment" → config sweep이면 `SWE`, 검증 테스트면 `ME`
- "lowering" → 양자화 모델이면 `Q`, 그래프 연산자면 `GO`

## Domain Agents

분류된 Part마다 **전문 에이전트**가 실행됩니다. 예를 들어 Classifier가 `["Q", "SWE"]`를 반환하면, Q Agent와 SWE Agent가 각각 회의록을 분석합니다.

### Agent가 하는 일

각 에이전트는 다음을 추출합니다:

```yaml
decisions:        # 회의에서 결정된 사항
action_items:     # 후속 조치 항목
keywords:         # Confluence 검색용 키워드
reference_pages:  # 참조할 Confluence 페이지 목록
cross_cut_impact: # 다른 도메인에 미치는 영향
```

### Topic-aware 분석

같은 Part Agent라도 Topic에 따라 분석 초점이 달라집니다.

**예시 — Q Agent:**
| Topic | 분석 초점 |
|-------|----------|
| Weekly Progress | 실험 결과, SNR 수치, lowering 성공/실패 |
| Sprint Planning | 양자화 마일스톤, 모델 커버리지 목표 |
| Technical Design | observer 아키텍처, QDQ 패턴 변경, calibration 흐름 |
| Experiment & Validation | 모델별/레이어별 SNR, lowering 성공률 |

### Cross-cut Context (Scenarios)

모든 에이전트는 **S0-S3 시나리오 컨텍스트**를 공유합니다.

| Scenario | 질문 | 목적 |
|----------|------|------|
| S0 | "일단 돌아가나?" | Preset 기본 실행 |
| S1 | "왜 이런 결과?" | 중간 디버깅/분석 |
| S2 | "어떤 설정이 최고?" | 사용자 커스텀 실험 |
| S3 | "재평가 가능한가?" | 사후 비교/재현 |

에이전트는 분석 시 항상 다음을 체크합니다:
1. 이 결정이 S0-S3 시나리오 정의를 바꾸는가?
2. 공유 파이프라인 흐름에 영향을 주는가?
3. 다른 Part에 영향을 미치는가?

## Integration

모든 에이전트의 출력이 모이면 **통합 단계**를 거칩니다:

```
Q Agent 출력  ──┐
GO Agent 출력 ──┤
MR Agent 출력 ──┼──▶  Merge & Deduplicate  ──▶  Confluence Search
ME Agent 출력 ──┤       - decisions 병합
SWE Agent 출력 ─┘       - action_items 중복 제거
                        - keywords 통합
                        - cross-cut 영향 확인
```

통합된 키워드로 Confluence를 검색하고, 에이전트가 지정한 reference page와 합쳐서 관련 문서 목록을 구성합니다. 이후 사용자 확인을 거쳐 문서 업데이트가 진행됩니다.

## File Structure

```
.claude/skills/doc-orchestrator/
├── SKILL.md                          # 메인 스킬 프롬프트 (8-step 실행 흐름)
└── domains/
    ├── classifiers/
    │   ├── topic.md                  # Topic Classifier 프롬프트
    │   └── part.md                   # Part Classifier 프롬프트
    ├── agents/
    │   ├── q.md                      # Quantization Agent
    │   ├── go.md                     # Graph Optimization Agent
    │   ├── mr.md                     # Model Representation Agent
    │   ├── me.md                     # Model Engineering Agent
    │   └── swe.md                    # Software Engineering Agent
    └── cross-cut/
        └── scenarios.md              # S0-S3 공유 컨텍스트
```

---

# Design: MCP Architecture

이 문서는 doc-orchestrator가 Confluence와 통신하기 위해 사용하는 **2개의 MCP 서버 구조** — 범용 `mcp-atlassian`과 프로젝트 전용 `confluence-helper` — 의 설계 배경과 동작 원리를 설명합니다.

## 구조

```
Claude Code (host process)
  │
  ├── stdio pipe ↔  mcp-atlassian (uvx mcp-atlassian)
  │                  ├── confluence_search
  │                  ├── confluence_get_page
  │                  ├── confluence_update_page
  │                  ├── confluence_create_page
  │                  └── confluence_add_comment
  │
  └── stdio pipe ↔  confluence-helper (python scripts/helper_mcp.py)
                     ├── confluence_patch_section    ← 섹션 단위 패치
                     ├── confluence_get_history       ← 버전 히스토리 조회
                     ├── confluence_get_version_content
                     └── confluence_restore_version   ← 버전 복원
```

두 서버 모두 `.mcp.json`에 선언되며, Claude Code가 시작할 때 각각 자식 프로세스로 spawn합니다. 프로세스 간 통신은 stdin/stdout 파이프를 통한 JSON-RPC입니다.

## 왜 MCP 서버가 2개인가

`mcp-atlassian`은 Confluence의 범용 CRUD를 제공하지만, doc-orchestrator에 필요한 **섹션 단위 패치**와 **버전 복원** 기능이 없습니다. 이를 보완하기 위해 `confluence-helper`를 별도로 구현했습니다.

| 기능 | mcp-atlassian | confluence-helper | 이유 |
|------|:---:|:---:|------|
| 페이지 검색/조회 | ✅ | - | 표준 기능 |
| 페이지 전체 업데이트 | ✅ | - | 표준 기능 |
| **섹션만 패치** | ❌ | ✅ | Confluence API 자체에 섹션 패치 없음 → 서버 사이드 파싱 필요 |
| **버전 히스토리** | ❌ | ✅ | mcp-atlassian 미지원 |
| **버전 복원** | ❌ | ✅ | get → compare → update 3-step 트랜잭션 필요 |

## confluence-helper가 직접 REST API를 호출하는 이유

MCP 서버는 다른 MCP 서버를 호출할 수 없습니다. 각 MCP 서버는 독립 프로세스로, host(Claude Code)와만 통신하며 서로의 존재를 모릅니다.

```
 ✅ Claude Code → mcp-atlassian     (host가 tool 호출)
 ✅ Claude Code → confluence-helper  (host가 tool 호출)
 ❌ confluence-helper → mcp-atlassian (MCP 간 직접 호출 불가)
```

따라서 `confluence-helper`는 `atlassian-python-api` 라이브러리로 Confluence REST API를 직접 호출합니다.

## stdio 통신 원리

MCP의 stdio 모드에서 host와 서버는 **파이프**로 연결됩니다.

```
Claude Code                              helper_mcp.py
  │                                          │
  ├─ pipe(write) ──→ stdin (fd 0)  ──→  readline()에서 블로킹 대기
  │                                          │
  └─ pipe(read)  ←── stdout (fd 1) ←──  결과를 write + flush
```

`mcp.run()`이 하는 일:

```
while True:
    line = stdin.readline()      ← 블로킹: 데이터 올 때까지 CPU 사용 없이 대기
    request = json_rpc_parse(line)
    result = call_tool(request)
    stdout.write(json_rpc_response(result))
```

JSON-RPC는 JSON으로 함수 호출을 표현하는 프로토콜입니다:

```json
// 요청 (Claude Code → helper_mcp.py stdin)
{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
 "params": {"name": "confluence_patch_section",
            "arguments": {"page_id": "123", "section_title": "Action items", ...}}}

// 응답 (helper_mcp.py stdout → Claude Code)
{"jsonrpc": "2.0", "id": 1,
 "result": {"content": [{"type": "text", "text": "{\"success\": true}"}]}}
```

HTTP 서버와 달리 포트를 열지 않고, OS 파이프로 통신하는 로컬 프로세스 간 RPC입니다.

## confluence_patch_section 동작 원리

Confluence 페이지에는 Jira 매크로, smart link, 이모지 등 복잡한 XML이 포함됩니다. 전체 페이지를 교체하면 이런 구조가 깨지므로, 변경이 필요한 섹션만 정확히 교체해야 합니다.

```
1. REST API로 storage format(raw XML) 가져오기
2. 정규식으로 헤딩 제목 매칭 → 섹션 경계(시작~다음 헤딩) 탐지
3. 해당 섹션 내용만 교체, 헤딩 태그와 나머지 페이지는 그대로 보존
4. storage format 그대로 REST API로 업데이트
```

이 전체 과정이 한 번의 MCP tool 호출 안에서 원자적으로 실행됩니다.

## 전체 흐름
1. Claude Code 시작
2. .mcp.json 읽음
3. subprocess.Popen("python", "scripts/helper_mcp.py") → 자식 프로세스 생성, pipe 연결
4. helper_mcp.py: mcp.run() → stdin.readline()에서 블로킹 대기
5. 사용자가 "이 섹션 업데이트해줘" 요청
6. Claude가 confluence_patch_section tool 호출 결정
7. Claude Code가 JSON-RPC 요청을 helper_mcp.py의 stdin pipe에 write
8. helper_mcp.py: readline() 반환 → 파싱 → confluence_patch_section() 실행 → Confluence API 호출
9. 결과를 stdout에 JSON-RPC로 write
10. Claude Code가 pipe에서 read → Claude에게 전달
11. 다시 4번으로 돌아가서 대기
