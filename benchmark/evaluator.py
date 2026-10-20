"""Quantitative Benchmark Evaluator for AccessAble AI.

Computes exact True Positives (TP), False Positives (FP), False Negatives (FN),
Precision, Recall, F1-Score, and Fix-and-Retest success metrics across fixtures.
"""
from __future__ import annotations

import json
import time
from typing import Any

from benchmark.test_fixtures import FIXTURES
from core.scanner import EnhancedAccessibilityScanner
from core.remediation import SandboxRetestEngine


def run_benchmark() -> dict[str, Any]:
    start_time = time.time()
    total_fixtures = len(FIXTURES)
    tp = 0
    fp = 0
    fn = 0
    tn = 0
    rule_metrics: dict[str, dict[str, int]] = {}

    fixture_results: list[dict[str, Any]] = []

    total_fixes_tested = 0
    total_fixes_succeeded = 0

    for fix in FIXTURES:
        scanner = EnhancedAccessibilityScanner(fix["html"])
        findings = scanner.scan_all()
        detected_rules = {f.rule_id for f in findings}
        expected_rules = fix["expected_violations"]

        # Track True/False detections
        cur_tp = len(detected_rules & expected_rules)
        cur_fp = len(detected_rules - expected_rules)
        cur_fn = len(expected_rules - detected_rules)

        tp += cur_tp
        fp += cur_fp
        fn += cur_fn
        if not expected_rules and not detected_rules:
            tn += 1

        # Evaluate remediation fix rate if violations exist
        if findings:
            retest_engine = SandboxRetestEngine(fix["html"])
            _, remediations, remaining = retest_engine.verify_remediations(findings)
            for r in remediations:
                total_fixes_tested += 1
                if r.retest_resolved:
                    total_fixes_succeeded += 1

        fixture_results.append({
            "id": fix["id"],
            "category": fix["category"],
            "description": fix["description"],
            "expected": list(expected_rules),
            "detected": list(detected_rules),
            "tp": cur_tp,
            "fp": cur_fp,
            "fn": cur_fn,
            "pass": (detected_rules == expected_rules),
        })

    elapsed_seconds = round(time.time() - start_time, 4)

    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 1.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 1.0
    f1_score = round(2 * (precision * recall) / (precision + recall), 4) if (precision + recall) > 0 else 1.0
    fix_success_rate = round(total_fixes_succeeded / total_fixes_tested, 4) if total_fixes_tested > 0 else 1.0

    return {
        "total_fixtures": total_fixtures,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "fix_success_rate": fix_success_rate,
        "total_fixes_tested": total_fixes_tested,
        "total_fixes_succeeded": total_fixes_succeeded,
        "execution_time_seconds": elapsed_seconds,
        "fixture_results": fixture_results,
    }


if __name__ == "__main__":
    report = run_benchmark()
    print("=== AccessAble AI Quantitative Benchmark Results ===")
    print(f"Total Fixtures Tested : {report['total_fixtures']}")
    print(f"Precision             : {report['precision'] * 100:.2f}% (TP: {report['true_positives']}, FP: {report['false_positives']})")
    print(f"Recall                : {report['recall'] * 100:.2f}% (FN: {report['false_negatives']})")
    print(f"F1-Score              : {report['f1_score']:.4f}")
    print(f"Fix Retest Pass Rate  : {report['fix_success_rate'] * 100:.2f}% ({report['total_fixes_succeeded']}/{report['total_fixes_tested']})")
    print(f"Execution Elapsed     : {report['execution_time_seconds']}s")
