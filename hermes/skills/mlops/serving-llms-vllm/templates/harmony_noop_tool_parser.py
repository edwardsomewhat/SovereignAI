# SPDX-License-Identifier: Apache-2.0
"""
No-op tool parser for GPT-OSS Harmony format.

GPT-OSS uses the Harmony response format. vLLM's harmony_utils.py handles
tool rendering (TypeScript declarations in developer message) and parsing
(<|channel|>commentary function calls) natively.

This parser exists only to satisfy the --tool-call-parser requirement
when --enable-auto-tool-choice is set. It does not interfere with
harmony_utils.py — all tool work happens at the chat template level.

Usage:
    --tool-call-parser harmony_noop
    --tool-parser-plugin /patches/harmony_noop_tool_parser.py

NOTE: This is a partial fix. GPT-OSS still may not reliably emit tool
calls through the standard vLLM pipeline because Harmony routes tools
through channel output. For agentic tool-calling, prefer Nemotron or Qwen.
"""

from collections.abc import Sequence

from vllm.entrypoints.openai.chat_completion.protocol import ChatCompletionRequest
from vllm.entrypoints.openai.engine.protocol import (
    DeltaMessage,
    ExtractedToolCallInformation,
)
from vllm.entrypoints.openai.responses.protocol import ResponsesRequest
from vllm.logger import init_logger
from vllm.tokenizers import TokenizerLike
from vllm.tool_parsers.abstract_tool_parser import Tool, ToolParser
from vllm.tool_parsers import ToolParserManager

logger = init_logger(__name__)


@ToolParserManager.register_module("harmony_noop")
class HarmonyNoopToolParser(ToolParser):
    """
    No-op tool parser for GPT-OSS Harmony format.

    Harmony handles tool rendering and parsing natively via
    vllm.entrypoints.openai.parser.harmony_utils. This parser
    passes through without modification.
    """

    supports_required_and_named: bool = True

    def __init__(self, tokenizer: TokenizerLike, tools: list[Tool] | None = None):
        super().__init__(tokenizer, tools)
        logger.info(
            "HarmonyNoopToolParser: initialized with %d tools",
            len(self.tools) if tools else 0,
        )

    def adjust_request(
        self, request: ChatCompletionRequest | ResponsesRequest
    ) -> ChatCompletionRequest | ResponsesRequest:
        return request

    def extract_tool_calls(
        self,
        model_output: str,
        request: ChatCompletionRequest,
        token_ids: Sequence[int] | None = None,
    ) -> ExtractedToolCallInformation:
        # harmony_utils.parse_output_into_messages handles extraction
        # upstream of this method in the response pipeline.
        return ExtractedToolCallInformation(
            tools_called=False,
            tool_calls=[],
            content=model_output,
        )

    def extract_tool_calls_streaming(
        self,
        previous_text: str,
        current_text: str,
        delta_text: str,
        request: ChatCompletionRequest,
        token_ids: Sequence[int] | None = None,
    ) -> DeltaMessage:
        return DeltaMessage(content=delta_text) if delta_text else DeltaMessage()
