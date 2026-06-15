# IC Agent Experimental setup

## Requirements & Architecture Specification

### Author

Abhinav Gupta

### Objective

Build an agentic analytics framework capable of solving business questions through iterative probing of structured enterprise data.

Unlike traditional retrieval agents that stop when they can answer a question, this system should continue exploring until the expected value of additional probes becomes sufficiently low.

The system must separate:

* Problem solving
* Probe generation
* Tool execution
* Probe evaluation
* Stopping decisions
* Final synthesis

to maximize reasoning quality and maintain domain portability.

---

# Core Design Principles

## Principle 1: Planning must be tool-agnostic

Reasoning should not depend on implementation details.

Planning components must never know:

* available tools
* APIs
* function signatures
* execution constraints

They should think only in terms of:

* objectives
* hypotheses
* information gaps
* evidence requirements

---

## Principle 2: Retrieval is a black box

Assumption:

Given a sufficiently precise question, the retrieval system returns correct answers.

The system therefore optimizes:

**Question quality**

rather than:

**SQL quality**

---

## Principle 3: Stopping is based on marginal value

The agent should not ask:

> Can I answer?

Instead ask:

> Would another probe significantly improve my answer?

---

## Principle 4: Exploration before synthesis

The agent should actively search for:

* alternative explanations
* competing hypotheses
* missing evidence

before producing conclusions.

---

# High-Level Architecture

```text
User Query
    |
    v
Planner Consultant
    |
    v
Planner
    |
    v
Tool Execution Layer
    |
    v
Retrieval Service
    |
    v
Decision Consultant
    |
    v
Decision Engine
    |
    +----> Planner Consultant (loop)
    |
    v
Final Answer Synthesizer
```

---

# Shared Prompt Architecture

Every service contains:

```python
{
    "system_prompt": "...",
    "domain_prompt": "..."
}
```

## System Prompt

Defines:

* purpose
* behavior
* responsibilities
* output contract

Static across domains.

---

## Domain Prompt

Defines:

* business context
* dataset descriptions
* metric definitions
* common terminology
* business rules

Customizable per domain.

Example:

```text
China Sales Domain

Datasets:
- Sales
- Revenue
- Pricing
- Portfolio

Metrics:
- Volume
- Revenue
- Margin

Dimensions:
- Brand
- Portfolio
- Region
```

---

# Component Specifications

---

# 1. Similar Plan Service

## Purpose

Provide planning precedents.

Must not return answers.

Must not return data.

Only return:

* reasoning patterns
* probe patterns
* solution structures

---

## Inputs

```json
{
  "user_query": "...",
  "domain_context": {...}
}
```

---

## Outputs

```json
{
  "matched_patterns": [
    {
      "pattern_id": "...",
      "confidence": 0.91,
      "reason": "...",
      "probe_strategy": [...]
    }
  ]
}
```

---

## Corpus Structure

Store archetypes, not examples.

Example:

```json
{
  "id": "root_cause_metric_change",
  "intent": "explain change in metric",
  "probe_sequence": [
    "trend",
    "decomposition",
    "segment analysis",
    "driver analysis"
  ],
  "failure_modes": [
    "missing baseline",
    "premature attribution"
  ],
  "stop_condition":
    "top drivers explain majority of change"
}
```

---

## Retrieval Strategy

Hybrid Retrieval

### Stage 1

Metadata filtering

```text
Domain
Intent
Dataset family
Analysis type
```

### Stage 2

Vector similarity

### Stage 3

Reranking

---

# 2. Planner Consultant

## Purpose

Convert business question into investigation plan.

Cannot see tools.

Cannot see APIs.

Cannot execute anything.

---

## Inputs

```json
{
  "query": "...",
  "domain_context": {...},
  "similar_patterns": [...]
}
```

---

## Responsibilities

Generate:

* objectives
* hypotheses
* probe goals
* investigation strategy

---

## Output Schema

```json
{
  "objective": "...",

  "hypotheses": [
    {
      "id": "H1",
      "description": "..."
    }
  ],

  "probe_candidates": [
    {
      "id": "P1",
      "goal": "...",
      "expected_value": "high",
      "reason": "..."
    }
  ],

  "success_criteria": "...",

  "open_questions": [...]
}
```

---

# 3. Planner

## Purpose

Translate probe goals into executable tool actions.

Knows:

* tools
* APIs
* execution constraints

---

## Inputs

```json
{
  "consultant_plan": {...}
}
```

---

## Responsibilities

Determine:

* tool selection
* execution order
* batching opportunities

---

## Output

```json
{
  "tool_calls": [...]
}
```

---

# 4. Retrieval Layer

## Purpose

Execute probe questions.

Treated as authoritative.

---

The input and output will be defined by the api we'll be using. For now, scaffold a client that can call a mock retrieval service with the following interface:

```python
class RetrievalService:
    def query(self, question: str) -> str:
        # Mock implementation
        return "Mock answer to: " + question
```

---

# 5. Evidence Ledger

