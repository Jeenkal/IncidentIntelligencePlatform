# # # 
# # import json
# # import logging
# # import os
# # import re
# # from typing import Any

# # from app.agents.state import InvestigationState
# # from app.database.connection import SessionLocal
# # from app.services.llm_service import generate_json
# # from app.services.reranker import rerank_documents
# # from app.services.retrieval import hybrid_search

# # logger = logging.getLogger(__name__)

# # # Chunks scoring below this are dropped. Calibrate from the logged scores.
# # MIN_RERANK_SCORE = float(os.getenv("MIN_RERANK_SCORE", "0.0"))
# # MAX_EVIDENCE = 5


# # # --------------------------------------------------------------------------
# # # Helpers
# # # --------------------------------------------------------------------------

# # def _prompt_evidence(evidence: list[dict]) -> str:
# #     """Send the LLM only what it needs (smaller prompt, fewer tokens)."""
# #     slim = [
# #         {
# #             "id": e["chunk_id"],
# #             "title": e.get("title"),
# #             "content": e.get("content"),
# #         }
# #         for e in evidence
# #     ]
# #     return json.dumps(slim, indent=2)


# # def _norm(text: Any) -> str:
# #     return re.sub(r"\s+", " ", str(text or "")).strip().lower()


# # _STEP_FILLER = {
# #     "check", "verify", "review", "inspect", "perform", "detailed",
# #     "ensure", "confirm", "examine", "test", "tests", "testing",
# #     "the", "and", "for", "with", "between", "current", "that", "this",
# #     "from", "your", "are", "all",
# # }


# # def _step_tokens(text: Any) -> set:
# #     return {
# #         w for w in re.findall(r"[a-z0-9]+", str(text).lower())
# #         if len(w) >= 3 and w not in _STEP_FILLER
# #     }


# # def _dedupe_steps(steps: list, threshold: float = 0.7) -> list:
# #     """Drop exact and near-duplicate steps, keeping the first occurrence.

# #     "Review PostgreSQL server logs for connection errors" and
# #     "Check the PostgreSQL server logs for connection errors" count as
# #     the same step.
# #     """
# #     kept: list[str] = []
# #     kept_norm: set[str] = set()
# #     kept_tokens: list[set] = []

# #     for step in steps:
# #         if not isinstance(step, str) or not step.strip():
# #             continue

# #         norm = _norm(step)
# #         tokens = _step_tokens(step)

# #         duplicate = norm in kept_norm
# #         if not duplicate and len(tokens) >= 2:
# #             for other in kept_tokens:
# #                 if len(other) < 2:
# #                     continue
# #                 overlap = len(tokens & other) / min(len(tokens), len(other))
# #                 if overlap >= threshold:
# #                     duplicate = True
# #                     break

# #         if duplicate:
# #             continue

# #         kept.append(step.strip())
# #         kept_norm.add(norm)
# #         kept_tokens.append(tokens)

# #     return kept


# # def _clean_ids(raw: Any, valid_ids: set) -> list:
# #     """Keep only IDs that exist in the real evidence.

# #     Small models sometimes return IDs as strings ("3"), so coerce first.
# #     """
# #     if not isinstance(raw, list):
# #         return []

# #     cleaned = []
# #     for value in raw:
# #         try:
# #             value = int(value)
# #         except (TypeError, ValueError):
# #             continue
# #         if value in valid_ids and value not in cleaned:
# #             cleaned.append(value)
# #     return cleaned


# # def _pick_root_cause(hypotheses: list[dict], sufficient: bool):
# #     if not sufficient:
# #         return None

# #     supported = [
# #         h for h in hypotheses
# #         if h.get("verification_status") == "supported"
# #         and h.get("supporting_evidence_ids")
# #     ]
# #     if not supported:
# #         return None

# #     order = {"high": 0, "medium": 1, "low": 2}
# #     best = sorted(
# #         supported,
# #         key=lambda h: order.get(h.get("confidence"), 3),
# #     )[0]

# #     return {
# #         "cause": best.get("cause"),
# #         "explanation": best.get("reasoning") or best.get("explanation"),
# #         "supporting_evidence_ids": best["supporting_evidence_ids"],
# #         "note": (
# #             "Supported by reference material only. "
# #             "Not confirmed against this incident's logs or metrics."
# #         ),
# #     }


# # # --------------------------------------------------------------------------
# # # Nodes
# # # --------------------------------------------------------------------------

# # def retrieve_evidence(state: InvestigationState) -> dict[str, Any]:
# #     db = SessionLocal()

# #     try:
# #         original_query = f"{state['title']} {state['description']}"

# #         current_query = state.get("current_query", original_query)

# #         results = hybrid_search(
# #             db=db,
# #             query=current_query,
# #             domain=state["domain"],
# #             top_k=12,
# #         )

# #         candidates = [
# #             {
# #                 "chunk_id": item["id"],
# #                 "document_id": item["document_id"],
# #                 "title": item["title"],
# #                 "content": item["content"],
# #                 "source_url": item["source_url"],
# #                 "retrieval_score": float(item["score"]),
# #             }
# #             for item in results
# #         ]

# #         ranked = rerank_documents(
# #             query=current_query,
# #             documents=candidates,
# #             top_k=MAX_EVIDENCE,
# #         )

# #         # Log scores so the threshold can be calibrated from real data.
# #         logger.info(
# #             "Rerank scores for incident %s: %s",
# #             state.get("incident_id"),
# #             [round(r["rerank_score"], 2) for r in ranked],
# #         )

# #         ranked = [
# #             r for r in ranked
# #             if r["rerank_score"] >= MIN_RERANK_SCORE
# #         ]

# #         # Merge with evidence from earlier attempts instead of replacing it.
# #         merged = {e["chunk_id"]: e for e in state.get("evidence", [])}
# #         for item in ranked:
# #             old = merged.get(item["chunk_id"])
# #             if old is None or item["rerank_score"] > old["rerank_score"]:
# #                 merged[item["chunk_id"]] = item

# #         evidence = sorted(
# #             merged.values(),
# #             key=lambda e: e["rerank_score"],
# #             reverse=True,
# #         )[:MAX_EVIDENCE]

# #         return {
# #             "evidence": evidence,
# #             "current_query": current_query,
# #         }

# #     finally:
# #         db.close()


# # def generate_hypotheses(
# #     state: InvestigationState,
# # ) -> dict[str, Any]:
# #     evidence = state.get("evidence", [])

# #     if not evidence:
# #         return {
# #             "hypotheses": [],
# #             "status": "insufficient_evidence",
# #         }

# #     prompt = f"""
# # Investigate the following technical incident.

# # INCIDENT:
# # {state['title']}

# # DESCRIPTION:
# # {state['description']}

# # DOMAIN:
# # {state['domain']}

# # RETRIEVED REFERENCE MATERIAL:
# # {_prompt_evidence(evidence)}

# # Identify up to three plausible root-cause hypotheses.

