"""Prompt templates. Kept short and focused so small local models do well."""

SYSTEM = (
    "You are a careful contract analyst. Answer only from the contract text provided. "
    "If information is not present, leave the field empty. Never invent facts. "
    "Reply with JSON only."
)

CLASSIFY = """Classify this contract into exactly one type from this list:
{types}

Contract opening text:
\"\"\"
{text}
\"\"\"
"""

ENTITIES = """Extract the parties (legal names and their role, e.g. "Provider", "Client"),
the governing law jurisdiction, and the effective date (YYYY-MM-DD) from this contract excerpt.

\"\"\"
{text}
\"\"\"
"""

CLAUSE_TYPE = """Which clause type best describes this contract section? Choose one of:
{types}
Use "other" if none fit.

Heading: {heading}
Text:
\"\"\"
{text}
\"\"\"
"""

RISK_REVIEW = """Review this {clause_type} clause from a {contract_type}.
Compared with market-standard terms, list at most 2 material risks for the party
receiving this contract. Only flag genuinely unusual or one-sided wording.
For each: severity (low|medium|high|critical), a one-sentence message
(e.g. "This indemnification clause is unusually broad"), and a one-sentence
negotiation suggestion. Return an empty list if the clause is standard.

Clause:
\"\"\"
{text}
\"\"\"
"""

SUMMARY = """Explain this contract in simple, plain {language} for a non-lawyer.
Write a short summary paragraph (max 120 words) and 4-7 key points covering:
who the parties are, what is being provided, money, how long it lasts and how it
renews or ends, and the most important risks.

Known facts (trust these):
{facts}

Contract text (may be truncated):
\"\"\"
{text}
\"\"\"
"""

COMPLIANCE = """Policy requirement: {requirement}

Does the contract text below satisfy this requirement?
Answer verdict = "pass", "fail" or "unclear", a one-sentence explanation, and quote
the most relevant sentence as evidence (empty if none).

Contract text:
\"\"\"
{text}
\"\"\"
"""

NEGOTIATE = """You are advising the party receiving this {contract_type}.
Given these identified issues:
{issues}

Write up to 5 concise, practical negotiation suggestions (one sentence each),
most important first, e.g. "Consider asking for a cap on liability equal to 12 months of fees."
"""

COMPARE = """Compare the contract clause with the standard template clause for "{clause_type}".
In one or two sentences, describe the material difference in meaning (not wording)
and whether it is less favourable than the template (true/false).

Template:
\"\"\"
{template}
\"\"\"

Contract:
\"\"\"
{contract}
\"\"\"
"""
