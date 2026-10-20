# AccessAble AI — Architecture & Agent Orchestration

AccessAble AI is an autonomous, multi-agent accessibility auditing and remediation engine built to detect Web Content Accessibility Guidelines (WCAG 2.2) barriers and synthesize verified, non-destructive code patches.

```mermaid
flowchart TD
    subgraph Input ["Input Gateway"]
        U[User Interface / CI] --> InputChoice{Audit Source}
        InputChoice -->|Static HTML / File| StaticSource[HTML File / Text]
        InputChoice -->|Public Web URL| SecGuard[SSRF Security Firewall]
    end

    subgraph Orchestrator ["Agent State Machine"]
        SecGuard --> Planner[Agent 0: Planner & Capability Assessor]
        StaticSource --> Planner

        Planner --> ScannerRouter{Scanner Engine}
        ScannerRouter -->|DOM & Style Parse| PythonScanner[Agent 1A: Deterministic DOM Engine]
        ScannerRouter -->|Full Rendered DOM| PlaywrightScanner[Agent 1B: Playwright + Axe-Core Engine]

        PythonScanner --> Harmonizer[Signal Harmonizer & Deduplicator]
        PlaywrightScanner --> Harmonizer

        Harmonizer --> Standards[Agent 2: WCAG Standards Analyst]
        Standards --> Remediation[Agent 3: Remediation Patch Synthesizer]

        Remediation --> Sandbox[Agent 4: Isolated Sandbox Retester]
        Sandbox --> CriticDecision{Critic: Clean Fix & Zero Regressions?}
        
        CriticDecision -->|Regression or Unresolved & Retries < 3| Remediation
        CriticDecision -->|Verified Clean or Max Retries Hit| Validator[Agent 5: Validation Boundary]
    end

    subgraph Output ["Human-in-the-Loop & Delivery"]
        Validator --> DiffView[Unified Before/After Code Diff]
        Validator --> Checklist[Mandatory Human Review Checklist]
        Validator --> Exports[CSV / JSON / HTML Report Export]
    end
```

## Agent Hand-Off Contracts

| Agent | Input State | Output State | Core Decision Logic |
|---|---|---|---|
| **Agent 0: Planner** | Input HTML or validated URL | Structured Execution Plan | Validates URL against SSRF firewall; selects optimal engine (Playwright vs. Python DOM). |
| **Agent 1: Scanner** | HTML or live URL | Raw Finding Signals | Detects WCAG violations (missing alt, unlabelled forms, contrast, heading order, link text). |
| **Agent 2: Standards Analyst** | Raw Finding Signals | Normative WCAG Mappings | Cross-references violations to specific WCAG 2.2 Success Criteria (1.1.1, 1.3.1, 1.4.3, 2.4.2, 2.4.4, 3.1.1). |
| **Agent 3: Remediation Agent** | Normalized Findings | Proposed Replacement Patches | Synthesizes contextual code fixes for offending DOM nodes. |
| **Agent 4: Critic & Retester** | Original HTML & Candidate Patches | Retest Results & Unified Diffs | Applies patch in isolated memory buffer; re-runs scanner; verifies resolution and flags new regressions. |
| **Agent 5: Validation Boundary** | Verified Results | Human Checkpoints & Exports | Explicitly distinguishes automated checks from mandatory assistive tech human verification. |

## Defense in Depth: Security Model
- **SSRF Protection**: Target URLs are validated using DNS pre-flight inspection against RFC 1918 private subnets, loopback addresses (`127.0.0.1`), link-local metadata endpoints (`169.254.169.254`), and non-HTTP protocols.
- **Isolated Sandbox**: Fixes are never applied directly to production files or live servers; all patches are computed and verified within an isolated in-memory buffer.