# # Requirements:
# # - Base hypotheses on the supplied reference material.
# # - Do not claim a hypothesis is confirmed merely because it is plausible.
# # - Use the "id" field of the reference material for evidence IDs.
# # - Identify missing information.
# # - Use incident-specific clues from the description (for example,
# #   "after a deployment", error codes, affected components), not only the
# #   reference material.
# # - next_checks must be concrete and actionable for THIS incident. Include
# #   checks drawn from the description even if the reference material does
# #   not list them.
# # - Each hypothesis must be tied to a specific symptom in the incident
# #   description. Do NOT turn every item of a troubleshooting checklist
# #   into a hypothesis. If the only link between the reference material and
# #   the incident is generic (for example, both mention "connection"),
# #   return no hypotheses.
# # - If the reference material describes a different kind of problem than
# #   the incident symptoms, return no hypotheses and say so in
# #   evidence_gaps.

# # Return JSON with this structure:
# # {{
# #   "hypotheses": [
# #     {{
# #       "cause": "Potential root cause",
# #       "explanation": "Why it may explain the incident",
# #       "supporting_evidence_ids": [1],
# #       "contradicting_evidence_ids": [],
# #       "confidence": "low",
# #       "verification_status": "unverified",
# #       "next_checks": ["Check the application logs"]
# #     }}
# #   ],
# #   "evidence_gaps": ["Missing diagnostic information"]
# # }}

# # Confidence must be low, medium, or high.
# # Use only evidence IDs present in the supplied reference material.
# # """

# #     result = generate_json(prompt)

# #     valid_ids = {item["chunk_id"] for item in evidence}

# #     hypotheses = result.get("hypotheses", [])

# #     if not isinstance(hypotheses, list):
# #         hypotheses = []

# #     validated_hypotheses = []

# #     for hypothesis in hypotheses[:3]:
# #         if not isinstance(hypothesis, dict):
# #             continue

# #         # Prevent the model from citing nonexistent evidence.
# #         hypothesis["supporting_evidence_ids"] = _clean_ids(
# #             hypothesis.get("supporting_evidence_ids"), valid_ids
# #         )
# #         hypothesis["contradicting_evidence_ids"] = _clean_ids(
# #             hypothesis.get("contradicting_evidence_ids"), valid_ids
# #         )

# #         if hypothesis.get("confidence") not in {"low", "medium", "high"}:
# #             hypothesis["confidence"] = "low"

# #         if not isinstance(hypothesis.get("next_checks"), list):
# #             hypothesis["next_checks"] = []

# #         # A generated hypothesis is not automatically verified.
# #         hypothesis["verification_status"] = "unverified"

# #         validated_hypotheses.append(hypothesis)

# #     return {
# #         "hypotheses": validated_hypotheses,
# #         "status": "verification_pending",
# #     }


# # def verify_hypotheses(
# #     state: InvestigationState,
# # ) -> dict[str, Any]:
# #     evidence = state.get("evidence", [])
# #     hypotheses = state.get("hypotheses", [])

# #     if not evidence or not hypotheses:
# #         report = {
# #             "incident_summary": state["title"],
# #             "domain": state["domain"],
# #             "status": "insufficient_evidence",
# #             "root_cause": None,
# #             "hypotheses": hypotheses,
# #             "evidence": evidence,
# #             "limitations": [
# #                 "No relevant reference material was found for this "
# #                 f"incident in the '{state['domain']}' knowledge base."
# #             ],
# #             "recommended_next_steps": [
# #                 "Collect logs and metrics for the affected service.",
# #                 "Check whether the incident was filed under the right "
# #                 "domain.",
# #             ],
# #         }

# #         return {
# #             "verification": {"sufficient_evidence": False},
# #             "report": report,
# #             "status": "insufficient_evidence",
# #         }

# #     prompt = f"""
# # Review the incident hypotheses against the retrieved reference material.

# # Incident:
# # {state['title']}

# # Description:
# # {state['description']}

# # Hypotheses:
# # {json.dumps(hypotheses, indent=2)}

# # Reference material:
# # {_prompt_evidence(evidence)}

# # For each hypothesis:
# # - Assess whether its supporting evidence actually supports it.
# # - Identify contradictions.
# # - Do not infer that missing evidence proves a hypothesis.
# # - Distinguish a possible explanation from a confirmed finding.
# # - Keep the hypothesis "cause" text exactly as given.
# # - List an evidence ID in supporting_evidence_ids ONLY if that material
# #   states something specific that matches the incident's symptoms. A
# #   generic checklist item that merely could apply is NOT support; use []
# #   in that case and say so in the reasoning.

# # Also judge whether the reference material is about the same kind of
# # problem as the incident symptoms. Use "off_topic" if it describes a
# # different failure type, or lists generic checks for a component that the
# # incident gives no sign of (e.g. database connection docs for a gateway
# # 502 with no database symptoms, credentials or firewall checks with no
# # sign of auth or network errors). Use "partial" if only some of it applies.

# # Return JSON:
# # {{
# #   "sufficient_evidence": false,
# #   "evidence_relevance": "relevant",
# #   "hypotheses": [
# #     {{
# #       "cause": "same text as input",
# #       "verification_status": "supported",
# #       "reasoning": "Explanation citing evidence IDs",
# #       "supporting_evidence_ids": [],
# #       "contradicting_evidence_ids": [],
# #       "next_checks": []
# #     }}
# #   ],
# #   "limitations": ["What remains unknown"],
# #   "recommended_next_steps": ["Next diagnostic action"]
# # }}

# # verification_status: supported, contradicted, or inconclusive.
# # evidence_relevance: relevant, partial, or off_topic.
# # Set sufficient_evidence to true only if the material adequately supports
# # the finding. A plausible explanation alone is not sufficient.
# # """

# #     result = generate_json(prompt)

# #     valid_ids = {item["chunk_id"] for item in evidence}
# #     allowed_statuses = {"supported", "contradicted", "inconclusive"}

# #     verified = result.get("hypotheses", [])
# #     if not isinstance(verified, list):
# #         verified = []
# #     verified = [v for v in verified if isinstance(v, dict)]

# #     by_cause = {_norm(v.get("cause")): v for v in verified}

# #     merged_hypotheses = []

# #     for index, original in enumerate(hypotheses):
# #         review = by_cause.get(_norm(original.get("cause")))
# #         if review is None and index < len(verified):
# #             review = verified[index]

# #         # Start from the original so explanation, confidence and
# #         # next_checks survive verification.
# #         merged = dict(original)

# #         if review:
# #             status = review.get("verification_status")
# #             merged["verification_status"] = (
# #                 status if status in allowed_statuses else "inconclusive"
# #             )
# #             merged["reasoning"] = review.get("reasoning", "")

# #             for key in (
# #                 "supporting_evidence_ids",
# #                 "contradicting_evidence_ids",
# #             ):
# #                 merged[key] = _clean_ids(review.get(key), valid_ids)

