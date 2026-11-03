"""Shared File Delivery Room for Free and Premium SceneContracts.

This room creates FileDeliveryBlock renderer artifacts from already-produced
TableBlock, CodeBlock, long-form text, or authenticated saved asset references.
It does not generate source content, decide plan entitlement, or persist bytes;
executors persist the payload and attach authenticated dialogue-memory references.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict
import csv
import io
import re
import uuid

from blocks.C_ARTIFACT_CONTRACT import create_artifact

ROOM_ID = "C_FILE_DELIVERY_ROOM"
ARTIFACT_TYPE = "file"
RENDERER = "FileDeliveryBlock"


def _object(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _identity(task: Dict[str, Any]) -> Dict[str, Any]:
    scene = _object(task.get("scene"))
    scene_id = str(task.get("scene_id") or scene.get("scene_id") or f"scene_{uuid.uuid4().hex[:12]}")
    turn_id = str(task.get("turn_id") or scene.get("turn_id") or f"turn_{uuid.uuid4().hex[:12]}")
    block_id = str(task.get("block_id") or scene.get("block_id") or f"file_{uuid.uuid4().hex[:12]}")
    return {"scene_id": scene_id, "turn_id": turn_id, "flow_id": str(task.get("flow_id") or scene.get("flow_id") or ""),
            "block_id": block_id, "render_id": str(task.get("render_id") or scene.get("render_id") or f"{block_id}:render")}


class FileDeliveryRoom:
    name = ROOM_ID
    room_type = "file_delivery"
    artifact_type = ARTIFACT_TYPE
    artifact_version = "1.0"
    web_space_ready = True
    renderer_safe = True
    continuity_safe = True
    orchestration_safe = True

    def can_handle(self, text: Any, context: Any) -> bool:
        return self.evaluate(text, context) > 0

    def evaluate(self, text: Any, context: Any) -> float:
        ctx = _object(context)
        semantic = _object(ctx.get("semantic"))
        requested = semantic.get("requested_outputs") or ctx.get("requested_outputs") or []
        return 1.0 if "file" in {str(item).lower() for item in requested if item} else 0.0

    def build_work_order(self, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        ctx = dict(context or {})
        return {"scene_id": ctx.get("scene_id"), "turn_id": ctx.get("turn_id"), "flow_id": ctx.get("flow_id"),
                "block_id": ctx.get("block_id"), "render_id": ctx.get("render_id"),
                "payload": deepcopy(ctx.get("file_payload") or ctx.get("payload") or {}),
                "title": ctx.get("title"), "filename": ctx.get("filename")}

    def process(self, task: Dict[str, Any]):
        source = dict(task or {})
        payload = _object(source.get("payload") or source.get("file_payload"))
        filename = str(payload.get("filename") or payload.get("name") or source.get("filename") or "april-file.txt").strip()
        filename = filename.replace("\\", "_").replace("/", "_").replace("\r", "").replace("\n", "")[:180] or "april-file.txt"
        mime = str(payload.get("mime_type") or source.get("mime_type") or "application/octet-stream")[:120]
        asset_ref = _object(payload.get("asset_ref") or source.get("asset_ref"))
        export_payload = _object(payload.get("export_payload") or source.get("export_payload"))
        content = payload.get("content") or payload.get("text") or payload.get("code") or source.get("content")
        # Keep raw binary data out of the SceneContract. A table may instead carry
        # its structured source for the existing protected XLSX export endpoint.
        if not asset_ref and not export_payload and not (isinstance(content, str) and content.strip()):
            raise ValueError("C_FILE_DELIVERY_ROOM requires content, asset_ref, or export_payload")
        identity = _identity(source)
        normalized = {"title": str(payload.get("title") or source.get("title") or filename),
                      "filename": filename, "mime_type": mime,
                      "size_bytes": int(payload.get("size_bytes") or 0),
                      "asset_ref": deepcopy(asset_ref), "export_payload": deepcopy(export_payload),
                      "source": str(payload.get("source") or "dialogue_asset"),
                      "description": str(payload.get("description") or source.get("description") or ""),
                      "scene": identity, "room": ROOM_ID, "payload_version": "april.file.v1"}
        if isinstance(content, str) and content.strip() and not asset_ref:
            normalized["content"] = content
        artifact = create_artifact(artifact_type=ARTIFACT_TYPE, room_source=ROOM_ID,
            data={"title": normalized["title"], "description": normalized["description"],
                  "payload": normalized, "renderer": RENDERER, "viewer": RENDERER,
                  "scene_id": identity["scene_id"], "turn_id": identity["turn_id"],
                  "flow_id": identity["flow_id"], "block_id": identity["block_id"],
                  "render_id": identity["render_id"], "text_companion_required": False})
        artifact.quality.validation_passed = True
        artifact.quality.quality_score = artifact.quality.confidence_score = artifact.quality.completeness_score = 1.0
        return artifact

    def execute(self, machine_request: Any):
        return self.process(machine_request) if isinstance(machine_request, dict) else None

    async def handle(self, user_id, text, context, run):
        return self.process(self.build_work_order(dict(context or {})))


ROOM = FileDeliveryRoom()



def attach_file_delivery_blocks(
    render_blocks: Any,
    output_asset_refs: Any,
    requested_outputs: Any,
    *,
    file_delivery_mode: str = "with_inline",
    language: str = "en",
    message_id: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Attach explicit file deliveries to existing blocks in one SceneContract.

    This adapter is plan-neutral. Free/Premium interpreters and executors decide
    their own limits; this function only binds already-persisted bytes or an
    existing structured table payload to the common FileDeliveryBlock renderer.
    """
    blocks = [deepcopy(item) for item in (render_blocks or []) if isinstance(item, dict)]
    refs = [dict(item) for item in (output_asset_refs or []) if isinstance(item, dict)]
    requested = {str(item).strip().lower() for item in (requested_outputs or []) if str(item).strip()}
    wants_file = "file" in requested
    if not wants_file:
        return blocks, []

    def block_payload(block: dict[str, Any]) -> dict[str, Any]:
        payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
        merged = dict(block)
        merged.update(payload)
        return merged

    file_blocks: list[dict[str, Any]] = []
    table_blocks = [
        block for block in blocks
        if str(block.get("type") or block.get("artifact_type") or "").strip().lower() == "table"
    ]
    # TableBlock has its own export control only when the table is also shown
    # inline. An explicit file-only request must instead produce a real XLSX
    # FileDeliveryBlock so the user receives one downloadable workbook.
    wants_inline_table = (
        "table" in requested and bool(table_blocks)
        and str(file_delivery_mode or "").lower() != "file_only"
    )
    existing_file_names = {
        str(block_payload(block).get("filename") or block_payload(block).get("name") or "").strip().casefold()
        for block in blocks if str(block.get("type") or block.get("artifact_type") or "").lower() in {"file", "document", "file_card", "text_file", "code_file"}
    }

    # Attach already-saved output bytes. Image payloads are intentionally excluded.
    saved_refs = [ref for ref in refs
                  if str(ref.get("asset_role") or "april_output") == "april_output"
                  and str(ref.get("output_type") or "").lower() in {"code", "file"}
                  and re.fullmatch(r"[a-f0-9]{64}", str(ref.get("sha256") or ""), re.I)]
    if str(file_delivery_mode or "").lower() == "file_only" and table_blocks:
        # When the table itself is the requested deliverable, the protected XLSX
        # export below is canonical. Do not also attach the provider's CSV asset
        # as a second, competing download card.
        saved_refs = [ref for ref in saved_refs
                      if not str(ref.get("filename") or "").lower().endswith(".csv")
                      and "text/csv" not in str(ref.get("mime_type") or "").lower()]
    if saved_refs:
        for block in blocks:
            block_type = str(block.get("type") or block.get("artifact_type") or "").lower()
            if block_type not in {"file", "document", "file_card", "text_file", "code_file"}:
                continue
            payload = block_payload(block)
            existing_ref = payload.get("asset_ref") if isinstance(payload.get("asset_ref"), dict) else {}
            existing_ref_is_valid = bool(
                str(existing_ref.get("message_id") or "").strip()
                and re.fullmatch(r"[a-f0-9]{64}", str(existing_ref.get("sha256") or ""), re.I)
            )
            # Inline text is useful for preview/share, but it is not a durable
            # mobile download route. Prefer the already-persisted, owner-scoped
            # asset reference whenever one can be matched to this file.
            if existing_ref_is_valid or isinstance(payload.get("export_payload"), dict):
                continue
            filename = str(payload.get("filename") or payload.get("name") or "").strip().casefold()
            ref = next((item for item in saved_refs if filename and str(item.get("filename") or "").strip().casefold() == filename), None)
            if ref is None and len(saved_refs) == 1:
                ref = saved_refs[0]
            if ref:
                asset_ref = {
                    "message_id": str(ref.get("message_id") or message_id),
                    "sha256": str(ref.get("sha256") or ""),
                    "filename": str(ref.get("filename") or payload.get("filename") or "april-output.txt"),
                    "mime_type": str(ref.get("mime_type") or "text/plain; charset=utf-8"),
                    "size_bytes": int(ref.get("size_bytes") or 0),
                }
                payload.update({"filename": asset_ref["filename"], "mime_type": asset_ref["mime_type"],
                                "size_bytes": asset_ref["size_bytes"], "asset_ref": asset_ref,
                                "source": "dialogue_asset"})
                block["payload"] = payload
                block["type"] = "file"
                block["artifact_type"] = "file"
                block["renderer"] = RENDERER
                block["viewer"] = RENDERER

        for ref in saved_refs[:8]:
            filename = str(ref.get("filename") or "april-output.txt")[:180]
            if filename.casefold() in existing_file_names:
                continue
            asset_ref = {
                "message_id": str(ref.get("message_id") or message_id),
                "sha256": str(ref.get("sha256") or ""),
                "filename": filename,
                "mime_type": str(ref.get("mime_type") or "text/plain; charset=utf-8"),
                "size_bytes": int(ref.get("size_bytes") or 0),
            }
            file_blocks.append({
                "type": "file", "artifact_type": "file", "renderer": RENDERER, "viewer": RENDERER,
                "source_room": ROOM_ID,
                "payload": {
                    "title": filename, "filename": filename,
                    "mime_type": asset_ref["mime_type"], "size_bytes": asset_ref["size_bytes"],
                    "asset_ref": asset_ref, "source": "dialogue_asset",
                    "description": "",
                },
            })
            existing_file_names.add(filename.casefold())

    # If the model produced both an inline table and a CSV file for the same
    # table request, fold the CSV rows into a second worksheet. This prevents
    # two competing downloads (CSV + XLSX) and preserves the full row dataset.
    csv_blocks_to_remove: set[int] = set()
    table_extra_sheets: list[dict[str, Any]] = []
    if table_blocks:
        for file_block in blocks:
            file_type = str(file_block.get("type") or file_block.get("artifact_type") or "").strip().lower()
            if file_type not in {"file", "document", "file_card", "text_file"}:
                continue
            file_payload = block_payload(file_block)
            filename_hint = str(file_payload.get("filename") or file_payload.get("name") or "").strip().lower()
            mime_hint = str(file_payload.get("mime_type") or file_payload.get("content_type") or "").strip().lower()
            if not (filename_hint.endswith(".csv") or "text/csv" in mime_hint or "application/csv" in mime_hint):
                continue
            csv_content = file_payload.get("content") or file_payload.get("text")
            if not isinstance(csv_content, str) or not csv_content.strip():
                continue
            try:
                csv_text = csv_content.lstrip("\ufeff")
                sample = csv_text[:4096]
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=";\t,|")
                except csv.Error:
                    dialect = csv.excel
                    dialect.delimiter = ";" if ";" in sample else ","
                csv_rows = list(csv.reader(io.StringIO(csv_text), dialect))
                csv_rows = [row for row in csv_rows if any(str(cell).strip() for cell in row)]
                if len(csv_rows) < 2 or len(csv_rows[0]) < 2:
                    continue
                csv_headers = [str(cell).strip()[:320] for cell in csv_rows[0]]
                csv_data = [
                    [str(row[index]).strip()[:32000] if index < len(row) else "" for index in range(len(csv_headers))]
                    for row in csv_rows[1:10001]
                ]
                if not csv_data:
                    continue
                sheet_title = "Все элементы" if any("атом" in h.lower() or "элемент" in h.lower() for h in csv_headers) else "Полные данные"
                table_extra_sheets.append({"title": sheet_title, "headers": csv_headers, "rows": csv_data})
                csv_blocks_to_remove.add(id(file_block))
            except Exception:
                # An unparseable CSV remains a separate file; never discard its content.
                continue

        if table_extra_sheets:
            primary_table = table_blocks[0]
            primary_payload = block_payload(primary_table)
            existing_sheets = primary_payload.get("additional_sheets")
            combined_sheets = list(existing_sheets) if isinstance(existing_sheets, list) else []
            known_sheet_names = {str(item.get("title") or "").casefold() for item in combined_sheets if isinstance(item, dict)}
            for sheet in table_extra_sheets:
                if str(sheet.get("title") or "").casefold() not in known_sheet_names:
                    combined_sheets.append(sheet)
                    known_sheet_names.add(str(sheet.get("title") or "").casefold())
            primary_table["additional_sheets"] = combined_sheets
            primary_table_payload = primary_table.get("payload") if isinstance(primary_table.get("payload"), dict) else {}
            primary_table_payload["additional_sheets"] = combined_sheets
            primary_table["payload"] = primary_table_payload
            blocks = [item for item in blocks if id(item) not in csv_blocks_to_remove]

            # Keep the visible response accurate after replacing the CSV card
            # with a single Excel workbook.
            language_key = str(language or "en").lower().split("-")[0]
            csv_replacements = {
                "ru": [(r"CSV[- ]файл", "Excel-файл"), (r"CSV", "Excel")],
                "ua": [(r"CSV[- ]файл", "Excel-файл"), (r"CSV", "Excel")],
                "uk": [(r"CSV[- ]файл", "Excel-файл"), (r"CSV", "Excel")],
                "en": [(r"CSV\s+file", "Excel workbook"), (r"CSV", "Excel")],
                "es": [(r"archivo\s+CSV", "libro de Excel"), (r"CSV", "Excel")],
                "de": [(r"CSV-Datei", "Excel-Datei"), (r"CSV", "Excel")],
                "fr": [(r"fichier\s+CSV", "classeur Excel"), (r"CSV", "Excel")],
                "it": [(r"file\s+CSV", "file Excel"), (r"CSV", "Excel")],
                "pl": [(r"plik\s+CSV", "plik Excel"), (r"CSV", "Excel")],
                "pt": [(r"arquivo\s+CSV", "arquivo Excel"), (r"CSV", "Excel")],
                "nl": [(r"CSV-bestand", "Excel-bestand"), (r"CSV", "Excel")],
            }
            replacements = csv_replacements.get(language_key, [(r"CSV", "Excel")])
            for text_block in blocks:
                if str(text_block.get("type") or text_block.get("artifact_type") or "").strip().lower() not in {"text", "markdown", "message", "message_text", "answer"}:
                    continue
                targets = [text_block]
                nested_payload = text_block.get("payload")
                if isinstance(nested_payload, dict):
                    targets.append(nested_payload)
                for target in targets:
                    for text_key in ("content", "text", "answer", "summary"):
                        current_text = target.get(text_key)
                        if not isinstance(current_text, str) or "csv" not in current_text.lower():
                            continue
                        for pattern, replacement in replacements:
                            current_text = re.sub(pattern, replacement, current_text, flags=re.IGNORECASE)
                        target[text_key] = current_text

    # A file-only table request uses the protected XLSX endpoint. When the user
    # also requested an inline table, TableBlock itself owns the same XLSX
    # download/share actions, so a second FileDeliveryBlock would be a duplicate.
    for block in blocks:
        block_type = str(block.get("type") or block.get("artifact_type") or "").strip().lower()
        if block_type != "table":
            continue
        table = block_payload(block)
        headers = table.get("headers") or table.get("columns") or table.get("column_headers") or []
        rows = table.get("rows") or table.get("data") or table.get("values") or []
        if not isinstance(headers, list) or not isinstance(rows, list) or not rows:
            continue
        # Match TableBlock's structural normalization so the existing XLSX
        # endpoint receives string headers and rectangular array rows even when
        # the model supplied column descriptors or object-shaped records.
        column_keys: list[str] = []
        normalized_headers: list[str] = []
        for index, column in enumerate(headers):
            if isinstance(column, dict):
                key = str(column.get("key") or column.get("field") or column.get("id") or column.get("name") or column.get("header") or column.get("title") or column.get("label") or f"column_{index + 1}")
                label = str(column.get("label") or column.get("title") or column.get("name") or column.get("header") or column.get("key") or column.get("field") or column.get("id") or f"Column {index + 1}")
            else:
                label = str(column if column is not None else f"Column {index + 1}")
                key = label
            column_keys.append(key)
            normalized_headers.append(label)
        if isinstance(rows[0], dict):
            if not column_keys:
                seen_keys: list[str] = []
                for row in rows:
                    if isinstance(row, dict):
                        for key in row.keys():
                            key_text = str(key)
                            if key_text not in seen_keys:
                                seen_keys.append(key_text)
                column_keys = seen_keys
                normalized_headers = list(seen_keys)
            normalized_rows = [
                [row.get(key, row.get(normalized_headers[index] if index < len(normalized_headers) else key, "")) if isinstance(row, dict) else ""
                 for index, key in enumerate(column_keys)]
                for row in rows
            ]
        elif isinstance(rows[0], list):
            normalized_rows = [
                [row[index] if index < len(row) else "" for index in range(len(normalized_headers))]
                for row in rows if isinstance(row, list)
            ]
            if not normalized_headers and normalized_rows:
                width = max(len(row) for row in normalized_rows)
                normalized_headers = [f"Column {index + 1}" for index in range(width)]
                normalized_rows = [row + [""] * (width - len(row)) for row in normalized_rows]
        else:
            continue
        if not normalized_headers or not normalized_rows:
            continue
        if wants_inline_table:
            # The visible TableBlock has a built-in XLSX export menu. Keeping an
            # extra FileDeliveryBlock here would create a second, inconsistent file.
            continue
        default_table_title = "Таблица" if str(language or "").lower().startswith(("ru", "uk", "ua")) else "April table"
        title = str(table.get("title") or table.get("caption") or default_table_title)[:120]
        filename = re.sub(r"[^\w.-]+", "_", title, flags=re.UNICODE).strip("._")[:90] or "april-table"
        filename = filename if filename.lower().endswith(".xlsx") else f"{filename}.xlsx"
        if filename.casefold() in existing_file_names:
            continue
        file_blocks.append({
            "type": "file", "artifact_type": "file", "renderer": RENDERER, "viewer": RENDERER,
            "source_room": ROOM_ID,
            "payload": {
                "title": title, "filename": filename,
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "source": "table_export",
                "description": "",
                "export_payload": {
                    "title": title,
                    "headers": normalized_headers,
                    "rows": normalized_rows,
                    "additional_sheets": table.get("additional_sheets") if isinstance(table.get("additional_sheets"), list) else [],
                },
                # Keep the table's typed source beside the file so later Premium
                # turns can continue editing/reusing the same table branch even
                # though file_only removes the visible TableBlock.
                "source_artifacts": [{
                    "type": "table", "title": title,
                    "headers": normalized_headers, "rows": normalized_rows,
                    "additional_sheets": table.get("additional_sheets") if isinstance(table.get("additional_sheets"), list) else [],
                }],
            },
        })
        existing_file_names.add(filename.casefold())

    # Code requested as a file must be a real downloadable source file, not only
    # an inline CodeBlock. Preserve the requested language and choose a safe,
    # conventional extension without changing the source text.
    code_blocks = [
        block for block in blocks
        if str(block.get("type") or block.get("artifact_type") or "").strip().lower() == "code"
    ]
    for code_block in code_blocks:
        code_payload = block_payload(code_block)
        code_text = next((str(code_payload.get(key) or "") for key in ("code", "source_code", "source", "content", "text")
                          if str(code_payload.get(key) or "").strip()), "")
        if not code_text:
            continue
        language_key = str(code_payload.get("language") or code_block.get("language") or "text").strip().lower()
        extensions = {
            "python": (".py", "text/x-python"), "py": (".py", "text/x-python"),
            "javascript": (".js", "text/javascript"), "js": (".js", "text/javascript"),
            "typescript": (".ts", "text/typescript"), "ts": (".ts", "text/typescript"),
            "tsx": (".tsx", "text/typescript"), "jsx": (".jsx", "text/javascript"),
            "json": (".json", "application/json"), "html": (".html", "text/html"),
            "css": (".css", "text/css"), "sql": (".sql", "application/sql"),
            "bash": (".sh", "text/x-shellscript"), "shell": (".sh", "text/x-shellscript"),
            "yaml": (".yml", "application/yaml"), "yml": (".yml", "application/yaml"),
            "xml": (".xml", "application/xml"), "markdown": (".md", "text/markdown"),
        }
        extension, mime_type = extensions.get(language_key, (".txt", "text/plain; charset=utf-8"))
        preferred_name = str(code_payload.get("filename") or code_block.get("filename") or "").strip()
        safe_name = re.sub(r"[^\w.-]+", "_", preferred_name, flags=re.UNICODE).strip("._")[:90]
        filename = safe_name or f"april_code{extension}"
        if not filename.lower().endswith(extension):
            filename = re.sub(r"\.[A-Za-z0-9]{1,8}$", "", filename) + extension
        if filename.casefold() in existing_file_names:
            continue
        file_blocks.append({
            "type": "file", "artifact_type": "file", "renderer": RENDERER, "viewer": RENDERER,
            "source_room": ROOM_ID,
            "payload": {
                "title": str(code_payload.get("title") or "Code file")[:120],
                "filename": filename, "mime_type": mime_type,
                "content": code_text, "source": "code_block_export", "description": "",
                "source_artifacts": [{
                    "type": "code", "language": language_key,
                    "filename": filename, "code": code_text,
                }],
            },
        })
        existing_file_names.add(filename.casefold())

    # When the user explicitly asks for a long answer as a file, create a Markdown
    # document from the complete assistant text. Tables and code are handled by
    # their typed exporters above, so they are not flattened into a text document.
    if not table_blocks and not code_blocks and not any(
        str(block.get("type") or block.get("artifact_type") or "").strip().lower() == "file"
        and any(str((block.get("payload") or {}).get(key) or "").strip() for key in ("content", "text", "code"))
        for block in blocks
    ):
        text_candidates: list[str] = []
        for text_block in blocks:
            if str(text_block.get("type") or text_block.get("artifact_type") or "").strip().lower() not in {"text", "markdown", "message", "message_text", "answer"}:
                continue
            text_payload = block_payload(text_block)
            candidate = next((str(text_payload.get(key) or "") for key in ("content", "markdown", "text", "answer")
                              if str(text_payload.get(key) or "").strip()), "")
            if candidate.strip():
                text_candidates.append(candidate)
        long_text = max(text_candidates, key=len) if text_candidates else ""
        if len(long_text.strip()) >= 500:
            filename = "april_answer.md"
            if filename.casefold() not in existing_file_names:
                file_blocks.append({
                    "type": "file", "artifact_type": "file", "renderer": RENDERER, "viewer": RENDERER,
                    "source_room": ROOM_ID,
                    "payload": {
                        "title": "April answer", "filename": filename,
                        "mime_type": "text/markdown; charset=utf-8",
                        "content": long_text, "source": "long_text_export", "description": "",
                        "source_artifacts": [{
                            "type": "copy", "filename": filename,
                            "content": long_text, "text": long_text,
                        }],
                    },
                })
                existing_file_names.add(filename.casefold())

    # Existing File blocks may already contain the bytes inline or a saved ref.
    for block in blocks:
        block_type = str(block.get("type") or block.get("artifact_type") or "").lower()
        if block_type not in {"file", "document", "file_card", "text_file", "code_file"}:
            continue
        payload = block_payload(block)
        filename = str(payload.get("filename") or payload.get("name") or "").strip()
        if isinstance(payload.get("asset_ref"), dict) or isinstance(payload.get("export_payload"), dict) or any(
            str(payload.get(key) or "").strip() for key in ("content", "text", "code", "data_uri", "file_data_uri", "download_url", "file_url")
        ):
            block["type"] = "file"
            block["artifact_type"] = "file"
            block["renderer"] = RENDERER
            block["viewer"] = RENDERER
            block.setdefault("source_room", ROOM_ID)

    blocks.extend(file_blocks)
    def has_downloadable_source(block: dict[str, Any]) -> bool:
        payload = block_payload(block)
        asset_ref = payload.get("asset_ref") if isinstance(payload.get("asset_ref"), dict) else {}
        if asset_ref.get("message_id") and re.fullmatch(r"[a-f0-9]{64}", str(asset_ref.get("sha256") or ""), re.I):
            return True
        export = payload.get("export_payload") if isinstance(payload.get("export_payload"), dict) else {}
        headers = export.get("headers") or export.get("columns")
        rows = export.get("rows") or export.get("data")
        if isinstance(headers, list) and headers and isinstance(rows, list) and rows:
            return True
        if any(str(payload.get(key) or "").strip() for key in ("content", "text", "code")):
            return True
        if str(payload.get("data_uri") or payload.get("file_data_uri") or "").startswith("data:"):
            return True
        return bool(re.match(r"^https://", str(payload.get("download_url") or payload.get("file_url") or ""), re.I))

    # Empty FileDeliveryBlock shells can coexist with a concrete artifact after
    # provider restoration (the mobile UI then displays a second, blank card).
    # Keep only file blocks that carry bytes, an authenticated asset reference,
    # an XLSX export payload, or a validated download URL.
    blocks = [
        block for block in blocks
        if str(block.get("type") or block.get("artifact_type") or "").lower() != "file"
        or has_downloadable_source(block)
    ]
    delivered_file_blocks = [
        block for block in blocks
        if str(block.get("type") or block.get("artifact_type") or "").lower() == "file"
        and has_downloadable_source(block)
    ]
    if str(file_delivery_mode or "").lower() == "file_only" and delivered_file_blocks:
        # Preserve the file's source in its own payload; do not duplicate huge
        # code/table data in the visible chat when the user explicitly asked for
        # a file only. Images and diagrams remain independent visual artifacts.
        blocks = [block for block in blocks if str(block.get("type") or block.get("artifact_type") or "").lower() not in {"code", "table"}]
        localized = {
            "ru": "Файл подготовлен.", "ua": "Файл підготовлено.", "uk": "Файл підготовлено.",
            "en": "The file is ready.", "fr": "Le fichier est prêt.", "de": "Die Datei ist fertig.",
            "es": "El archivo está listo.", "it": "Il file è pronto.", "pl": "Plik jest gotowy.",
            "pt": "O arquivo está pronto.", "nl": "Het bestand is klaar.",
        }
        notice = localized.get(str(language or "en").lower().split("-")[0], localized["en"])
        blocks = [block for block in blocks if str(block.get("type") or block.get("artifact_type") or "").lower() not in {"text", "markdown", "message", "message_text", "answer"}]
        blocks.insert(0, {"type": "text", "artifact_type": "text", "content": notice,
                          "renderer": "MessageTextBlock", "viewer": "MessageTextBlock"})
    return blocks, delivered_file_blocks
