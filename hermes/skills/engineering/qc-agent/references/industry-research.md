# QC Research Synthesis — Industry Standards for AI Agent Evaluation

Sources: Anthropic (Jan 2026), Galileo (Feb 2026)

## Core Concepts from Anthropic

**Two things to grade, not one:**
- OUTCOME — the final state. Did the code pass tests? Does the image match the prompt?
- TRAJECTORY — how the agent got there. Tool calls, reasoning, decisions.

"An evaluation is a test for an AI system: give an AI an input, then apply grading logic to its output to measure success."

**Grader types:**
- Code-based: deterministic, fast, cheap (tests, lint, regex, static analysis)
- Model-based (LLM-as-judge): rubric scoring, natural language assertions, flexible
- Human: gold standard, used to calibrate the other two

**Coding agents:** Use fail-to-pass tests (SWE-bench Verified pattern). If failing tests are fixed without breaking others, it passes.

## Core Concepts from Galileo

**Three-tier rubric taxonomy:** 7 dimensions → 25 sub-dimensions → 130 measurable items.

**Production target:** ≥ 0.80 Spearman correlation between LLM judge and human evaluators. Systematic pipeline achieves 0.86.

**Two temporal dimensions:**
- Pre-deployment validation: "Should we release this version?"
- Continuous production monitoring: track drift over time

**Key stat:** "Enterprise AI deployments show agents can achieve 60% success on single runs. That drops to 25% across eight runs." — this is why QC exists.

## How We Apply It

SovereignAI QC adapts the three-tier rubric to a minimal, token-efficient checklist per domain. We use LLM-as-judge (MiniMax M2.7) with deterministic code-based checks where possible (tests, lint). The 3-strike escalation loop is our own design — industry doesn't prescribe this, but the principle of progressive fallback (local model → large-context model → human) matches Anthropic's recommendation to combine automated and human grading.