# #             new_checks = review.get("next_checks")
# #             if isinstance(new_checks, list) and new_checks:
# #                 merged["next_checks"] = new_checks
# #         else:
# #             merged["verification_status"] = "inconclusive"
# #             merged["reasoning"] = "Not reviewed by the verification step."

# #         merged_hypotheses.append(merged)

# #     limitations = result.get("limitations", [])
# #     next_steps = result.get("recommended_next_steps", [])

# #     if not isinstance(limitations, list):
# #         limitations = []
# #     if not isinstance(next_steps, list):
# #         next_steps = []

# #     relevance = result.get("evidence_relevance", "partial")
# #     if relevance not in {"relevant", "partial", "off_topic"}:
# #         relevance = "partial"

# #     # Off-topic material cannot support anything, whatever the model says.
# #     if relevance == "off_topic":
# #         for h in merged_hypotheses:
# #             h["supporting_evidence_ids"] = []
# #             h["verification_status"] = "inconclusive"

# #     sufficient = (
# #         result.get("sufficient_evidence") is True
# #         and relevance != "off_topic"
# #         and any(
# #             h["verification_status"] == "supported"
# #             and h.get("supporting_evidence_ids")
# #             for h in merged_hypotheses
# #         )
# #     )

# #     # Always state what was searched, so a misfiled incident is obvious.
# #     doc_count = len({e.get("document_id") for e in evidence})
# #     limitations.insert(
# #         0,
# #         f"Only the '{state['domain']}' knowledge base was searched "
# #         f"({doc_count} reference document(s) retrieved). If this incident "
# #         "was filed under the wrong domain, re-file it and investigate "
# #         "again.",
# #     )

# #     if relevance == "off_topic":
# #         limitations.insert(
# #             0,
# #             "The retrieved reference material does not match this "
# #             "incident's symptoms. Check the incident domain and the "
# #             "knowledge base contents.",
# #         )

# #     # Surface hypothesis-level checks in the overall steps,
# #     # removing exact and near-duplicates.
# #     all_steps = list(next_steps)
# #     for h in merged_hypotheses:
# #         all_steps.extend(
# #             c for c in h.get("next_checks", []) if isinstance(c, str)
# #         )
# #     next_steps = _dedupe_steps(all_steps)

# #     status = "investigated" if sufficient else "insufficient_evidence"

# #     report = {
# #         "incident_summary": state["title"],
# #         "domain": state["domain"],
# #         "status": status,
# #         "root_cause": _pick_root_cause(merged_hypotheses, sufficient),
# #         "hypotheses": merged_hypotheses,
# #         "evidence": evidence,
# #         "limitations": limitations,
# #         "recommended_next_steps": next_steps,
# #     }

# #     return {
# #         "verification": {"sufficient_evidence": sufficient},
# #         "hypotheses": merged_hypotheses,
# #         "report": report,
# #         "status": "completed" if sufficient else "insufficient_evidence",
# #     }


# # def refine_investigation_query(
# #     state: InvestigationState,
# # ) -> dict[str, Any]:
# #     retry_count = state.get("retry_count", 0)

# #     prompt = f"""
# # You are refining a technical incident investigation search query.

# # Incident title:
# # {state['title']}

# # Incident description:
# # {state['description']}

# # Domain:
# # {state['domain']}

# # Current query:
# # {state.get('current_query', state['description'])}

# # Previous reference material:
# # {_prompt_evidence(state.get('evidence', []))}

# # Create a more specific search query that may retrieve
# # additional relevant technical evidence.

# # Focus on technical error messages, likely components,
# # relevant symptoms, and diagnostic terminology.

# # Do not assume a root cause has been confirmed.

# # Return JSON:
# # {{
# #   "query": "Refined search query"
# # }}
# # """

# #     result = generate_json(prompt)

# #     refined_query = result.get("query", "")

# #     if not isinstance(refined_query, str):
# #         refined_query = ""

# #     refined_query = refined_query.strip()

# #     if len(refined_query) < 5:
# #         refined_query = (
# #             f"{state['title']} {state['description']} "
# #             f"{state['domain']} troubleshooting"
# #         )

# #     return {
# #         "current_query": refined_query,
# #         "retry_count": retry_count + 1,
# #     }


# # # --------------------------------------------------------------------------
# # # Routing
# # # --------------------------------------------------------------------------

# # def should_retry_after_retrieval(
# #     state: InvestigationState,
# # ) -> str:
# #     evidence = state.get("evidence", [])
# #     retry_count = state.get("retry_count", 0)
# #     max_retries = state.get("max_retries", 1)

# #     # Evidence was retrieved successfully.
# #     if evidence:
# #         return "generate_hypotheses"

# #     # Retry retrieval if attempts remain.
# #     if retry_count < max_retries:
# #         return "refine_query"

# #     # No evidence after retries.
# #     return "verify_hypotheses"


# # def should_retry_after_verification(
# #     state: InvestigationState,
# # ) -> str:
# #     verification = state.get("verification", {})
# #     retry_count = state.get("retry_count", 0)
# #     max_retries = state.get("max_retries", 1)

# #     # Stop when the verification node reports sufficient evidence.
# #     if verification.get("sufficient_evidence") is True:
# #         return "finish"

# #     # Retry if attempts remain.
# #     if retry_count < max_retries:
# #         return "refine_query"

# #     return "finish"
# import json
# import logging
# import os
# import re
# from typing import Any

# from app.agents.state import InvestigationState
# from app.database.connection import SessionLocal
# from app.services.llm_service import generate_json
# from app.services.reranker import rerank_documents
# from app.services.retrieval import hybrid_search

# logger = logging.getLogger(__name__)

# # Chunks scoring below this are dropped. Calibrate from the logged scores.
# MIN_RERANK_SCORE = float(os.getenv("MIN_RERANK_SCORE", "0.0"))
# MAX_EVIDENCE = 5


# # --------------------------------------------------------------------------
# # Helpers
# # --------------------------------------------------------------------------

# def _prompt_evidence(evidence: list[dict]) -> str:
#     """Send the LLM only what it needs (smaller prompt, fewer tokens)."""
#     slim = [
#         {
#             "id": e["chunk_id"],
#             "title": e.get("title"),
#             "content": e.get("content"),
#         }
#         for e in evidence
#     ]
#     return json.dumps(slim, indent=2)


# def _norm(text: Any) -> str:
#     return re.sub(r"\s+", " ", str(text or "")).strip().lower()


# _STEP_FILLER = {
#     "check", "verify", "review", "inspect", "perform", "detailed",
#     "ensure", "confirm", "examine", "test", "tests", "testing",
#     "the", "and", "for", "with", "between", "current", "that", "this",
#     "from", "your", "are", "all",
# }


# def _step_tokens(text: Any) -> set:
#     return {
#         w for w in re.findall(r"[a-z0-9]+", str(text).lower())
#         if len(w) >= 3 and w not in _STEP_FILLER
#     }


# def _dedupe_steps(steps: list, threshold: float = 0.7) -> list:
#     """Drop exact and near-duplicate steps, keeping the first occurrence.

