"""LLM-as-Judge relevance evaluation using OpenAI."""

from openai import OpenAI

JUDGE_MODEL = "gpt-4o-mini"

JUDGE_PROMPT = """당신은 회의록과 문서 간의 관련성을 평가하는 전문 평가자입니다.

## 회의록 내용
{transcript}

## 문서 제목
{doc_title}

## 문서 내용 (발췌)
{doc_content}

## 평가 기준
1점: 전혀 관련 없음 - 회의 주제와 문서 내용이 완전히 다른 영역
2점: 약간 관련 - 같은 프로젝트이지만 구체적 연결점 없음
3점: 보통 관련 - 일부 주제가 겹치지만 직접적 업데이트 필요성 낮음
4점: 높은 관련성 - 회의 결정사항이 문서 내용에 영향을 미침
5점: 매우 높은 관련성 - 회의에서 직접 언급된 문서이거나 즉시 업데이트가 필요

## 응답 형식
점수만 숫자로 응답하세요 (1-5).
"""


def judge_relevance(
    transcript: str,
    doc_title: str,
    doc_content: str,
) -> int:
    """Ask LLM to rate relevance of a document to a meeting transcript.

    Returns score 1-5.
    """
    client = OpenAI()
    prompt = JUDGE_PROMPT.format(
        transcript=transcript[:3000],
        doc_title=doc_title,
        doc_content=doc_content[:2000],
    )

    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=5,
        temperature=0,
    )

    text = response.choices[0].message.content.strip()
    try:
        score = int(text[0])
        return max(1, min(5, score))
    except (ValueError, IndexError):
        return 3  # default middle score on parse failure


def evaluate_search_results(
    transcript: str,
    results: list[dict],
) -> list[dict]:
    """Evaluate relevance of each search result against a transcript.

    Each result dict should have: page_id, title, content (optional).
    Returns list of dicts with added 'relevance_score' field.
    """
    evaluated = []
    for result in results:
        score = judge_relevance(
            transcript=transcript,
            doc_title=result.get("title", ""),
            doc_content=result.get("content", ""),
        )
        evaluated.append({**result, "relevance_score": score})

    return evaluated