## Purpose

Persistent memory across loops.

Stores all probes and outcomes.

---

## Schema

```json
{
  "probe_id": "...",

  "question": "...",

  "result": "...",

  "relevance_score": 0.87,

  "gap_closed": "...",

  "created_at": "..."
}
```

---

## Requirements

Must persist across iterations.

Decision services must always read ledger.

Never evaluate only latest probe.

---

# 6. Decision Consultant

## Purpose

Evaluate evidence quality.

Cannot execute tools.

Cannot stop execution.

Only evaluate.

---

## Inputs

```json
{
  "query": "...",
  "ledger": [...]
}
```

---

## Output

```json
{
  "relevant_probes": [...],

  "irrelevant_probes": [...],

  "remaining_gaps": [...],

  "new_hypotheses": [...],

  "confidence": 0.72
}
```

---

# Gap Categories

### Closed

Question answered.

### Partial

Evidence exists but insufficient.

### Open

No evidence.

### Conflicting

Evidence disagrees.

---

# 7. Decision Engine

## Purpose

Determine whether another probe cycle is worthwhile.

---

## Inputs

```json
{
  "ledger": [...],
  "decision_consultant_output": {...}
}
```

---

## Core Question

Not:

> Can I answer?

Instead:

> Is another probe likely to improve answer quality enough to justify cost?

---

## Output

```json
{
  "continue": true,

  "expected_incremental_value": 0.42,

  "recommended_next_gap":
    "pricing contribution",

  "reason": "..."
}
```

---

# Incremental Value Framework

Score:

### Evidence Coverage

Weight: 30%

---

### Confidence

Weight: 25%

---

### Remaining Gaps

Weight: 20%

---

### Alternative Hypotheses

Weight: 15%

---

### Probe Cost

Weight: 10%

---

Example:

```text
Coverage: 0.8
Confidence: 0.7
Gaps: 0.6
Alternatives: 0.4
Cost: 0.2

Expected Value = 0.61
```

---

## Stop Conditions

Stop when:

```text
Expected Incremental Value < Threshold
```

OR

```text
Max probe budget reached
```

OR

```text
All major gaps closed
```

---

# Probe Budget Controls

Configurable.

Example:

```yaml
max_rounds: 5
max_probes_per_round: 6
max_total_probes: 20
```

---

# 8. Final Answer Synthesizer

## Purpose

Convert evidence into user-facing answer.

---

## Inputs

```json
{
  "query": "...",
  "ledger": [...]
}
```

---

## Responsibilities

Produce:

### Conclusion

### Supporting Evidence

### Confidence

### Caveats

### Recommended Actions

### Remaining Unknowns

---

## Output Structure

```markdown
## Summary

...

## Key Findings

...

## Evidence

...

## Recommendations

...

## Confidence

...

## Remaining Unknowns

...
```

---

# State Model

```python
class AgentState:
    query: str

    objectives: List

    hypotheses: List

    probe_queue: List

    completed_probes: List

    evidence_ledger: List

    remaining_gaps: List

    confidence: float

    rounds_completed: int
```

---

# LangGraph Implementation Notes

Recommended nodes:

```text
START

↓

SimilarPlanNode

↓

PlannerConsultantNode

↓

PlannerNode

↓

ExecutionNode

↓

DecisionConsultantNode

↓

DecisionNode

↓

Continue?
    |
    +---- Yes → PlannerConsultantNode
    |
    +---- No → SynthesisNode

↓

END
```

# Success Criteria

The system is considered successful when:

1. It consistently performs multiple probe cycles before stopping when appropriate.
2. It stops because marginal value is low, not because a superficial answer exists.
3. Planning remains tool-agnostic.
4. Retrieval remains fully abstracted.
5. Evidence is accumulated and evaluated across iterations.
6. New hypotheses can emerge during exploration.
7. Final answers include confidence and evidence-backed reasoning.

# Additional Instructions

- Focus on modularity and separation of concerns.
- Separate configs and env variables cleanly
- Implement robust logging for all components.
- Ensure all components are testable in isolation.
- Assume retrieval service is an API call which will be provided later. Scaffold a client for it with a mock response for now.
- Separate utility functions into a utils module and prompts into a prompts module for maintainability.
- All boundaries use pydantic models for input/output validation and documentation. Never pass raw dicts or primitives across service boundaries.
- Use uv for package management and script execution. Define clear scripts for running the system, testing, and any maintenance tasks.
- Document all assumptions and design decisions in code comments and documentation.
- Prioritize clarity and maintainability over cleverness in code implementation.
- Ensure all components can be easily extended or replaced without affecting others, adhering to the defined interfaces.
- Implement constraints on iteration limits and probe budgets to prevent infinite loops or excessive probing.
- Design the system to be easily adaptable to different domains by simply changing the domain prompt and similar plan corpus, without modifying core logic.
- When writing system prompts, use the prompt of prompts file in the docs folder as precise guidance. Leave dynamic prompts empty for now.