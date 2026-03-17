---
name: index-manager
description: RAG 벡터 인덱스 빌드 및 관리 도구 (개발자용)
allowed-tools: Read, Bash
---

# Index Manager

RAG 벡터 인덱스의 빌드, 증분 업데이트, 상태 확인을 수행합니다.

## Step 0: 환경 설정

1. `.env` 파일에서 환경변수 로드 (`CONFLUENCE_URL`, `CONFLUENCE_EMAIL`, `CONFLUENCE_TOKEN`, `OPENAI_API_KEY`)
2. 의존성 설치:
   ```bash
   pip install -q -r requirements.txt
   ```

## Step 1: 인덱스 상태 확인

1. `data/vectordb/.last_indexed` 파일 존재 여부 확인
2. **존재하면:**
   - 마지막 인덱싱 시각 표시
   - ChromaDB collection의 chunk 수 표시:
     ```bash
     python -c "from scripts.rag.store import VectorStore; s = VectorStore(); print(s.get_stats())"
     ```
3. **존재하지 않으면:** "인덱스가 없습니다" 표시

## Step 2: 작업 선택

AskUserQuestion으로 사용자에게 질문:

> 어떤 작업을 수행할까요?
> 1. 풀 빌드 (전체 페이지를 새로 인덱싱)
> 2. 증분 업데이트 (마지막 인덱싱 이후 수정된 페이지만)
> 3. 상태 확인만 (여기서 종료)

"상태 확인만"을 선택하면 Step 1 결과를 보여주고 종료합니다.

## Step 3: 인덱스 빌드 실행

선택에 따라 실행:

- **풀 빌드:**
  ```bash
  python scripts/rag/index.py
  ```
- **증분 업데이트:**
  ```bash
  python scripts/rag/index.py --incremental
  ```

실행 중 진행 상황(페이지 수, chunk 수, 임베딩 수)을 표시합니다.

## Step 4: 결과 보고

완료 후 다음 정보를 표시:
- 인덱싱된 페이지 수
- 생성된 chunk 수
- collection 총 chunk 수
- 소요 시간

## 제약사항

- 이 스킬은 Confluence 문서를 **수정하지 않습니다** (읽기 전용)
- 인덱스 빌드에는 OpenAI API 호출(임베딩)이 필요하므로 비용이 발생할 수 있음을 안내
