#!/usr/bin/env python3
"""
April interpretation-layer repair for the 2026-09-21 dialogue regression.

Usage:
  python April_interpretation_layer_dialogue_synced_REPAIR.py SOURCE.py
  python April_interpretation_layer_dialogue_synced_REPAIR.py SOURCE.py FIXED.py

Creates a .bak backup and a source-preserving fixed copy. It refuses to patch
when a required anchor is missing or ambiguous.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{name}: expected exactly 1 match, got {count}")
    return text.replace(old, new, 1)


def replace_regex_once(text: str, pattern: str, new: str, name: str) -> str:
    out, count = re.subn(pattern, new, text, count=1, flags=re.S | re.M)
    if count != 1:
        raise RuntimeError(f"{name}: expected exactly 1 regex match, got {count}")
    return out


def patch_source(source: str) -> tuple[str, list[str]]:
    fixed = source
    applied: list[str] = []

    # 1) Boundary before the semantic measurement used by the main analyzer.
    measure_anchor = '''        p=self.measure(
            text,
            previous_assistant=last_a,
            previous_user=last_u,
            active_topic=active_topic,
            active_goal=active_goal,
        )
'''
    boundary = '''        # ================================================================
        # CURRENT-TURN AUTHORITY BOUNDARY (repair 2026-09-21)
        # ================================================================
        # A request that is semantically self-contained and has no explicit
        # discourse reference must start a new turn. A stale CONTINUE result
        # must not leak the previous topic/representation into measurement.
        _seq_trajectory = (
            sequential_dialogue.get("trajectory")
            if isinstance(sequential_dialogue, dict)
            and isinstance(sequential_dialogue.get("trajectory"), dict)
            else {}
        )
        _force_current_turn_new = bool(
            str(sequential_relation or "").upper() == "CONTINUE"
            and bool(_seq_trajectory.get("self_contained"))
            and not bool(_seq_trajectory.get("explicit_reference"))
            and not bool(_seq_trajectory.get("grammatical_anaphora"))
            and not bool(_seq_trajectory.get("pending_input"))
            and not bool(_seq_trajectory.get("explicit_task"))
        )
        if _force_current_turn_new:
            sequential_relation = "NEW"
            continuation = False
            reference = False
            memory = False
            sequential_dialogue = dict(sequential_dialogue)
            sequential_dialogue["relation"] = "NEW"
            sequential_dialogue["subtype"] = "NEW_TOPIC"
            sequential_dialogue["selected_pair"] = {}
            sequential_dialogue["selected_memory_index"] = -1
            sequential_dialogue["resolved_reference"] = ""
            _seq_trajectory = dict(_seq_trajectory)
            _seq_trajectory["forced_current_turn_boundary"] = True
            _seq_trajectory["boundary_reason"] = "self_contained_without_reference_evidence"
            sequential_dialogue["trajectory"] = _seq_trajectory
            print("🛡️ APRIL CURRENT-TURN BOUNDARY:", {
                "forced_new_topic": True,
                "reason": "self_contained_without_reference_evidence",
                "current_request": self.normalize(text),
            })

'''
    fixed = replace_once(fixed, measure_anchor, boundary + measure_anchor, "current_turn_boundary")
    applied.append("current_turn_boundary")

    # 2) Continuation: preserve the actual previous pair as structured data.
    old = '''        resolved_request = text
        history_task_context = dict(dialogue_vector.get("history_task_context") or {})

        if sequential_relation == "CONTINUE" and (last_u or last_a):
            resolved_request = (
                f"{text}\\n\\n"
                "The current request is a semantic continuation of the immediately "
                "preceding completed USER→APRIL turn. Continue from that result; "
                "do not ask the user to repeat information already present.\\n"
                f"Previous USER request: {last_u}\\n"
                f"Previous APRIL answer: {last_a}"
            )
            if pending_previous_input:
                resolved_request += (
                    "\\nThe previous April answer requested user input. "
                    "The current user message supplies that input and completes the pending task; "
                    "treat it as the value of the preceding task, not as a new topic."
                )

'''
    new = '''        # CURRENT REQUEST is the sole request operand. Previous dialogue
        # remains structured context and never becomes part of the prompt text.
        resolved_request = text
        history_task_context = dict(dialogue_vector.get("history_task_context") or {})

        if sequential_relation == "CONTINUE" and (last_u or last_a):
            dialogue_vector["continuation_context"] = {
                "previous_user_turn": self.normalize(last_u),
                "previous_april_turn": self.normalize(last_a),
                "pending_previous_input": bool(pending_previous_input),
                "source": "sequential_dialogue_owner",
            }

'''
    fixed = replace_once(fixed, old, new, "continuation_request_concatenation")
    applied.append("continuation_request_concatenation")

    # 3) Recall: structured operand only.
    old = '''        selected_memory = dialogue_vector.get("selected_memory_operand")
        if selected_relation == "RECALL" and isinstance(selected_memory, dict):
            recalled_user = self.normalize(selected_memory.get("user"))
            recalled_result = self.normalize(
                selected_memory.get("result") or selected_memory.get("april") or selected_memory.get("assistant")
            )
            if recalled_user or recalled_result:
                resolved_request = (
                    f"{text}\\n\\n"
                    "The current request recalls an older authenticated USER↔APRIL result. "
                    "Use the recalled result as a concrete context operand and develop it; "
                    "do not ask the user to resend the previous result.\\n"
                    f"Recalled USER request: {recalled_user}\\n"
                    f"Recalled APRIL result: {recalled_result}"
                )
                reference = True
                memory = False
                dialogue_vector["resolved_memory_operand"] = {
                    "user": recalled_user,
                    "result": recalled_result,
                    "index": dialogue_vector.get("selected_memory_index", -1),
                }

'''
    new = '''        # RECALL remains structured context. It never rewrites `resolved_request`.
        selected_memory = dialogue_vector.get("selected_memory_operand")
        if selected_relation == "RECALL" and isinstance(selected_memory, dict):
            recalled_user = self.normalize(selected_memory.get("user"))
            recalled_result = self.normalize(
                selected_memory.get("result")
                or selected_memory.get("april")
                or selected_memory.get("assistant")
            )
            if recalled_user or recalled_result:
                reference = True
                memory = False
                dialogue_vector["resolved_memory_operand"] = {
                    "user": recalled_user,
                    "result": recalled_result,
                    "index": dialogue_vector.get("selected_memory_index", -1),
                }
                dialogue_vector["recall_context"] = {
                    "user_request": recalled_user,
                    "result": recalled_result,
                    "source": "authenticated_dialogue_history",
                }

'''
    fixed = replace_once(fixed, old, new, "recall_request_concatenation")
    applied.append("recall_request_concatenation")

    # 4) History task bridge: operands/results stay typed.
    old = '''        if history_task_context.get("required"):
            selected_results = history_task_context.get("selected_results") or []
            lines = []
            for idx, item in enumerate(selected_results, start=1):
                lines.append(
                    f"Historical result {idx}: {item.get('result')} (from USER: {item.get('user')}; APRIL: {item.get('assistant')})"
                )
            resolved_request = (
                f"{text}\\n\\n"
                "The current calculation is history-dependent. The interpretation engine resolved the "
                "required operands from the two most recent concrete numeric results in the authenticated "
                "USER↔APRIL dialogue history. Use these values directly; do not ask the user to repeat them.\\n"
                + "\\n".join(lines)
            )

'''
    new = '''        if history_task_context.get("required"):
            selected_results = history_task_context.get("selected_results") or []
            dialogue_vector["history_resolution"] = {
                "required": True,
                "operation": history_task_context.get("operation")
                    or history_task_context.get("arithmetic_operation")
                    or "",
                "resolved_operands": list(
                    history_task_context.get("resolved_operands") or []
                ),
                "available_numeric_results": history_task_context.get(
                    "available_numeric_results", 0
                ),
                "selected_results": selected_results,
                "source": "interpretation_history_task_context",
            }

'''
    fixed = replace_once(fixed, old, new, "history_task_request_concatenation")
    applied.append("history_task_request_concatenation")

    # 5) Resolved referent: structured, never appended to user text.
    old = '''        if resolved_reference and (continuation or reference):
            # Structural discourse resolution: make the provider-facing request
            # explicit without hard-coded topic/entity rules.
            resolved_request = (
                f"{text}\\n\\nContextual referent resolved from the immediately previous human exchange: "
                f"{resolved_reference}. Answer the current request about that referent without asking the user to repeat it."
            )

'''
    new = '''        if resolved_reference and (continuation or reference):
            dialogue_vector["resolved_reference"] = self.normalize(resolved_reference)
            dialogue_vector["reference_context"] = {
                "target": self.normalize(resolved_reference),
                "source": "semantic_reference_resolution",
            }

'''
    fixed = replace_once(fixed, old, new, "resolved_reference_concatenation")
    applied.append("resolved_reference_concatenation")

    # 6) Safety fence after reference metadata.
    anchor = '''        if reference_resolution.get("resolved") and reference_resolution.get("target"):
            resolved_scene = dict(resolved_scene or {})
            resolved_scene["reference_target"] = reference_resolution.get("target")
'''
    fence = '''        if reference_resolution.get("resolved") and reference_resolution.get("target"):
            resolved_scene = dict(resolved_scene or {})
            resolved_scene["reference_target"] = reference_resolution.get("target")
            resolved_scene["reference_resolution"] = dict(reference_resolution)

        # ================================================================
        # REQUEST-OPERAND SAFETY FENCE (repair 2026-09-21)
        # ================================================================
        # No processor instructions or history prose may ever become the
        # current request operand. Such material is internal-only metadata.
        _request_operand = self.normalize(resolved_request)
        _internal_prompt_markers = (
            "The current request is a semantic continuation of the immediately preceding",
            "The current request recalls an older authenticated USER↔APRIL result.",
            "The current calculation is history-dependent.",
            "Previous USER request:",
            "Previous APRIL answer:",
            "Recalled USER request:",
            "Recalled APRIL result:",
            "Resolved semantic referent:",
            "Use this referent as the object of the current request",
        )
        if any(marker in _request_operand for marker in _internal_prompt_markers):
            print("🛡️ APRIL REQUEST OPERAND SANITIZER:", {
                "removed_internal_prompt_material": True,
                "current_request": self.normalize(text),
            })
            resolved_request = self.normalize(text)
        else:
            resolved_request = _request_operand or self.normalize(text)
'''
    fixed = replace_once(fixed, anchor, fence, "request_operand_safety_fence")
    applied.append("request_operand_safety_fence")

    # 7) Output-purity fence after current scene composition is enumerated.
    anchor = '''        for index, item in enumerate(scene_composition):
            item["sequence"] = index
'''
    fence = '''        for index, item in enumerate(scene_composition):
            item["sequence"] = index

        # ================================================================
        # CURRENT OUTPUT PURITY FENCE (repair 2026-09-21)
        # ================================================================
        # Ordinary informational/explanatory turns stay textual unless a
        # structured output is represented by a current-turn segment.
        _task_output_segments = (
            task_understanding.get("output_segments")
            if isinstance(task_understanding, dict)
            else []
        )
        _has_current_structured_segment = bool(
            isinstance(_task_output_segments, list)
            and any(
                isinstance(segment, dict)
                and _clean_representation(segment.get("output"))
                    in STRUCTURED_REPRESENTATIONS
                and self.normalize(
                    segment.get("segment_text")
                    or segment.get("text")
                    or ""
                )
                for segment in _task_output_segments
            )
        )
        _current_operation = str(p.get("best_operation") or "").lower()
        if (
            _current_operation in {
                "answer", "explain", "analyze", "list", "retrieve", "summarize"
            }
            and not _has_current_structured_segment
        ):
            complete_outputs = ["text"]
            production = "text"
            source = "current_turn_text_authority"
            locked = False
            scene_composition = [{
                "segment_index": 1,
                "representation": "text",
                "segment_text": self.normalize(text),
                "semantic_source": "current_turn_text_authority",
                "sequence": 0,
            }]
'''
    fixed = replace_once(fixed, anchor, fence, "current_output_purity_fence")
    applied.append("current_output_purity_fence")

    # Final checks.
    for marker in (
        "CURRENT-TURN AUTHORITY BOUNDARY (repair 2026-09-21)",
        "REQUEST-OPERAND SAFETY FENCE (repair 2026-09-21)",
        "CURRENT OUTPUT PURITY FENCE (repair 2026-09-21)",
        '"continuation_context"',
        '"history_resolution"',
        '"recall_context"',
    ):
        if marker not in fixed:
            raise RuntimeError(f"verification: missing {marker}")

    return fixed, applied


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(
            "Usage: python April_interpretation_layer_dialogue_synced_REPAIR.py "
            "SOURCE.py [FIXED.py]"
        )
        return 2

    src = Path(sys.argv[1]).expanduser().resolve()
    if not src.is_file():
        print(f"Source file not found: {src}")
        return 2

    dst = (
        Path(sys.argv[2]).expanduser().resolve()
        if len(sys.argv) == 3
        else src.with_name(src.stem + "_fixed.py")
    )

    original = src.read_text(encoding="utf-8")
    fixed, applied = patch_source(original)

    backup = src.with_suffix(src.suffix + ".bak")
    if not backup.exists():
        shutil.copy2(src, backup)

    dst.write_text(fixed, encoding="utf-8")
    print(f"PATCHED: {dst}")
    print(f"BACKUP:  {backup}")
    print("APPLIED:")
    for name in applied:
        print(f"  - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
