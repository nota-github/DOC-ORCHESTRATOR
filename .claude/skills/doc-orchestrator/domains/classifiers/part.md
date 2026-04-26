# Part Classifier

회의 트랜스크립트에서 관련 part(팀)를 분류하는 classifier. 한국어 회의록이 주로 입력되지만, 기술 용어는 영어로 나올 수 있다.

## 분류 규칙

- 트랜스크립트를 읽고 아래 키워드 패턴과 매칭
- 논의되거나 영향받는 part를 **모두** 선택 (개수 제한 없음)
- Part는 **비배타적** — 한 회의가 여러 part에 관련될 수 있음
- 키워드가 모호한 경우, 문맥으로 판단 (아래 모호성 해소 참고)
- 출력은 JSON 배열로 part 코드만

## Parts

| Part | 코드 | 키워드 패턴 | 설명 |
|------|------|------------|------|
| **Quantization** | `Q` | quantization, AQ, GQ, observer, calibration, SNR, precision, W8A8, SmoothQuant, AWQ, MPQ, AMP, RTN, QDQ, quantize, dequantize, 양자화, 캘리브레이션 | 가중치/활성화 양자화 알고리즘 및 pipeline |
| **Graph Optimization** | `GO` | graph optimizer, NPGO, operator fusion, decomposition, Xnnpack lowering, Ethos decompose, TOSA, Vela, FVP, fusion, NPU lowering, 그래프 최적화, 연산자 융합, 분해 | 그래프 레벨 최적화 및 backend lowering |
| **Model Representation** | `MR` | IR manager, NPIR, EXIR, conversion, tensor, graph structure, frontend, backend (IR context), node, module (IR context), lookup table, 변환, 그래프 구조 | 내부 그래프 표현 및 포맷 변환 |
| **Model Engineering** | `ME` | benchmark, profiling, device, latency, model zoo, RPI, E2E pipeline, Alif, executorch runtime, .pte, .pt2, device farm, 벤치마크, 프로파일링, 디바이스, 레이턴시 | 벤치마킹, 프로파일링, 디바이스 통합 |
| **Software Engineering** | `SWE` | CLI, backend server, workspace, experiment (product context), np run, dashboard, probe, sprint ops, Typer, Rich, run.yaml, monorepo, 워크스페이스, 대시보드 | CLI 도구, 제품 기능, 인프라 |

## 모호성 해소

- **"backend"**: IR 변환(NPIR → 타겟 포맷)을 논의하면 `MR`. 서버/API를 논의하면 `SWE`.
- **"experiment"**: 최적화 config/sweep을 논의하면 `SWE` (제품 기능). 검증 테스트를 논의하면 `ME`.
- **"lowering"**: 양자화 모델 lowering(QDQ → 타겟)을 논의하면 `Q`. 그래프 레벨 연산자 lowering(decomposition)을 논의하면 `GO`.
- **"module"**: NPIR module(노드 그룹)을 논의하면 `MR`. Python module/package를 논의하면 `SWE`.

## Output Format

```json
{
  "parts": ["Q", "GO", "MR", "ME", "SWE"]
}
```

## Examples

- "GQ calibration"과 "SNR 결과" 논의 → `{"parts": ["Q"]}`
- "Xnnpack lowering 성공"과 "operator fusion" 논의 → `{"parts": ["GO"]}`
- "NPIR 노드 구조"와 "EXIR 변환" 논의 → `{"parts": ["MR"]}`
- "RPI5 벤치마크"와 "레이턴시 프로파일링" 논의 → `{"parts": ["ME"]}`
- "CLI np run"과 "workspace init" 논의 → `{"parts": ["SWE"]}`
- "GQ lowering to Xnnpack"과 "operator decomposition" 논의 → `{"parts": ["Q", "GO"]}`
- "S0 시나리오"와 "np run --default"와 "SNR 체크" 논의 → `{"parts": ["Q", "SWE"]}`