#     "Review PostgreSQL server logs for connection errors" and
#     "Check the PostgreSQL server logs for connection errors" count as
#     the same step.
#     """
#     kept: list[str] = []
#     kept_norm: set[str] = set()
#     kept_tokens: list[set] = []

#     for step in steps:
#         if not isinstance(step, str) or not step.strip():
#             continue

#         norm = _norm(step)
#         tokens = _step_tokens(step)

#         duplicate = norm in kept_norm
#         if not duplicate and len(tokens) >= 2:
#             for other in kept_tokens:
#                 if len(other) < 2:
#                     continue
#                 overlap = len(tokens & other) / min(len(tokens), len(other))
#                 if overlap >= threshold:
#                     duplicate = True
#                     break

#         if duplicate:
#             continue

#         kept.append(step.strip())
#         kept_norm.add(norm)
#         kept_tokens.append(tokens)

#     return kept


# def _clean_ids(raw: Any, valid_ids: set) -> list:
#     """Keep only IDs that exist in the real evidence.

#     Small models sometimes return IDs as strings ("3"), so coerce first.
#     """
#     if not isinstance(raw, list):
#         return []

#     cleaned = []
#     for value in raw:
#         try:
#             value = int(value)
#         except (TypeError, ValueError):
#             continue
#         if value in valid_ids and value not in cleaned:
#             cleaned.append(value)
#     return cleaned


# def _pick_root_cause(hypotheses: list[dict], sufficient: bool):
#     if not sufficient:
#         return None

#     supported = [
#         h for h in hypotheses
#         if h.get("verification_status") == "supported"
#         and h.get("supporting_evidence_ids")
#     ]
#     if not supported:
#         return None

#     order = {"high": 0, "medium": 1, "low": 2}
#     best = sorted(
#         supported,
#         key=lambda h: order.get(h.get("confidence"), 3),
#     )[0]

#     return {
#         "cause": best.get("cause"),
#         "explanation": best.get("reasoning") or best.get("explanation"),
#         "supporting_evidence_ids": best["supporting_evidence_ids"],
#         "note": (
#             "Supported by reference material only. "
#             "Not confirmed against this incident's logs or metrics."
#         ),
#     }


# # --------------------------------------------------------------------------
# # Nodes
# # --------------------------------------------------------------------------

# def retrieve_evidence(state: InvestigationState) -> dict[str, Any]:
#     db = SessionLocal()

#     try:
#         original_query = f"{state['title']} {state['description']}"

#         current_query = state.get("current_query", original_query)

#         results = hybrid_search(
#             db=db,
#             query=current_query,
#             domain=state["domain"],
#             top_k=12,
#         )

#         candidates = [
#             {
#                 "chunk_id": item["id"],
#                 "document_id": item["document_id"],
#                 "title": item["title"],
#                 "content": item["content"],
#                 "source_url": item["source_url"],
#                 "retrieval_score": float(item["score"]),
#             }
#             for item in results
#         ]

#         ranked = rerank_documents(
#             query=current_query,
#             documents=candidates,
#             top_k=MAX_EVIDENCE,
#         )

#         # Log scores so the threshold can be calibrated from real data.
#         logger.info(
#             "Rerank scores for incident %s: %s",
#             state.get("incident_id"),
#             [round(r["rerank_score"], 2) for r in ranked],
#         )

#         ranked = [
#             r for r in ranked
#             if r["rerank_score"] >= MIN_RERANK_SCORE
#         ]

#         # Merge with evidence from earlier attempts instead of replacing it.
#         merged = {e["chunk_id"]: e for e in state.get("evidence", [])}
#         for item in ranked:
#             old = merged.get(item["chunk_id"])
#             if old is None or item["rerank_score"] > old["rerank_score"]:
#                 merged[item["chunk_id"]] = item

#         evidence = sorted(
#             merged.values(),
#             key=lambda e: e["rerank_score"],
#             reverse=True,
#         )[:MAX_EVIDENCE]

#         return {
#             "evidence": evidence,
#             "current_query": current_query,
#         }

#     finally:
#         db.close()


# def generate_hypotheses(
#     state: InvestigationState,
# ) -> dict[str, Any]:
#     evidence = state.get("evidence", [])

#     if not evidence:
#         return {
#             "hypotheses": [],
#             "status": "insufficient_evidence",
#         }

#     prompt = f"""
# Investigate the following technical incident.

# INCIDENT:
# {state['title']}

# DESCRIPTION:
# {state['description']}

# DOMAIN:
# {state['domain']}

# RETRIEVED REFERENCE MATERIAL:
# {_prompt_evidence(evidence)}

# Identify up to three plausible root-cause hypotheses.

# Requirements:
# - Base hypotheses on the supplied reference material.
# - Do not claim a hypothesis is confirmed merely because it is plausible.
# - Use the "id" field of the reference material for evidence IDs.
# - Identify missing information.
# - Use incident-specific clues from the description (for example,
#   "after a deployment", error codes, affected components), not only the
#   reference material.
# - next_checks must be concrete and actionable for THIS incident. Include
#   checks drawn from the description even if the reference material does
#   not list them.
# - Each hypothesis must be tied to a specific symptom in the incident
#   description. Do NOT turn every item of a troubleshooting checklist
#   into a hypothesis. If the only link between the reference material and
#   the incident is generic (for example, both mention "connection"),
#   return no hypotheses.
# - If the reference material describes a different kind of problem than
#   the incident symptoms, return no hypotheses and say so in
#   evidence_gaps.

# Return JSON with this structure:
# {{
#   "hypotheses": [
#     {{
#       "cause": "Potential root cause",
#       "explanation": "Why it may explain the incident",
#       "supporting_evidence_ids": [1],
#       "contradicting_evidence_ids": [],
#       "confidence": "low",
#       "verification_status": "unverified",
#       "next_checks": ["Check the application logs"]
#     }}
#   ],
#   "evidence_gaps": ["Missing diagnostic information"]
# }}

# Confidence must be low, medium, or high.
# Use only evidence IDs present in the supplied reference material.
# """

#     result = generate_json(prompt)

#     valid_ids = {item["chunk_id"] for item in evidence}

#     hypotheses = result.get("hypotheses", [])

#     if not isinstance(hypotheses, list):
#         hypotheses = []

#     validated_hypotheses = []

#     for hypothesis in hypotheses[:3]:
#         if not isinstance(hypothesis, dict):
#             continue

#         # Prevent the model from citing nonexistent evidence.
#         hypothesis["supporting_evidence_ids"] = _clean_ids(
#             hypothesis.get("supporting_evidence_ids"), valid_ids
#         )
#         hypothesis["contradicting_evidence_ids"] = _clean_ids(
#             hypothesis.get("contradicting_evidence_ids"), valid_ids
#         )

#         if hypothesis.get("confidence") not in {"low", "medium", "high"}:
#             hypothesis["confidence"] = "low"

#         if not isinstance(hypothesis.get("next_checks"), list):
#             hypothesis["next_checks"] = []

