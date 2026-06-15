from ic_agent.models.synthesizer import SynthesizerInput, SynthesizerOutput
from ic_agent.services.synthesizer_service import SynthesizerService
from tests.conftest import FakeStructuredChatModel

_MARKDOWN = """## Summary
Revenue declined due to pricing pressure.

## Key Findings
- Pricing was the dominant driver.

## Evidence
- P-aaaaaaaa: revenue trend was down.

## Recommendations
- Investigate pricing strategy in East China.

## Confidence
Moderate confidence based on available evidence.

## Remaining Unknowns
- Impact of competitor promotions is unclear.
"""


def test_run_returns_fake_output(sample_domain_config, sample_evidence_ledger):
    fixed_output = SynthesizerOutput(markdown=_MARKDOWN, confidence=0.6)
    chat_model = FakeStructuredChatModel({SynthesizerOutput: [fixed_output]})
    service = SynthesizerService(sample_domain_config, chat_model=chat_model)

    result = service.run(
        SynthesizerInput(
            query="Why did revenue decline in East China during Q1?",
            ledger=sample_evidence_ledger,
            decision_consultant_output=None,
            stop_reason="all_major_gaps_closed",
        )
    )

    assert result == fixed_output
    assert 0.0 <= result.confidence <= 1.0
    for header in (
        "## Summary",
        "## Key Findings",
        "## Evidence",
        "## Recommendations",
        "## Confidence",
        "## Remaining Unknowns",
    ):
        assert header in result.markdown
