"""Explicit, limited OFFLINE SIMULATION. Not an AI or semantic safety assessment."""

import json
import re

from nyayasaathi.models import CASE_FIELDS, LLMRequest, LLMResponse
from nyayasaathi.retrieval import STATES, contains
from nyayasaathi.safety import assess_request


class SimulatedLLM:
    def generate(self, request: LLMRequest) -> LLMResponse:
        data = json.loads(request.messages[-1].content)
        text = data["message"]
        topic = assess_request(text).topic
        if topic == "unclear":
            topic = data["case"]["topic"]
        facts = []
        # General label parser, not canned case answers. See README for syntax.
        for name in CASE_FIELDS:
            match = re.search(r"(?<!\w)" + name + r"\s*:\s*([^;\n]+)", text, re.I)
            if match:
                value = match.group(1).strip()
                facts.append({"name": name, "value": None if value.casefold() == "unknown" else value,
                              "quote": match.group(0)})
        names = {f["name"] for f in facts}
        if "state" not in names:
            for state in STATES:
                if contains(text, state):
                    match = re.search(re.escape(state), text, re.I)
                    if match:
                        facts.append({"name": "state", "value": match.group(), "quote": match.group()})
                        break
        if "problem" not in names and topic in {"consumer", "rental_deposit"} and not data["case"]["has_problem"]:
            facts.append({"name": "problem", "value": text[:500], "quote": text[:500]})
        return LLMResponse(json.dumps({"topic": topic, "confidence": 0.9 if topic in {"consumer", "rental_deposit"} else 0.2,
                                      "risk_flags": [], "facts": facts}, ensure_ascii=False), "offline-simulation")