#         # A generated hypothesis is not automatically verified.
#         hypothesis["verification_status"] = "unverified"

#         validated_hypotheses.append(hypothesis)

#     return {
#         "hypotheses": validated_hypotheses,
#         "status": "verification_pending",
#     }


# def verify_hypotheses(
#     state: InvestigationState,
# ) -> dict[str, Any]:
#     evidence = state.get("evidence", [])
#     hypotheses = state.get("hypotheses", [])

#     if not evidence or not hypotheses:
#         report = {
#             "incident_summary": state["title"],
#             "domain": state["domain"],
#             "status": "insufficient_evidence",
#             "root_cause": None,
#             "hypotheses": hypotheses,
#             "evidence": evidence,
#             "limitations": [
#                 "No relevant reference material was found for this "
#                 f"incident in the '{state['domain']}' knowledge base."
#             ],
#             "recommended_next_steps": [
#                 "Collect logs and metrics for the affected service.",
#                 "Check whether the incident was filed under the right "
#                 "domain.",
#             ],
#         }

#         return {
#             "verification": {"sufficient_evidence": False},
#             "report": report,
#             "status": "insufficient_evidence",
#         }

#     prompt = f"""
# Review the incident hypotheses against the retrieved reference material.

# Incident:
# {state['title']}

# Description:
# {state['description']}

# Hypotheses:
# {json.dumps(hypotheses, indent=2)}

# Reference material:
# {_prompt_evidence(evidence)}

# For each hypothesis:
# - Assess whether its supporting evidence actually supports it.
# - Identify contradictions.
# - Do not infer that missing evidence proves a hypothesis.
# - Distinguish a possible explanation from a confirmed finding.
# - Keep the hypothesis "cause" text exactly as given.
# - List an evidence ID in supporting_evidence_ids ONLY if that material
#   states something specific that matches the incident's symptoms. A
#   generic checklist item that merely could apply is NOT support; use []
#   in that case and say so in the reasoning.

# Also judge whether the reference material is about the same kind of
# problem as the incident symptoms. Use "off_topic" if it describes a
# different failure type, or lists generic checks for a component that the
# incident gives no sign of (e.g. database connection docs for a gateway
# 502 with no database symptoms, credentials or firewall checks with no
# sign of auth or network errors). Use "partial" if only some of it applies.

# Return JSON:
# {{
#   "sufficient_evidence": false,
#   "evidence_relevance": "relevant",
#   "hypotheses": [
#     {{
#       "cause": "same text as input",
#       "verification_status": "supported",
#       "reasoning": "Explanation citing evidence IDs",
#       "supporting_evidence_ids": [],
#       "contradicting_evidence_ids": [],
#       "next_checks": []
#     }}
#   ],
#   "limitations": ["What remains unknown"],
#   "recommended_next_steps": ["Next diagnostic action"]
# }}

# verification_status: supported, contradicted, or inconclusive.
# evidence_relevance: relevant, partial, or off_topic.
# Set sufficient_evidence to true only if the material adequately supports
# the finding. A plausible explanation alone is not sufficient.
# """

#     result = generate_json(prompt)

#     valid_ids = {item["chunk_id"] for item in evidence}
#     allowed_statuses = {"supported", "contradicted", "inconclusive"}

#     verified = result.get("hypotheses", [])
#     if not isinstance(verified, list):
#         verified = []
#     verified = [v for v in verified if isinstance(v, dict)]

#     by_cause = {_norm(v.get("cause")): v for v in verified}

#     merged_hypotheses = []

#     for index, original in enumerate(hypotheses):
#         review = by_cause.get(_norm(original.get("cause")))
#         if review is None and index < len(verified):
#             review = verified[index]

#         # Start from the original so explanation, confidence and
#         # next_checks survive verification.
#         merged = dict(original)

#         if review:
#             status = review.get("verification_status")
#             merged["verification_status"] = (
#                 status if status in allowed_statuses else "inconclusive"
#             )
#             merged["reasoning"] = review.get("reasoning", "")

#             for key in (
#                 "supporting_evidence_ids",
#                 "contradicting_evidence_ids",
#             ):
#                 merged[key] = _clean_ids(review.get(key), valid_ids)

#             new_checks = review.get("next_checks")
#             if isinstance(new_checks, list) and new_checks:
#                 merged["next_checks"] = new_checks
#         else:
#             merged["verification_status"] = "inconclusive"
#             merged["reasoning"] = "Not reviewed by the verification step."

#         merged_hypotheses.append(merged)

#     limitations = result.get("limitations", [])
#     next_steps = result.get("recommended_next_steps", [])

#     if not isinstance(limitations, list):
#         limitations = []
#     if not isinstance(next_steps, list):
#         next_steps = []

#     relevance = result.get("evidence_relevance", "partial")
#     if relevance not in {"relevant", "partial", "off_topic"}:
#         relevance = "partial"

#     # Off-topic material cannot support anything, whatever the model says.
#     if relevance == "off_topic":
#         for h in merged_hypotheses:
#             h["verification_status"] = "inconclusive"

#     # Material that is only partly relevant may be related to a hypothesis
#     # but cannot back it unless the hypothesis was actually supported.
#     # Keep the link, but label it honestly.
#     if relevance != "relevant":
#         for h in merged_hypotheses:
#             h["related_evidence_ids"] = []
#             if h.get("verification_status") != "supported":
#                 h["related_evidence_ids"] = h.get(
#                     "supporting_evidence_ids", []
#                 )
#                 h["supporting_evidence_ids"] = []

#     sufficient = (
#         result.get("sufficient_evidence") is True
#         and relevance != "off_topic"
#         and any(
#             h["verification_status"] == "supported"
#             and h.get("supporting_evidence_ids")
#             for h in merged_hypotheses
#         )
#     )

#     # Always state what was searched, so a misfiled incident is obvious.
#     doc_count = len({e.get("document_id") for e in evidence})
#     limitations.insert(
#         0,
#         f"Only the '{state['domain']}' knowledge base was searched "
#         f"({doc_count} reference document(s) retrieved). If this incident "
#         "was filed under the wrong domain, re-file it and investigate "
#         "again.",
#     )

#     if relevance == "off_topic":
#         limitations.insert(
#             0,
#             "The retrieved reference material does not match this "
#             "incident's symptoms. Check the incident domain and the "
#             "knowledge base contents.",
#         )

#     # Surface hypothesis-level checks in the overall steps,
#     # removing exact and near-duplicates.
#     all_steps = list(next_steps)
#     for h in merged_hypotheses:
#         all_steps.extend(
#             c for c in h.get("next_checks", []) if isinstance(c, str)
#         )
#     next_steps = _dedupe_steps(all_steps)

#     status = "investigated" if sufficient else "insufficient_evidence"

