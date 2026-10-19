# Five Minute Speaking Script

## Slide 1 0:00 to 0:30

Good morning. I am Priyansh Pandey. My CA-3 project is AccessAble AI, a multi-agent accessibility auditor for web pages. The problem is that small web teams can publish simple accessibility barriers without noticing them during normal development.

## Slide 2 0:30 to 1:05

Examples include images with no text description, form fields without labels, and low-contrast text. A manual review is essential but takes time. This PoC gives a developer a first structured review and explains what they can fix before human testing.

## Slide 3 1:05 to 1:55

The workflow has six explicit stages. The Planner selects the supported deterministic checks. The Scanner finds HTML signals. The Standards Analyst maps them to WCAG 2.2. The Fix Recommendation Agent provides an implementation example. The Validation Agent separates automatic results from required human review. Finally, the Critic checks that every result has complete guidance.

## Slide 4 1:55 to 2:30

I built the PoC in Python and Streamlit. It uses Python's HTML parser and a WCAG contrast formula, so it does not require a paid API or an external model. This makes the demo repeatable and easy to test.

## Slide 5 2:30 to 3:30

In the demo, I select the broken store page and run the audit. It reports five findings: missing image alternative text, missing form label, missing language declaration, missing page title, and low inline contrast. I then select the improved page. Under the same five rules, the result becomes zero findings. Each finding contains evidence, a WCAG mapping, a recommended fix, and validation guidance. I can also download it as CSV.

## Slide 6 3:30 to 4:15

The important limitation is that zero automated findings does not prove that a page is accessible. A human must check meaningful descriptions, keyboard navigation, visible focus, screen-reader flow, dynamic content, and cognitive clarity. The interface displays this checklist so the limitation stays visible.

## Slide 7 4:15 to 5:00

AccessAble AI demonstrates how agent orchestration can make a focused QA task faster and more understandable. Future work could analyse full CSS and rendered pages, integrate browser-based tests, support batch audits, and allow a human reviewer to approve findings. The current project remains intentionally transparent and does not claim WCAG conformance. Thank you.
