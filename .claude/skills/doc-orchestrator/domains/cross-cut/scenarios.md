# 공유 S0-S3 시나리오 정의

이 컨텍스트는 모든 part agent에 공통 지식으로 주입된다. 분석 결과의 설명(description, impact 등)은 한국어로 작성하되, 기술 용어는 영어를 그대로 사용한다.

## 시나리오 개요

| 시나리오 | 핵심 질문 | 목표 | 설명 |
|----------|----------|------|------|
| **S0** | "일단 돌아가나?" | Preset 기반 첫 성공 | 기본 pipeline이 동작하는 결과를 만들어내는가? |
| **S1** | "왜 이런 결과가 나왔지?" | 중간 결과 디버깅 | Pipeline이 왜 이 특정 출력을 만들었는가? |
| **S2** | "어떤 설정이 제일 좋은가?" | 사용자 정의 sweep 실험 | 어떤 configuration이 최적 결과를 내는가? |
| **S3** | "이 결과를 다시 평가할 수 있나?" | 사후 분석 및 재평가 | 과거 결과를 다시 확인하고 비교할 수 있는가? |

## S0: 첫 성공 (Preset Pipeline)

- 최소 config, 사용자는 모델 + 타겟 디바이스만 선택
- 기본 pipeline: `GO → GQ` 또는 `AQ → GO → GQ` (preset에 따라)
- Sweep 없음, 비교 없음 — 단일 실행
- 타겟: RPI5 + ExecuTorch + Xnnpack
- CLI: `np run --default`
- 성공 = 모델이 타겟 디바이스에서 실행되어 유효한 출력 생성

## S1: 결과 디버깅

- Layerwise SNR 분석 (연산자별 signal-to-noise ratio)
- 최적화 단계별 latency 분석
- Observer 통계 (tensor별 min/max/mean)
- Fallback 원인 분석 (왜 연산이 NPU에서 CPU로 fallback 되었는지)
- Probe를 통한 최적화 전/후 graph diff 시각화

## S2: Sweep 실험

- `sweep` 섹션이 있는 사용자 정의 YAML (다중 config)
- 다수의 AQ/GO/GQ variant 비교
- Metric 기반 `best` 선택 (latency, accuracy, SNR, model size)
- YAML 기반: `np run --config run.yaml`
- Dashboard에서 실행 간 비교

## S3: 사후 분석 및 재평가

- 과거 실행을 다른 metric으로 재평가
- 실험 간 교차 비교 (cross-experiment analysis)
- Dashboard에서 실험 비교 시각화
- Probe를 통한 서로 다른 최적화 결과의 graph diff
- Artifact 내보내기 (모델 파일, 리포트, config)

## Reference Pages

| 페이지 | Page ID |
|--------|---------|
| S0 CLI Scenario | `1968439297` |
| S1 CLI Scenario | `1992327173` |
| S2 CLI Scenario | `1991770151` |
| S3 CLI Scenario | `1993244710` |
| NetsPresso V2.0 User Scenarios & Module Goals | `1998290955` |

## Cross-Cut 확인 지시

자신의 part 관점에서 트랜스크립트를 분석한 후, 다음 cross-cut 확인을 수행한다:

1. **어떤 의사결정이 S0-S3 시나리오 정의를 변경하는가?**
   - 예: 기본 pipeline 순서 변경은 S0에 영향
   - 예: 새 metric 추가는 S2 best 선택 기준에 영향

2. **어떤 의사결정이 공유 pipeline 흐름을 변경하는가?**
   - 예: GO와 GQ 사이에 새 최적화 단계 추가
   - 예: 기본 타겟 디바이스를 RPI5에서 변경

3. **어떤 의사결정이 여러 part에 영향을 주는가?**
   - 예: 새 IR 노드 타입은 MR(데이터 구조)과 Q(QDQ 패턴) 모두에 영향
   - 예: 새 CLI 명령은 SWE(구현)와 관련 도메인 part에 영향

Cross-cut 영향이 감지되면 분석 출력에 다음과 같이 플래그한다:
```
cross_cut_impacts:
  - scenario: S0/S1/S2/S3
    impact: "이 의사결정이 시나리오에 미치는 영향 설명"
  - shared_pipeline: true/false
    impact: "pipeline 흐름 변경 설명"
  - affected_parts: [영향받는 다른 part 목록]
    impact: "cross-part 영향 설명"
```