#     report = {
#         "incident_summary": state["title"],
#         "domain": state["domain"],
#         "status": status,
#         "root_cause": _pick_root_cause(merged_hypotheses, sufficient),
#         "hypotheses": merged_hypotheses,
#         "evidence": evidence,
#         "limitations": limitations,
#         "recommended_next_steps": next_steps,
#     }

#     return {
#         "verification": {"sufficient_evidence": sufficient},
#         "hypotheses": merged_hypotheses,
#         "report": report,
#         "status": "completed" if sufficient else "insufficient_evidence",
#     }


# def refine_investigation_query(
#     state: InvestigationState,
# ) -> dict[str, Any]:
#     retry_count = state.get("retry_count", 0)

#     prompt = f"""
# You are refining a technical incident investigation search query.

# Incident title:
# {state['title']}

# Incident description:
# {state['description']}

# Domain:
# {state['domain']}

# Current query:
# {state.get('current_query', state['description'])}

# Previous reference material:
# {_prompt_evidence(state.get('evidence', []))}

# Create a more specific search query that may retrieve
# additional relevant technical evidence.

# Focus on technical error messages, likely components,
# relevant symptoms, and diagnostic terminology.

# Do not assume a root cause has been confirmed.

# Return JSON:
# {{
#   "query": "Refined search query"
# }}
# """

#     result = generate_json(prompt)

#     refined_query = result.get("query", "")

#     if not isinstance(refined_query, str):
#         refined_query = ""

#     refined_query = refined_query.strip()

#     if len(refined_query) < 5:
#         refined_query = (
#             f"{state['title']} {state['description']} "
#             f"{state['domain']} troubleshooting"
#         )

#     return {
#         "current_query": refined_query,
#         "retry_count": retry_count + 1,
#     }


# # --------------------------------------------------------------------------
# # Routing
# # --------------------------------------------------------------------------

# def should_retry_after_retrieval(
#     state: InvestigationState,
# ) -> str:
#     evidence = state.get("evidence", [])
#     retry_count = state.get("retry_count", 0)
#     max_retries = state.get("max_retries", 1)

#     # Evidence was retrieved successfully.
#     if evidence:
#         return "generate_hypotheses"

#     # Retry retrieval if attempts remain.
#     if retry_count < max_retries:
#         return "refine_query"

#     # No evidence after retries.
#     return "verify_hypotheses"


# def should_retry_after_verification(
#     state: InvestigationState,
# ) -> str:
#     verification = state.get("verification", {})
#     retry_count = state.get("retry_count", 0)
#     max_retries = state.get("max_retries", 1)

#     # Stop when the verification node reports sufficient evidence.
#     if verification.get("sufficient_evidence") is True:
#         return "finish"

#     # Retry if attempts remain.
#     if retry_count < max_retries:
#         return "refine_query"

#     return "finish"
import json
import logging
import os
import re
from typing import Any

from app.agents.state import InvestigationState
from app.database.connection import SessionLocal
from app.services.llm_service import generate_json
from app.services.reranker import rerank_documents
from app.services.retrieval import hybrid_search

logger = logging.getLogger(__name__)

# Chunks scoring below this are dropped. Calibrate from the logged scores.
MIN_RERANK_SCORE = float(os.getenv("MIN_RERANK_SCORE", "0.0"))
MAX_EVIDENCE = 5


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _prompt_evidence(evidence: list[dict]) -> str:
    """Send the LLM only what it needs (smaller prompt, fewer tokens)."""
    slim = [
        {
            "id": e["chunk_id"],
            "title": e.get("title"),
            "content": e.get("content"),
        }
        for e in evidence
    ]
    return json.dumps(slim, indent=2)


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


_OVERLAP_IGNORE = {
    "the", "and", "for", "with", "that", "this", "from", "after", "was",
    "were", "has", "have", "not", "yet", "are", "but", "its", "into",
    "when", "then", "than", "been", "issue", "issues", "affects",
    "production", "error", "errors", "failed", "failure", "server",
    "application", "applications", "logs", "check", "root", "cause",
    "confirmed", "started", "returning", "report", "only", "also",
}


def _lexical_overlap(incident_text: str, evidence: list[dict]) -> int:
    """Count distinctive incident terms that appear in the evidence text.

    A cheap, model-independent check: if a 502 incident and a Postgres
    runbook share no distinctive term, the runbook is not about this
    incident, whatever the LLM says.
    """
    def terms(text: Any) -> set:
        return {
            w for w in re.findall(r"[a-z0-9]+", str(text).lower())
            if len(w) >= 3 and w not in _OVERLAP_IGNORE
        }

    incident_terms = terms(incident_text)
    evidence_terms: set = set()
    for item in evidence:
        evidence_terms |= terms(item.get("title", ""))
        evidence_terms |= terms(item.get("content", ""))

    return len(incident_terms & evidence_terms)


_STEP_FILLER = {
    "check", "verify", "review", "inspect", "perform", "detailed",
    "ensure", "confirm", "examine", "test", "tests", "testing",
    "the", "and", "for", "with", "between", "current", "that", "this",
    "from", "your", "are", "all",
}


def _step_tokens(text: Any) -> set:
    return {
        w for w in re.findall(r"[a-z0-9]+", str(text).lower())
        if len(w) >= 3 and w not in _STEP_FILLER
    }


def _dedupe_steps(steps: list, threshold: float = 0.7) -> list:
    """Drop exact and near-duplicate steps, keeping the first occurrence.

    "Review PostgreSQL server logs for connection errors" and
    "Check the PostgreSQL server logs for connection errors" count as
    the same step.
    """
    kept: list[str] = []
    kept_norm: set[str] = set()
    kept_tokens: list[set] = []

    for step in steps:
        if not isinstance(step, str) or not step.strip():
            continue

        norm = _norm(step)
        tokens = _step_tokens(step)

        duplicate = norm in kept_norm
        if not duplicate and len(tokens) >= 2:
            for other in kept_tokens:
                if len(other) < 2:
                    continue
                overlap = len(tokens & other) / min(len(tokens), len(other))
                if overlap >= threshold:
                    duplicate = True
                    break

        if duplicate:
            continue

        kept.append(step.strip())
        kept_norm.add(norm)
        kept_tokens.append(tokens)

    return kept


def _clean_ids(raw: Any, valid_ids: set) -> list:
    """Keep only IDs that exist in the real evidence.

    Small models sometimes return IDs as strings ("3"), so coerce first.
    """
    if not isinstance(raw, list):
        return []

    cleaned = []
    for value in raw:
        try:
            value = int(value)
        except (TypeError, ValueError):
            continue
        if value in valid_ids and value not in cleaned:
            cleaned.append(value)
    return cleaned


def _pick_root_cause(hypotheses: list[dict], sufficient: bool):
    if not sufficient:
        return None

    supported = [
        h for h in hypotheses
        if h.get("verification_status") == "supported"
        and h.get("supporting_evidence_ids")
    ]
    if not supported:
        return None

    order = {"high": 0, "medium": 1, "low": 2}
    best = sorted(
        supported,
        key=lambda h: order.get(h.get("confidence"), 3),
    )[0]

    return {
        "cause": best.get("cause"),
        "explanation": best.get("reasoning") or best.get("explanation"),
        "supporting_evidence_ids": best["supporting_evidence_ids"],
        "note": (
            "Supported by reference material only. "
            "Not confirmed against this incident's logs or metrics."
        ),
    }


