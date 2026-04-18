from __future__ import annotations

from dataclasses import dataclass
from typing import Any


RECALL_PERCENTS = (5, 10, 20, 30, 40, 50, 60)


def safe_text(value: Any) -> str:
    return str(value or "").strip()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _sorted_ranked_rows(ranked_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        ranked_rows,
        key=lambda row: (-safe_float(row.get("score")), safe_text(row.get("key"))),
    )


def answer_label_to_score(label: str) -> float:
    normalized = safe_text(label).lower()
    if normalized == "positive":
        return 1.0
    if normalized == "neutral":
        return 0.5
    return 0.0


def _fbeta(precision: float, recall: float, beta: float) -> float:
    beta_sq = beta * beta
    denom = beta_sq * precision + recall
    if denom == 0.0:
        return 0.0
    return (1.0 + beta_sq) * precision * recall / denom


def compute_binary_metrics(*, tp: int, fp: int, tn: int, fn: int) -> dict[str, Any]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": _fbeta(precision, recall, 1.0),
        "f2": _fbeta(precision, recall, 2.0),
        "f3": _fbeta(precision, recall, 3.0),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def compute_binary_metrics_from_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    for row in results:
        gold = 1 if bool(row.get("gold_label")) else 0
        pred = 1 if int(row.get("prediction") or 0) else 0
        if gold == 1 and pred == 1:
            tp += 1
        elif gold == 1 and pred == 0:
            fn += 1
        elif gold == 0 and pred == 1:
            fp += 1
        else:
            tn += 1
    metrics = compute_binary_metrics(tp=tp, fp=fp, tn=tn, fn=fn)
    metrics["matched"] = len(results)
    metrics["results_size"] = len(results)
    metrics["gold_size"] = len(results)
    return metrics


def compute_average_precision(ranked_rows: list[dict[str, Any]]) -> float:
    positives = sum(1 for row in ranked_rows if bool(row.get("gold_label")))
    if positives <= 0:
        return 0.0
    running_tp = 0
    precision_sum = 0.0
    for rank, row in enumerate(_sorted_ranked_rows(ranked_rows), start=1):
        if bool(row.get("gold_label")):
            running_tp += 1
            precision_sum += running_tp / rank
    return precision_sum / positives


def rank_of_last_positive_at_recall(ranked_rows: list[dict[str, Any]], recall_threshold: float) -> int:
    sorted_rows = _sorted_ranked_rows(ranked_rows)
    positives = sum(1 for row in sorted_rows if bool(row.get("gold_label")))
    if positives <= 0:
        return 0
    running_tp = 0
    for rank, row in enumerate(sorted_rows, start=1):
        if bool(row.get("gold_label")):
            running_tp += 1
        recall = running_tp / positives
        if recall >= recall_threshold:
            return rank
    return len(sorted_rows)


def compute_ranking_metrics(ranked_rows: list[dict[str, Any]]) -> dict[str, Any]:
    sorted_rows = _sorted_ranked_rows(ranked_rows)
    total = len(sorted_rows)
    last_relevant_rank = rank_of_last_positive_at_recall(sorted_rows, 1.0)
    last_relevant_rank_95 = rank_of_last_positive_at_recall(sorted_rows, 0.95)
    wss95 = ((total - last_relevant_rank_95) / total) - 0.05 if total else 0.0
    recall_at_percent: dict[str, float] = {}
    positives = sum(1 for row in sorted_rows if bool(row.get("gold_label")))
    for percent in RECALL_PERCENTS:
        threshold = total * (percent / 100)
        amount = sum(
            1
            for rank, row in enumerate(sorted_rows, start=1)
            if rank <= threshold and bool(row.get("gold_label"))
        )
        recall_at_percent[f"R@{percent}%"] = (amount / positives) if positives else 0.0
    return {
        "map": compute_average_precision(sorted_rows),
        "wss95": wss95,
        "last_relevant_rank": last_relevant_rank,
        "recall_at_percent": recall_at_percent,
        "candidate_total": total,
        "positive_total": positives,
    }


@dataclass(frozen=True)
class ThresholdSelection:
    k: int
    metrics: dict[str, Any]


def choose_oracle_threshold_k(ranked_rows: list[dict[str, Any]]) -> dict[str, Any]:
    sorted_rows = _sorted_ranked_rows(ranked_rows)
    best = ThresholdSelection(k=0, metrics=compute_binary_metrics(tp=0, fp=0, tn=len(sorted_rows), fn=sum(1 for row in sorted_rows if bool(row.get("gold_label")))))
    for k in range(1, len(sorted_rows) + 1):
        metrics = compute_binary_metrics_from_results(
            [
                {
                    "gold_label": row.get("gold_label"),
                    "prediction": 1 if rank <= k else 0,
                }
                for rank, row in enumerate(sorted_rows, start=1)
            ]
        )
        if metrics["f1"] > best.metrics["f1"] or (metrics["f1"] == best.metrics["f1"] and k < best.k):
            best = ThresholdSelection(k=k, metrics=metrics)
    return {"k": best.k, "metrics": best.metrics}


