# Topic Classifier

회의 트랜스크립트의 주제를 분류하는 classifier. 한국어 회의록이 주로 입력되지만, AI/SW 기술 용어는 영어로 나올 수 있다.

## 분류 규칙

- 트랜스크립트를 읽고 아래 키워드 패턴과 매칭
- 해당하는 주제를 **모두** 선택 (개수 제한 없음)
- 주제는 **비배타적** — 한 회의가 여러 주제를 다룰 수 있음
- 출력은 JSON 배열로 topic 이름만 (topic 이름은 영어 코드로 유지)

## Topics

| Topic | 키워드 패턴 | 설명 |
|-------|------------|------|
| **Weekly Progress** | weekly, 주간, progress, status, done, to-do, 완료, 진행, 이번 주, 다음 주, 금주, 차주, 이번주, 다음주 | 정기 현황 보고 및 진행 상황 공유 |
| **Sprint Planning** | sprint, planning, goal, epic, story, task, backlog, retrospective, 스프린트, 계획, 목표, 회고, 백로그 | Sprint ceremony 및 작업 계획 |
| **Scenario & Product** | S0, S1, S2, S3, scenario, CLI, workspace, experiment, user flow, product, preset, 시나리오, 사용자, 유저 플로우 | 제품 시나리오 및 사용자 대면 기능 논의 |
| **Technical Design** | architecture, API, schema, sequence diagram, interface, module design, config, 설계, 구조, 아키텍처, 시퀀스 다이어그램 | 아키텍처 및 설계 의사결정 |
| **Experiment & Validation** | SNR, lowering, test, benchmark, model zoo, latency, accuracy, PPL, validation, 실험, 검증, 테스트, 성능, 벤치마크 | 테스트, 벤치마킹 및 검증 결과 |

## Output Format

```json
{
  "topics": ["Topic Name 1", "Topic Name 2"]
}
```

## Examples

- 트랜스크립트에 "이번 주 완료 항목"과 "SNR 결과" 언급 → `{"topics": ["Weekly Progress", "Experiment & Validation"]}`
- 트랜스크립트에 "S0 시나리오 변경"과 "CLI flow" 언급 → `{"topics": ["Scenario & Product"]}`
- 트랜스크립트에 "sprint goal"과 "backlog grooming" 언급 → `{"topics": ["Sprint Planning"]}`
- 트랜스크립트에 "API schema 변경"과 "시퀀스 다이어그램" 언급 → `{"topics": ["Technical Design"]}`