# --------------------------------------------------------------------------
# Nodes
# --------------------------------------------------------------------------

def retrieve_evidence(state: InvestigationState) -> dict[str, Any]:
    db = SessionLocal()

    try:
        original_query = f"{state['title']} {state['description']}"

        current_query = state.get("current_query", original_query)

        results = hybrid_search(
            db=db,
            query=current_query,
            domain=state["domain"],
            top_k=12,
        )

        candidates = [
            {
                "chunk_id": item["id"],
                "document_id": item["document_id"],
                "title": item["title"],
                "content": item["content"],
                "source_url": item["source_url"],
                "retrieval_score": float(item["score"]),
            }
            for item in results
        ]

        ranked = rerank_documents(
            query=current_query,
            documents=candidates,
            top_k=MAX_EVIDENCE,
        )

        # Log scores so the threshold can be calibrated from real data.
        logger.info(
            "Rerank scores for incident %s: %s",
            state.get("incident_id"),
            [round(r["rerank_score"], 2) for r in ranked],
        )

        ranked = [
            r for r in ranked
            if r["rerank_score"] >= MIN_RERANK_SCORE
        ]

        # Merge with evidence from earlier attempts instead of replacing it.
        merged = {e["chunk_id"]: e for e in state.get("evidence", [])}
        for item in ranked:
            old = merged.get(item["chunk_id"])
            if old is None or item["rerank_score"] > old["rerank_score"]:
                merged[item["chunk_id"]] = item

        evidence = sorted(
            merged.values(),
            key=lambda e: e["rerank_score"],
            reverse=True,
        )[:MAX_EVIDENCE]

        return {
            "evidence": evidence,
            "current_query": current_query,
        }

    finally:
        db.close()


def generate_hypotheses(
    state: InvestigationState,
) -> dict[str, Any]:
    evidence = state.get("evidence", [])

    if not evidence:
        return {
            "hypotheses": [],
            "status": "insufficient_evidence",
        }

    prompt = f"""
Investigate the following technical incident.

INCIDENT:
{state['title']}

DESCRIPTION:
{state['description']}

DOMAIN:
{state['domain']}

RETRIEVED REFERENCE MATERIAL:
{_prompt_evidence(evidence)}

Identify up to three plausible root-cause hypotheses.

Requirements:
- Base hypotheses on the supplied reference material.
- Do not claim a hypothesis is confirmed merely because it is plausible.
- Use the "id" field of the reference material for evidence IDs.
- Identify missing information.
- Use incident-specific clues from the description (for example,
  "after a deployment", error codes, affected components), not only the
  reference material.
- next_checks must be concrete and actionable for THIS incident. Include
  checks drawn from the description even if the reference material does
  not list them.
- Each hypothesis must be tied to a specific symptom in the incident
  description. Do NOT turn every item of a troubleshooting checklist
  into a hypothesis. If the only link between the reference material and
  the incident is generic (for example, both mention "connection"),
  return no hypotheses.
- If the reference material describes a different kind of problem than
  the incident symptoms, return no hypotheses and say so in
  evidence_gaps.

Return JSON with this structure:
{{
  "hypotheses": [
    {{
      "cause": "Potential root cause",
      "explanation": "Why it may explain the incident",
      "supporting_evidence_ids": [1],
      "contradicting_evidence_ids": [],
      "confidence": "low",
      "verification_status": "unverified",
      "next_checks": ["Check the application logs"]
    }}
  ],
  "evidence_gaps": ["Missing diagnostic information"]
}}

Confidence must be low, medium, or high.
Use only evidence IDs present in the supplied reference material.
"""

    result = generate_json(prompt)

    valid_ids = {item["chunk_id"] for item in evidence}

    hypotheses = result.get("hypotheses", [])

    if not isinstance(hypotheses, list):
        hypotheses = []

    validated_hypotheses = []

    for hypothesis in hypotheses[:3]:
        if not isinstance(hypothesis, dict):
            continue

        # Prevent the model from citing nonexistent evidence.
        hypothesis["supporting_evidence_ids"] = _clean_ids(
            hypothesis.get("supporting_evidence_ids"), valid_ids
        )
        hypothesis["contradicting_evidence_ids"] = _clean_ids(
            hypothesis.get("contradicting_evidence_ids"), valid_ids
        )

        if hypothesis.get("confidence") not in {"low", "medium", "high"}:
            hypothesis["confidence"] = "low"

        if not isinstance(hypothesis.get("next_checks"), list):
            hypothesis["next_checks"] = []

        # A generated hypothesis is not automatically verified.
        hypothesis["verification_status"] = "unverified"

        validated_hypotheses.append(hypothesis)

    return {
        "hypotheses": validated_hypotheses,
        "status": "verification_pending",
    }


