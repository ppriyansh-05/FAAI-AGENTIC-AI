import unittest

from audit_engine import contrast_ratio, findings_to_rows, planner_agent, run_audit
from sample_pages import BROKEN_STORE_PAGE, IMPROVED_STORE_PAGE


class AuditEngineTests(unittest.TestCase):
    def test_broken_demo_reports_expected_rules(self):
        result = run_audit(BROKEN_STORE_PAGE)
        rules = {finding.rule_id for finding in result["findings"]}
        self.assertEqual(result["counts"], {"High": 3, "Medium": 2, "Low": 0})
        self.assertSetEqual(rules, {"IMG_ALT", "FORM_LABEL", "PAGE_LANG", "PAGE_TITLE", "COLOR_CONTRAST"})

    def test_improved_demo_has_no_findings(self):
        self.assertEqual(run_audit(IMPROVED_STORE_PAGE)["findings"], [])

    def test_finding_has_wcag_recommendation_and_validation(self):
        finding = run_audit(BROKEN_STORE_PAGE)["findings"][0]
        self.assertIn("WCAG 2.2", finding.why_it_matters)
        self.assertTrue(finding.recommendation)
        self.assertTrue(finding.validation)

    def test_empty_input_is_handled_gracefully(self):
        result = run_audit("   ")
        self.assertEqual(result["status"], "no_input")
        self.assertEqual(result["findings"], [])

    def test_malformed_html_does_not_crash(self):
        result = run_audit("<html><img src='x'><input id='email'")
        self.assertEqual(result["status"], "complete")
        self.assertGreaterEqual(len(result["findings"]), 1)

    def test_planner_and_validation_are_exposed(self):
        self.assertEqual(planner_agent("<html>")["status"], "ready")
        result = run_audit(BROKEN_STORE_PAGE)
        self.assertEqual(len(result["human_checks"]), 4)
        self.assertIn("Critic check passed", result["critic_notes"][0])

    def test_csv_ready_finding_structure(self):
        rows = findings_to_rows(run_audit(BROKEN_STORE_PAGE)["findings"])
        self.assertEqual(len(rows), 5)
        self.assertIn("rule_id", rows[0])
        self.assertIn("recommendation", rows[0])

    def test_contrast_calculation(self):
        self.assertAlmostEqual(contrast_ratio("#000000", "#ffffff"), 21.0)
        self.assertLess(contrast_ratio("#777777", "#ffffff"), 4.5)


if __name__ == "__main__":
    unittest.main()
