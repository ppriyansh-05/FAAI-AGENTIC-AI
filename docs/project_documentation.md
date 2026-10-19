# AccessAble AI Project Documentation

## Purpose

AccessAble AI is a domain-specific software quality PoC for teams that publish web pages. It helps a developer or QA reviewer identify selected accessibility barriers early, before a human accessibility review. The domain is web development and quality assurance, where small teams commonly need fast, understandable feedback during content review.

## Business challenge

Manual accessibility review takes specialist time, while developers can miss basic HTML signals such as absent image alternatives, unlabelled form fields, missing document metadata, and weak text contrast. A tool that only reports an error code can also slow remediation because the developer must research the relevant standard and implementation approach.

## Proposed solution

The Streamlit application accepts a synthetic demo page or pasted HTML. A deterministic agent workflow plans supported checks, scans the supplied HTML, maps findings to WCAG 2.2 criteria, gives implementation-focused guidance, labels the boundary of automatic validation, and checks that each finding contains complete hand-off information. It then provides a severity-grouped report, a CSV download, and a human-review checklist.

## Implemented agent workflow

1. **Planner Orchestrator** accepts valid HTML and lists the five supported checks. Empty input stops safely.
2. **Scanner Agent** parses supplied HTML and detects missing alt text, missing form names, language, title, and low inline foreground/background contrast.
3. **Standards Analyst Agent** maps each rule to relevant WCAG 2.2 success criteria.
4. **Fix Recommendation Agent** adds an actionable remediation and code example.
5. **Validation Agent** states what the deterministic check established and creates the human checklist.
6. **Critic Agent** verifies every finding contains standards context, a recommendation, and validation guidance.

The workflow is agentic in the narrow, demonstrable sense used here: separate functions hand structured output to the next stage and make explicit decisions. It does not use an external LLM, autonomous browsing, persistent memory, or claims of full compliance.

## Results with supplied synthetic pages

| Page | Expected result under implemented rules |
|---|---:|
| Broken store page | 5 findings: 3 High, 2 Medium |
| Improved store page | 0 findings |

## Validation boundary

Automation checks structural presence and a limited inline-colour calculation. A human must still assess whether alt text is meaningful, keyboard and focus behaviour work, dynamic announcements make sense, and instructions are suitable in context. The tool must not be used as a WCAG conformance certificate.

## Tests

`python -m unittest discover -s tests -v` exercises the two sample pages, all rule types, contrast calculation, WCAG mapping, recommendations, empty input, malformed HTML, planner output, critic output, and human-review checklist generation.

## References

1. W3C. Web Content Accessibility Guidelines (WCAG) 2.2. https://www.w3.org/TR/WCAG22/
2. W3C. Easy Checks: A First Review of Web Accessibility. https://www.w3.org/WAI/test-evaluate/preliminary/
3. Streamlit documentation. https://docs.streamlit.io/