def verify_hypotheses(
    state: InvestigationState,
) -> dict[str, Any]:
    evidence = state.get("evidence", [])
    hypotheses = state.get("hypotheses", [])

    if not evidence or not hypotheses:
        report = {
            "incident_summary": state["title"],
            "domain": state["domain"],
            "status": "insufficient_evidence",
            "root_cause": None,
            "hypotheses": hypotheses,
            "evidence": evidence,
            "limitations": [
                "No relevant reference material was found for this "
                f"incident in the '{state['domain']}' knowledge base."
            ],
            "recommended_next_steps": [
                "Collect logs and metrics for the affected service.",
                "Check whether the incident was filed under the right "
                "domain.",
            ],
        }

        return {
            "verification": {"sufficient_evidence": False},
            "report": report,
            "status": "insufficient_evidence",
        }

    prompt = f"""
Review the incident hypotheses against the retrieved reference material.

Incident:
{state['title']}

Description:
{state['description']}

Hypotheses:
{json.dumps(hypotheses, indent=2)}

Reference material:
{_prompt_evidence(evidence)}

For each hypothesis:
- Assess whether its supporting evidence actually supports it.
- Identify contradictions.
- Do not infer that missing evidence proves a hypothesis.
- Distinguish a possible explanation from a confirmed finding.
- Keep the hypothesis "cause" text exactly as given.
- List an evidence ID in supporting_evidence_ids ONLY if that material
  states something specific that matches the incident's symptoms. A
  generic checklist item that merely could apply is NOT support; use []
  in that case and say so in the reasoning.

Also judge whether the reference material is about the same kind of
problem as the incident symptoms. Use "off_topic" if it describes a
different failure type, or lists generic checks for a component that the
incident gives no sign of (e.g. database connection docs for a gateway
502 with no database symptoms, credentials or firewall checks with no
sign of auth or network errors). Use "partial" if only some of it applies.

Return JSON:
{{
  "sufficient_evidence": false,
  "evidence_relevance": "relevant",
  "hypotheses": [
    {{
      "cause": "same text as input",
      "verification_status": "supported",
      "reasoning": "Explanation citing evidence IDs",
      "supporting_evidence_ids": [],
      "contradicting_evidence_ids": [],
      "next_checks": []
    }}
  ],
  "limitations": ["What remains unknown"],
  "recommended_next_steps": ["Next diagnostic action"]
}}

verification_status: supported, contradicted, or inconclusive.
evidence_relevance: relevant, partial, or off_topic.
Set sufficient_evidence to true only if the material adequately supports
the finding. A plausible explanation alone is not sufficient.
"""

    result = generate_json(prompt)

    valid_ids = {item["chunk_id"] for item in evidence}
    allowed_statuses = {"supported", "contradicted", "inconclusive"}

    verified = result.get("hypotheses", [])
    if not isinstance(verified, list):
        verified = []
    verified = [v for v in verified if isinstance(v, dict)]

    by_cause = {_norm(v.get("cause")): v for v in verified}

    merged_hypotheses = []

    for index, original in enumerate(hypotheses):
        review = by_cause.get(_norm(original.get("cause")))
        if review is None and index < len(verified):
            review = verified[index]

        # Start from the original so explanation, confidence and
        # next_checks survive verification.
        merged = dict(original)

        if review:
            status = review.get("verification_status")
            merged["verification_status"] = (
                status if status in allowed_statuses else "inconclusive"
            )
            merged["reasoning"] = review.get("reasoning", "")

            for key in (
                "supporting_evidence_ids",
                "contradicting_evidence_ids",
            ):
                merged[key] = _clean_ids(review.get(key), valid_ids)

            new_checks = review.get("next_checks")
            if isinstance(new_checks, list) and new_checks:
                merged["next_checks"] = new_checks
        else:
            merged["verification_status"] = "inconclusive"
            merged["reasoning"] = "Not reviewed by the verification step."

        merged_hypotheses.append(merged)

    limitations = result.get("limitations", [])
    next_steps = result.get("recommended_next_steps", [])

    if not isinstance(limitations, list):
        limitations = []
    if not isinstance(next_steps, list):
        next_steps = []

    relevance = result.get("evidence_relevance", "partial")
    if relevance not in {"relevant", "partial", "off_topic"}:
        relevance = "partial"

    # Do not rely on the model alone: check term overlap in code.
    overlap = _lexical_overlap(
        f"{state['title']} {state['description']}", evidence
    )
    model_relevance = relevance
    if overlap == 0:
        relevance = "off_topic"
    elif overlap == 1 and relevance == "relevant":
        relevance = "partial"

    logger.info(
        "Incident %s relevance: model=%s lexical_overlap=%s final=%s",
        state.get("incident_id"), model_relevance, overlap, relevance,
    )

    # Off-topic material cannot support anything, whatever the model says.
    if relevance == "off_topic":
        for h in merged_hypotheses:
            h["verification_status"] = "inconclusive"

    # Material that is only partly relevant may be related to a hypothesis
    # but cannot back it unless the hypothesis was actually supported.
    # Keep the link, but label it honestly.
    if relevance != "relevant":
        for h in merged_hypotheses:
            h["related_evidence_ids"] = []
            if h.get("verification_status") != "supported":
                h["related_evidence_ids"] = h.get(
                    "supporting_evidence_ids", []
                )
                h["supporting_evidence_ids"] = []

    sufficient = (
        result.get("sufficient_evidence") is True
        and relevance != "off_topic"
        and any(
            h["verification_status"] == "supported"
            and h.get("supporting_evidence_ids")
            for h in merged_hypotheses
        )
    )

    # Always state what was searched, so a misfiled incident is obvious.
    doc_count = len({e.get("document_id") for e in evidence})
    limitations.insert(
        0,
        f"Only the '{state['domain']}' knowledge base was searched "
        f"({doc_count} reference document(s) retrieved). If this incident "
        "was filed under the wrong domain, re-file it and investigate "
        "again.",
    )

    if relevance == "off_topic":
        limitations.insert(
            0,
            "The retrieved reference material does not match this "
            "incident's symptoms. Check the incident domain and the "
            "knowledge base contents.",
        )

    # Surface hypothesis-level checks in the overall steps,
    # removing exact and near-duplicates.
    all_steps = list(next_steps)
    for h in merged_hypotheses:
        all_steps.extend(
            c for c in h.get("next_checks", []) if isinstance(c, str)
        )
    next_steps = _dedupe_steps(all_steps)

    status = "investigated" if sufficient else "insufficient_evidence"

    report = {
        "incident_summary": state["title"],
        "domain": state["domain"],
        "status": status,
        "root_cause": _pick_root_cause(merged_hypotheses, sufficient),
        "hypotheses": merged_hypotheses,
        "evidence": evidence,
        "limitations": limitations,
        "recommended_next_steps": next_steps,
    }

    return {
        "verification": {"sufficient_evidence": sufficient},
        "hypotheses": merged_hypotheses,
        "report": report,
        "status": "completed" if sufficient else "insufficient_evidence",
    }


def refine_investigation_query(
    state: InvestigationState,
) -> dict[str, Any]:
    retry_count = state.get("retry_count", 0)

    prompt = f"""
You are refining a technical incident investigation search query.

Incident title:
{state['title']}

Incident description:
{state['description']}

Domain:
{state['domain']}

Current query:
{state.get('current_query', state['description'])}

Previous reference material:
{_prompt_evidence(state.get('evidence', []))}

Create a more specific search query that may retrieve
additional relevant technical evidence.

Focus on technical error messages, likely components,
relevant symptoms, and diagnostic terminology.

Do not assume a root cause has been confirmed.

Return JSON:
{{
  "query": "Refined search query"
}}
"""

    result = generate_json(prompt)

    refined_query = result.get("query", "")

    if not isinstance(refined_query, str):
        refined_query = ""

    refined_query = refined_query.strip()

    if len(refined_query) < 5:
        refined_query = (
            f"{state['title']} {state['description']} "
            f"{state['domain']} troubleshooting"
        )

    return {
        "current_query": refined_query,
        "retry_count": retry_count + 1,
    }


# --------------------------------------------------------------------------
# Routing
# --------------------------------------------------------------------------

def should_retry_after_retrieval(
    state: InvestigationState,
) -> str:
    evidence = state.get("evidence", [])
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 1)

    # Evidence was retrieved successfully.
    if evidence:
        return "generate_hypotheses"

    # Retry retrieval if attempts remain.
    if retry_count < max_retries:
        return "refine_query"

    # No evidence after retries.
    return "verify_hypotheses"


def should_retry_after_verification(
    state: InvestigationState,
) -> str:
    verification = state.get("verification", {})
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 1)

    # Stop when the verification node reports sufficient evidence.
    if verification.get("sufficient_evidence") is True:
        return "finish"

    # Retry if attempts remain.
    if retry_count < max_retries:
        return "refine_query"

    return "finish"