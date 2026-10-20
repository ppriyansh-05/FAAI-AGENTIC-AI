import unittest
from core.models import Finding, AuditState
from core.scanner import EnhancedAccessibilityScanner, calculate_contrast_ratio
from core.security import validate_audit_url, is_ip_blocked
from core.remediation import SandboxRetestEngine, compute_unified_diff, AdaptiveRemediationSynthesizer
from core.orchestrator import AgentOrchestrator
from benchmark.evaluator import run_benchmark
from core.database import init_db, record_audit, get_audit_history
import ipaddress


class EnhancedAuditEngineTests(unittest.TestCase):
    def test_decorative_alt_is_not_flagged(self):
        """WCAG H67: alt='' must NOT be flagged as a missing text alternative."""
        html = '<!doctype html><html lang="en"><head><title>Test</title></head><body><img src="divider.png" alt=""></body></html>'
        scanner = EnhancedAccessibilityScanner(html)
        findings = scanner.scan_all()
        img_findings = [f for f in findings if f.rule_id == "IMG_ALT"]
        self.assertEqual(len(img_findings), 0)

    def test_aria_hidden_img_is_not_flagged(self):
        html = '<!doctype html><html lang="en"><head><title>Test</title></head><body><img src="icon.svg" aria-hidden="true"></body></html>'
        scanner = EnhancedAccessibilityScanner(html)
        findings = scanner.scan_all()
        img_findings = [f for f in findings if f.rule_id == "IMG_ALT"]
        self.assertEqual(len(img_findings), 0)

    def test_wrapping_label_is_valid(self):
        html = '<!doctype html><html lang="en"><head><title>Test</title></head><body><form><label>Search: <input type="text"></label></form></body></html>'
        scanner = EnhancedAccessibilityScanner(html)
        findings = scanner.scan_all()
        form_findings = [f for f in findings if f.rule_id == "FORM_LABEL"]
        self.assertEqual(len(form_findings), 0)

    def test_invalid_aria_labelledby_target_flagged(self):
        """Aria-labelledby referencing a missing ID must be flagged as unlabelled."""
        html = '<!doctype html><html lang="en"><head><title>Test</title></head><body><form><input id="email" aria-labelledby="ghost_id"></form></body></html>'
        scanner = EnhancedAccessibilityScanner(html)
        findings = scanner.scan_all()
        form_findings = [f for f in findings if f.rule_id == "FORM_LABEL"]
        self.assertEqual(len(form_findings), 1)

    def test_heading_order_gap_flagged(self):
        html = '<!doctype html><html lang="en"><head><title>Test</title></head><body><h1>Title</h1><h3>Sub-header</h3></body></html>'
        scanner = EnhancedAccessibilityScanner(html)
        findings = scanner.scan_all()
        heading_findings = [f for f in findings if f.rule_id == "HEADING_ORDER"]
        self.assertEqual(len(heading_findings), 1)

    def test_ssrf_blocks_private_ip_and_metadata(self):
        """Security: Guard against localhost, AWS/GCP metadata, and RFC1918 subnets."""
        valid, msg = validate_audit_url("http://127.0.0.1/admin")
        self.assertFalse(valid)
        self.assertTrue("prohibited" in msg.lower() or "blocked" in msg.lower())

        valid, msg = validate_audit_url("http://169.254.169.254/latest/meta-data/")
        self.assertFalse(valid)
        self.assertTrue("prohibited" in msg.lower() or "restricted ip" in msg.lower() or "blocked" in msg.lower())

        valid, msg = validate_audit_url("file:///etc/passwd")
        self.assertFalse(valid)
        self.assertIn("blocked protocol", msg.lower())

        # Test embedded user credentials in URL
        valid, msg = validate_audit_url("http://user:password@example.com")
        self.assertFalse(valid)
        self.assertIn("credentials", msg.lower())

    def test_ssrf_ipv4_mapped_ipv6_blocked(self):
        self.assertTrue(is_ip_blocked(ipaddress.ip_address("::ffff:127.0.0.1")))
        self.assertTrue(is_ip_blocked(ipaddress.ip_address("::ffff:10.0.0.1")))

    def test_remediation_sandbox_and_diff(self):
        html = '<html><head><title>T</title></head><body><p>Hello</p></body></html>'
        scanner = EnhancedAccessibilityScanner(html)
        findings = scanner.scan_all()
        self.assertTrue(any(f.rule_id == "PAGE_LANG" for f in findings))

        engine = SandboxRetestEngine(html)
        patched_html, results, records = engine.verify_remediations(findings, attempt_number=1)
        self.assertIn('lang="en"', patched_html)
        self.assertTrue(any(r.retest_resolved for r in results if r.rule_id == "PAGE_LANG"))
        self.assertTrue(len(records) > 0)
        self.assertTrue(records[0].resolved)

    def test_adaptive_agent_orchestrator_retry_record(self):
        state = AuditState(
            input_source="raw_html",
            raw_html="<!doctype html><html><head><title>Title</title></head><body><p>Hi</p></body></html>",
            max_retries=2,
        )
        orchestrator = AgentOrchestrator(state)
        res = orchestrator.run()
        self.assertEqual(res.status, "complete")
        self.assertLessEqual(res.critic_iteration, 2)
        self.assertGreaterEqual(len(res.agent_trace), 4)
        self.assertTrue(len(res.retry_history) > 0)
        self.assertIn("Applied strategy", res.retry_history[0].changed_action)

    def test_benchmark_reproducibility(self):
        results = run_benchmark()
        self.assertEqual(results["total_fixtures"], 18)
        self.assertGreaterEqual(results["precision"], 0.95)
        self.assertGreaterEqual(results["recall"], 0.95)

    def test_database_persistence(self):
        init_db()
        record_audit(
            audit_id="test_run_123",
            input_source="test_source",
            raw_html="<html><body>test</body></html>",
            finding_count=1,
            counts={"High": 1, "Medium": 0, "Low": 0},
            resolved_fix_count=1,
            retry_iterations=1,
            engine_mode="Python DOM",
            status="complete",
        )
        history = get_audit_history(limit=5)
        self.assertTrue(any(h["id"] == "test_run_123" for h in history))


if __name__ == "__main__":
    unittest.main()
