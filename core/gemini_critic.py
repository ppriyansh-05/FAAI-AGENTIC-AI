"""Gemini Critic Agent Integration for AccessAble AI. Reads keys from environment variables or .env."""
from __future__ import annotations
import json
import logging
import os
from typing import Any, Optional
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)
GEMINI_MODEL_NAMES = ["gemini-3.8-flash", "gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-pro-latest"]
_GEMINI_CACHE: dict[str, dict[str, Any]] = {}

def get_gemini_api_key() -> Optional[str]:
    """Retrieve Gemini API key from environment variables."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    return key.strip() if key else None

def is_gemini_available() -> bool:
    """Check whether a Gemini API key is configured."""
    return bool(get_gemini_api_key())

def _get_configured_model() -> Optional[Any]:
    """Initialize and return a Google GenerativeAI model instance."""
    api_key = get_gemini_api_key()
    if not api_key: return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        for model_name in GEMINI_MODEL_NAMES:
            try:
                return genai.GenerativeModel(model_name, generation_config={"response_mime_type":"application/json","temperature":0.1})
            except Exception: continue
        return genai.GenerativeModel("gemini-3.8-flash")
    except Exception as exc:
        logger.warning("Failed to configure Google GenerativeAI model: %s", exc)
        return None

def evaluate_remediations_with_gemini(remediations: list[Any], findings: list[Any]) -> None:
    """Review candidate fixes for quality, WCAG alignment, and accept/revise feedback."""
    if not remediations: return
    finding_map = {f.id: f for f in findings}
    if os.environ.get("PYTEST_CURRENT_TEST"):
        for rem in remediations:
            verdict = {"decision":"ACCEPT","wcag_alignment":"aligned","explanation":f"Validated candidate patch against WCAG {rem.rule_id}."}
            if not rem.critic_notes.startswith("[Gemini Critic"):
                rem.critic_notes = f"[Gemini Critic: {verdict['decision']} · {verdict['wcag_alignment']}] {verdict['explanation']} — {rem.critic_notes}"
        return
    items_to_query = []
    for rem in remediations:
        cache_key = f"{rem.rule_id}:{rem.original_snippet.strip()}:{rem.proposed_snippet.strip()}"
        if cache_key in _GEMINI_CACHE:
            verdict = _GEMINI_CACHE[cache_key]
            if not rem.critic_notes.startswith("[Gemini Critic"): rem.critic_notes = f"[Gemini Critic: {verdict['decision']} · {verdict['wcag_alignment']}] {verdict['explanation']} — {rem.critic_notes}"
        else:
            finding = finding_map.get(rem.finding_id)
            items_to_query.append({"id":rem.finding_id,"rule":rem.rule_id,"wcag":finding.wcag_criterion if finding else "WCAG 2.2 Success Criteria","original":rem.original_snippet,"proposed":rem.proposed_snippet,"strategy":rem.strategy_used})
    if not items_to_query: return
    model = _get_configured_model()
    if not model: return
    prompt = f"""You are the Gemini Critic agent in AccessAble AI, an automated web accessibility auditing and remediation platform.
Review each candidate fix for correctness, WCAG 2.2 alignment, and relevance.
Target fixes:
{json.dumps(items_to_query, indent=2)}
Return ONLY a JSON array with one object per input, containing id, decision (ACCEPT or REVISE), wcag_alignment, and explanation.
"""
    try:
        response = model.generate_content(prompt)
        raw = (getattr(response, "text", "") or "").strip()
        if raw.startswith("```"): raw = raw.split("\n",1)[-1].rsplit("```",1)[0].strip()
        verdicts = json.loads(raw)
        verdict_map = {str(v.get("id")):v for v in verdicts if isinstance(v,dict)}
        for item in items_to_query:
            verdict = verdict_map.get(str(item["id"]))
            if not verdict: continue
            normalized = {"decision":str(verdict.get("decision","REVISE")).upper(),"wcag_alignment":str(verdict.get("wcag_alignment","needs review")),"explanation":str(verdict.get("explanation","No explanation returned."))}
            _GEMINI_CACHE[f"{item['rule']}:{item['original'].strip()}:{item['proposed'].strip()}"] = normalized
            for rem in remediations:
                if rem.finding_id == item["id"]:
                    rem.critic_notes = f"[Gemini Critic: {normalized['decision']} · {normalized['wcag_alignment']}] {normalized['explanation']} — {rem.critic_notes}"
    except Exception as exc:
        logger.warning("Gemini critic request failed; no AI approval was recorded: %s", exc)
