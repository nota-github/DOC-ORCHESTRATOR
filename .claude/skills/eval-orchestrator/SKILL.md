---
name: eval-orchestrator
description: doc-orchestrator 검색 품질 및 수락률 평가 도구 (개발자용)
allowed-tools: Read, Bash
---

# Eval Orchestrator

검색 품질(키워드 vs RAG 비교)과 시스템 수락률을 측정하는 평가 스킬입니다.

## Step 0: 환경 설정

1. `.env` 파일에서 환경변수 로드
2. 의존성 설치:
   ```bash
   pip install -q -r requirements.txt
   ```

## Step 1: 평가 유형 선택

AskUserQuestion으로 사용자에게 질문:

> 어떤 평가를 실행할까요?
> 1. 검색 비교 평가 (키워드 vs RAG)
> 2. 수락률 평가
> 3. 전체 평가 (둘 다)

## Step 2a: 검색 비교 평가 (선택 시)

### 전제 조건 확인

1. `test-data/sample_meetings/` 디렉토리에 샘플 회의 JSON 파일이 있는지 확인
2. RAG 인덱스가 빌드되어 있는지 확인 (`data/vectordb/.last_indexed` 존재 여부)
3. 인덱스가 없으면: "RAG 인덱스가 없습니다. `/index-manager`로 먼저 빌드해주세요." 안내 후 키워드 검색만으로 진행할지 확인

### 실행

```bash
python scripts/evaluate.py --search-only --meetings-dir test-data/sample_meetings
```

### 결과 설명

- 회의별 Jaccard 유사도 (키워드 vs RAG 결과 겹침 정도)
- RAG가 추가로 찾아낸 문서 수 (`rag_only_count`)
- 키워드만 찾은 문서 수 (`keyword_only_count`)

## Step 2b: 수락률 평가 (선택 시)

### 전제 조건 확인

1. `logs/` 디렉토리에 `*_update.json` 파일이 있는지 확인
2. 없으면: "아직 업데이트 로그가 없습니다. `/doc-orchestrator`를 사용하면 자동으로 쌓입니다." 안내

### 실행

```bash
python scripts/evaluate.py --acceptance-only
```

### 결과 설명

- 전체 수락률
- REQUIRED vs RECOMMENDED 분류별 수락률
- 시간에 따른 추세 (로그가 여러 개일 때)

## Step 3: 리포트 확인

- `logs/evaluation_report_YYYY-MM-DD.json` 과 `.md` 파일 경로 안내
- Markdown 리포트 내용 요약 표시

## 샘플 회의 데이터 형식

`test-data/sample_meetings/` 에 들어가는 JSON 파일 형식:

```json
{
  "transcript": "회의 트랜스크립트 텍스트...",
  "summary": "회의 요약 2-3문장",
  "keywords": ["GQ", "calibration", "Xnnpack", "lowering"]
}
```