def build_threshold_results(
    *,
    ranked_rows: list[dict[str, Any]],
    cutoff_excluded_rows: list[dict[str, Any]],
    k: int,
    strategy_id: str,
    threshold_id: str,
) -> dict[str, Any]:
    sorted_rows = _sorted_ranked_rows(ranked_rows)
    results: list[dict[str, Any]] = []
    for row in cutoff_excluded_rows:
        results.append(
            {
                "key": safe_text(row.get("key")),
                "title": safe_text(row.get("title")),
                "strategy_id": strategy_id,
                "threshold_id": threshold_id,
                "source": "cutoff",
                "prediction": 0,
                "gold_label": 1 if bool(row.get("gold_label")) else 0,
                "final_verdict": "exclude (cutoff_time_window)",
                "score": None,
                "rank": None,
            }
        )
    for rank, row in enumerate(sorted_rows, start=1):
        prediction = 1 if rank <= k else 0
        results.append(
            {
                "key": safe_text(row.get("key")),
                "title": safe_text(row.get("title")),
                "strategy_id": strategy_id,
                "threshold_id": threshold_id,
                "source": "ranked_candidate",
                "prediction": prediction,
                "gold_label": 1 if bool(row.get("gold_label")) else 0,
                "final_verdict": (
                    f"include (paper_faithful:{strategy_id}:{threshold_id})"
                    if prediction
                    else f"exclude (paper_faithful:{strategy_id}:{threshold_id})"
                ),
                "score": safe_float(row.get("score")),
                "rank": rank,
            }
        )
    return {
        "strategy_id": strategy_id,
        "threshold_id": threshold_id,
        "k": k,
        "results": results,
        "metrics": compute_binary_metrics_from_results(results),
    }


def compute_soft_vote_score(review_rows: list[dict[str, Any]]) -> float:
    if not review_rows:
        return 0.0
    question_count = len(review_rows[0].get("answers") or [])
    if question_count <= 0:
        return 0.0
    question_scores: list[float] = []
    for question_index in range(question_count):
        counts = {"positive": 0, "neutral": 0, "negative": 0}
        for row in review_rows:
            answers = row.get("answers") or []
            if question_index >= len(answers):
                continue
            label = safe_text((answers[question_index] or {}).get("answer_label")).lower()
            if label not in counts:
                label = "negative"
            counts[label] += 1
        top_count = max(counts.values())
        winners = [label for label, count in counts.items() if count == top_count]
        if len(winners) != 1:
            question_scores.append(0.5)
        else:
            question_scores.append(answer_label_to_score(winners[0]))
    return sum(question_scores) / len(question_scores)


def compute_mad_raw_score(review_rows: list[dict[str, Any]]) -> float:
    scores: list[float] = []
    for row in review_rows:
        for answer in row.get("answers") or []:
            scores.append(answer_label_to_score(safe_text((answer or {}).get("answer_label"))))
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def compute_adj_rank_score(*, primary_rows: dict[str, dict[str, Any]], judge_row: dict[str, Any]) -> float:
    judge_answers = judge_row.get("answers") or []
    if not judge_answers:
        return 0.0
    question_scores: list[float] = []
    for question_index, judge_answer in enumerate(judge_answers):
        ratings_payload = (judge_answer or {}).get("reviewer_ratings") or {}
        if isinstance(ratings_payload, dict):
            ratings = {safe_text(key): safe_float(value) for key, value in ratings_payload.items()}
        else:
            ratings = {
                safe_text(item.get("reviewer_role")): safe_float(item.get("rating"))
                for item in ratings_payload
                if isinstance(item, dict)
            }
        weighted_sum = 0.0
        weight_total = 0.0
        for reviewer_role, primary_row in primary_rows.items():
            answers = primary_row.get("answers") or []
            if question_index >= len(answers):
                continue
            weight = safe_float(ratings.get(reviewer_role))
            if weight <= 0.0:
                continue
            answer_score = answer_label_to_score(safe_text((answers[question_index] or {}).get("answer_label")))
            weighted_sum += answer_score * weight
            weight_total += weight
        if weight_total <= 0.0:
            question_scores.append(answer_label_to_score(safe_text((judge_answer or {}).get("answer_label"))))
        else:
            question_scores.append(weighted_sum / weight_total)
    if not question_scores:
        return 0.0
    return sum(question_scores) / len(question_scores)


def compute_adj_judge_score(judge_row: dict[str, Any]) -> float:
    answers = judge_row.get("answers") or []
    if not answers:
        return 0.0
    scores = [answer_label_to_score(safe_text((answer or {}).get("answer_label"))) for answer in answers]
    return sum(scores) / len(scores)
