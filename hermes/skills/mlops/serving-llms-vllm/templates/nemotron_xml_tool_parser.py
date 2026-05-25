# SPDX-License-Identifier: Apache-2.0
"""
Tool parser for Nemotron-3 Nano 30B-A3B (V3) XML tool call format.

Nemotron outputs tool calls in XML format:
    <tool_call>
    <function=calculator>
    <parameter=expr>
    2+2
    </parameter>
    </function>
    </tool_call>

vLLM's built-in hermes parser expects JSON between <tool_call> tags,
so it silently fails on this XML format. This plugin handles the Nemotron
XML format correctly.

Usage:
    --tool-call-parser nemotron_xml
    --tool-parser-plugin /patches/nemotron_xml_tool_parser.py

Register under 'nemotron_xml' via ToolParserManager.register_module.
"""

import json
import re
from collections.abc import Sequence

from vllm.entrypoints.chat_utils import make_tool_call_id
from vllm.entrypoints.openai.chat_completion.protocol import ChatCompletionRequest
from vllm.entrypoints.openai.engine.protocol import (
    DeltaFunctionCall,
    DeltaMessage,
    DeltaToolCall,
    ExtractedToolCallInformation,
    FunctionCall,
    ToolCall,
)
from vllm.entrypoints.openai.responses.protocol import ResponsesRequest
from vllm.logger import init_logger
from vllm.tokenizers import TokenizerLike
from vllm.tool_parsers.abstract_tool_parser import Tool, ToolParser
from vllm.tool_parsers import ToolParserManager

logger = init_logger(__name__)


@ToolParserManager.register_module("nemotron_xml")
class NemotronXMLToolParser(ToolParser):
    """
    Parser for Nemotron-3 Nano 30B-A3B XML tool call format.
    """

    # Nemotron XML is not standard JSON — fall back to extract_tool_calls
    supports_required_and_named: bool = False

    tool_call_start_token: str = "<tool_call>"
    tool_call_end_token: str = "</tool_call>"
    function_start_re = re.compile(r"<function=([^>]+)>")
    parameter_start_re = re.compile(r"<parameter=([^>]+)>")

    def __init__(self, tokenizer: TokenizerLike, tools: list[Tool] | None = None):
        super().__init__(tokenizer, tools)
        self._sent_content_idx: int = 0

    def adjust_request(
        self, request: ChatCompletionRequest | ResponsesRequest
    ) -> ChatCompletionRequest | ResponsesRequest:
        request = super().adjust_request(request)
        if request.tools and request.tool_choice != "none":
            request.skip_special_tokens = False
        return request

    # ── XML parsing helpers ──────────────────────────────────────────

    @staticmethod
    def _parse_function_tag(block: str) -> tuple[str, dict] | None:
        """Parse <function=name>...<parameter=key>val</parameter>...</function>"""
        m = NemotronXMLToolParser.function_start_re.search(block)
        if not m:
            return None
        func_name = m.group(1).strip()

        arguments = {}
        end_tag = "</parameter>"
        for pm in NemotronXMLToolParser.parameter_start_re.finditer(block):
            param_name = pm.group(1).strip()
            start = pm.end()
            end = block.find(end_tag, start)
            if end == -1:
                continue
            value = block[start:end].strip()
            arguments[param_name] = value

        return func_name, arguments

    # ── Non-streaming extraction ─────────────────────────────────────

    def extract_tool_calls(
        self,
        model_output: str,
        request: ChatCompletionRequest,
        token_ids: Sequence[int] | None = None,
    ) -> ExtractedToolCallInformation:
        if self.tool_call_start_token not in model_output:
            return ExtractedToolCallInformation(
                tools_called=False, tool_calls=[], content=model_output
            )

        try:
            tc_re = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)
            matches = list(tc_re.finditer(model_output))

            if not matches:
                return ExtractedToolCallInformation(
                    tools_called=False, tool_calls=[], content=model_output
                )

            tool_calls = []
            last_end = 0
            content_parts = []

            for m in matches:
                before = model_output[last_end : m.start()]
                if before.strip():
                    content_parts.append(before)

                block = m.group(1)
                parsed = self._parse_function_tag(block)
                if parsed:
                    func_name, arguments = parsed
                    tool_calls.append(
                        ToolCall(
                            type="function",
                            id=make_tool_call_id(),
                            function=FunctionCall(
                                name=func_name,
                                arguments=json.dumps(arguments),
                            ),
                        )
                    )

                last_end = m.end()

            after = model_output[last_end:]
            if after.strip():
                content_parts.append(after)

            content = "\n".join(p for p in content_parts if p).strip() or None

            if tool_calls:
                return ExtractedToolCallInformation(
                    tools_called=True,
                    tool_calls=tool_calls,
                    content=content,
                )

            return ExtractedToolCallInformation(
                tools_called=False, tool_calls=[], content=model_output
            )

        except Exception as e:
            logger.error("NemotronXMLToolParser: failed to parse: %s", e)
            return ExtractedToolCallInformation(
                tools_called=False, tool_calls=[], content=model_output
            )

    # ── Streaming extraction ─────────────────────────────────────────

    def extract_tool_calls_streaming(
        self,
        previous_text: str,
        current_text: str,
        delta_text: str,
        request: ChatCompletionRequest,
        token_ids: Sequence[int] | None = None,
    ) -> DeltaMessage:
        extracted = self.extract_tool_calls(current_text, request)

        if not extracted.tools_called:
            new_content = current_text[self._sent_content_idx :]
            self._sent_content_idx = len(current_text)
            return DeltaMessage(content=new_content) if new_content else DeltaMessage()

        delta = DeltaMessage(tool_calls=[])
        for i, tc in enumerate(extracted.tool_calls):
            delta.tool_calls.append(
                DeltaToolCall(
                    index=i,
                    id=tc.id,
                    type="function",
                    function=DeltaFunctionCall(
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                    ),
                )
            )

        if extracted.content:
            new_content = extracted.content[self._sent_content_idx :]
            if new_content:
                delta.content = new_content

        self._sent_content_idx = len(current_text)
        return delta
