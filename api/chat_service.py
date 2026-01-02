# -*- coding: utf-8 -*-
"""AA Chat Service - Handles conversation with AA system.

This service provides:
1. LLM-based conversation handling
2. Requirement extraction from conversation
3. Delivery standard extraction
4. File attachment handling for context
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class FileAttachment:
    """File attached to a message."""
    id: int
    filename: str
    file_type: str
    content: str | None = None  # Text content for text files
    summary: str | None = None  # AI-generated summary for complex files

    def to_context_string(self) -> str:
        """Convert file attachment to a context string for LLM."""
        parts = [f"[文件: {self.filename}]"]
        if self.content:
            # Truncate very long content
            content = self.content[:5000] if len(self.content) > 5000 else self.content
            parts.append(f"内容:\n```\n{content}\n```")
        elif self.summary:
            parts.append(f"摘要: {self.summary}")
        else:
            parts.append(f"(类型: {self.file_type})")
        return "\n".join(parts)


@dataclass
class ExtractedRequirement:
    """Extracted requirement from conversation."""
    content: str
    type: str = 'requirement'  # 'requirement' or 'delivery_standard'
    delivery_standards: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)  # Referenced file names


@dataclass
class ChatResponse:
    """Response from AA chat."""
    content: str
    requirements: list[ExtractedRequirement] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    referenced_files: list[str] = field(default_factory=list)  # Files mentioned in response


class AAChatService:
    """Service for handling AA conversations."""

    # System prompt for AA assistant
    SYSTEM_PROMPT = """你是 HiveCore 的 AA (Assistant Agent) 智能助手，专门负责需求分析和项目规划。

## 你的核心能力

1. **需求理解与澄清**
   - 深入分析用户描述，识别核心需求与潜在需求
   - 对模糊或不完整的需求，主动提出针对性问题
   - 识别技术约束、业务规则和非功能性需求

2. **需求拆解与结构化**
   - 将复杂需求拆解为独立、可执行的子任务
   - 识别任务间的依赖关系和优先级
   - 评估需求的技术可行性

3. **交付标准定义**
   - 为每个需求定义具体、可验证的验收标准
   - 考虑功能、性能、安全性、用户体验等维度
   - 确保标准可测量、可自动化验证

4. **文件分析**（如果用户上传了文件）
   - 分析设计稿、原型图、文档等附件
   - 从文件中提取需求和约束条件
   - 结合文件内容完善需求描述

## 输出格式【重要】

每次回复 **必须** 包含两部分：

### 第一部分：对话内容
用清晰、专业的语言与用户沟通，包括：
- 对需求的理解和确认
- 需要澄清的问题
- 建议和风险提示

### 第二部分：需求 JSON【必须输出】
在回复最后，**必须** 用 JSON 格式输出从用户消息中识别的需求。

**关键规则**：
- 只要用户描述了任何想做的事情、目标或期望，就应该提取为需求
- 即使需求描述不完整或需要澄清，也要先记录下来
- 每次回复都必须包含 JSON 块，即使是空的 requirements 数组

```json
{
  "requirements": [
    {
      "content": "需求的完整描述（基于用户原始表述）",
      "type": "requirement",
      "delivery_standards": [
        "具体的交付标准1",
        "具体的交付标准2"
      ]
    }
  ]
}
```

示例 - 用户说"我要一个登录功能"：
```json
{
  "requirements": [
    {
      "content": "实现用户登录功能",
      "type": "requirement",
      "delivery_standards": ["用户可以输入用户名密码登录", "登录成功后跳转到首页"]
    }
  ]
}
```

## 对话原则

- 专业严谨，但保持友好
- 主动引导，帮助用户完善需求
- 适时总结，确认理解是否正确
- 对技术方案给出专业建议"""

    def __init__(self):
        """Initialize the chat service."""
        self._client = None
        self._provider = None
        self._model = None

    def _get_llm(self):
        """Lazy-load LLM client using OpenAI-compatible API."""
        if self._client is not None:
            return self._client, self._provider

        import os
        try:
            from openai import OpenAI

            # Try Zhipu first
            zhipu_key = os.environ.get('ZHIPU_API_KEY')
            zhipu_base = os.environ.get('ZHIPU_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4')
            zhipu_model = os.environ.get('ZHIPU_MODEL', 'glm-4-plus')

            if zhipu_key:
                self._client = OpenAI(api_key=zhipu_key, base_url=zhipu_base)
                self._provider = 'zhipu'
                self._model = zhipu_model
                logger.info(f"LLM initialized: zhipu ({zhipu_model})")
                return self._client, self._provider

            # Try SiliconFlow
            sf_key = os.environ.get('SILICONFLOW_API_KEY')
            sf_base = os.environ.get('SILICONFLOW_BASE_URL', 'https://api.siliconflow.cn/v1')
            sf_model = os.environ.get('SILICONFLOW_MODEL', 'Qwen/Qwen2.5-72B-Instruct')

            if sf_key:
                self._client = OpenAI(api_key=sf_key, base_url=sf_base)
                self._provider = 'siliconflow'
                self._model = sf_model
                logger.info(f"LLM initialized: siliconflow ({sf_model})")
                return self._client, self._provider

            logger.warning("No LLM API key found, using mock")
            return None, 'mock'

        except ImportError:
            logger.warning("OpenAI package not available, using mock LLM")
            return None, 'mock'
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            return None, 'error'

    def _build_messages(
        self,
        conversation_history: list[dict[str, str]],
        user_message: str,
        attachments: list[FileAttachment] | None = None,
    ) -> list[dict[str, str]]:
        """Build messages list for LLM call.

        Args:
            conversation_history: Previous messages
            user_message: The new user message
            attachments: Optional file attachments for the current message
        """
        messages = [{'role': 'system', 'content': self.SYSTEM_PROMPT}]

        # Add conversation history
        for msg in conversation_history:
            messages.append({
                'role': 'user' if msg['type'] == 'user' else 'assistant',
                'content': msg['content'],
            })

        # Build user message with attachments
        if attachments:
            attachment_context = "\n\n".join(
                f"### 附件 {i+1}\n{att.to_context_string()}"
                for i, att in enumerate(attachments)
            )
            full_message = f"""## 用户消息
{user_message}

## 附带文件
{attachment_context}"""
        else:
            full_message = user_message

        messages.append({'role': 'user', 'content': full_message})

        return messages

    def _parse_response(self, response_text: str) -> ChatResponse:
        """Parse LLM response to extract requirements."""
        requirements = []
        import re

        # Log raw response for debugging
        logger.info("LLM raw response length: %d chars", len(response_text))
        logger.debug("LLM raw response: %s", response_text[:500])

        # Try multiple patterns to extract JSON
        json_data = None
        clean_content = response_text

        # Pattern 1: ```json ... ``` (standard markdown)
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            try:
                json_data = json.loads(json_match.group(1))
                clean_content = response_text[:json_match.start()].strip()
                logger.info("Extracted JSON using pattern 1 (```json```)")
            except json.JSONDecodeError as e:
                logger.warning("Pattern 1 JSON parse failed: %s", e)

        # Pattern 2: ``` ... ``` (generic code block)
        if json_data is None:
            code_match = re.search(r'```\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if code_match:
                try:
                    json_data = json.loads(code_match.group(1))
                    clean_content = response_text[:code_match.start()].strip()
                    logger.info("Extracted JSON using pattern 2 (generic code block)")
                except json.JSONDecodeError as e:
                    logger.warning("Pattern 2 JSON parse failed: %s", e)

        # Pattern 3: Raw JSON object at end of response
        if json_data is None:
            raw_match = re.search(r'(\{[^{}]*"requirements"\s*:\s*\[.*?\]\s*\})', response_text, re.DOTALL)
            if raw_match:
                try:
                    json_data = json.loads(raw_match.group(1))
                    clean_content = response_text[:raw_match.start()].strip()
                    logger.info("Extracted JSON using pattern 3 (raw JSON)")
                except json.JSONDecodeError as e:
                    logger.warning("Pattern 3 JSON parse failed: %s", e)

        # Extract requirements from parsed JSON
        if json_data:
            for req_data in json_data.get('requirements', []):
                if req_data.get('content'):
                    requirements.append(ExtractedRequirement(
                        content=req_data.get('content', ''),
                        type=req_data.get('type', 'requirement'),
                        delivery_standards=req_data.get('delivery_standards', []),
                    ))
            logger.info("Extracted %d requirements from LLM response", len(requirements))
        else:
            logger.warning("No JSON found in LLM response, requirements will be empty")

        # Clean up internal markers that shouldn't be shown to users
        clean_content = re.sub(r'#{1,3}\s*第[一二]部分[：:]\s*对话内容\s*', '', clean_content)
        clean_content = re.sub(r'#{1,3}\s*第[一二]部分[：:]\s*需求\s*JSON.*', '', clean_content, flags=re.IGNORECASE)
        clean_content = re.sub(r'#{1,3}\s*对话内容\s*\n?', '', clean_content)
        clean_content = re.sub(r'#{1,3}\s*需求\s*JSON.*', '', clean_content, flags=re.IGNORECASE | re.DOTALL)
        clean_content = clean_content.strip()

        return ChatResponse(
            content=clean_content,
            requirements=requirements,
        )

    async def chat(
        self,
        conversation_history: list[dict[str, str]],
        user_message: str,
        attachments: list[FileAttachment] | None = None,
    ) -> ChatResponse:
        """Process a chat message and return AA response.

        Args:
            conversation_history: Previous messages in format [{'type': 'user'|'assistant', 'content': str}]
            user_message: The new user message
            attachments: Optional file attachments for context

        Returns:
            ChatResponse with AA's reply and extracted requirements
        """
        client, provider = self._get_llm()

        if client is None:
            # Mock response for testing
            return self._mock_response(user_message, attachments)

        messages = self._build_messages(conversation_history, user_message, attachments)

        try:
            # Call LLM using OpenAI-compatible API
            response = client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
            )
            response_text = response.choices[0].message.content or ''

            return self._parse_response(response_text)

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return ChatResponse(
                content=f"抱歉，处理您的请求时出现了问题。请稍后重试。\n\n错误详情: {str(e)}",
                metadata={'error': str(e)},
            )

    def chat_sync(
        self,
        conversation_history: list[dict[str, str]],
        user_message: str,
        attachments: list[FileAttachment] | None = None,
    ) -> ChatResponse:
        """Synchronous version of chat."""
        import asyncio
        return asyncio.run(self.chat(conversation_history, user_message, attachments))

    def chat_stream(
        self,
        conversation_history: list[dict[str, str]],
        user_message: str,
        attachments: list[FileAttachment] | None = None,
    ):
        """Stream chat response token by token.

        Yields:
            dict with 'type' and 'content':
            - type='token': content is a text chunk
            - type='done': content is the full response for parsing
            - type='error': content is error message
        """
        import re

        client, provider = self._get_llm()

        if client is None:
            # Mock streaming for testing
            mock_resp = self._mock_response(user_message, attachments)
            # Simulate streaming by yielding chunks
            for char in mock_resp.content:
                yield {'type': 'token', 'content': char}
            yield {'type': 'done', 'content': mock_resp.content, 'requirements': [
                {'content': r.content, 'type': r.type, 'delivery_standards': r.delivery_standards}
                for r in mock_resp.requirements
            ]}
            return

        messages = self._build_messages(conversation_history, user_message, attachments)

        try:
            # Stream response using OpenAI-compatible API
            stream = client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                stream=True,
            )

            full_response = ""
            json_block_started = False
            requirements_array_started = False
            sent_requirement_count = 0

            # Fine-grained streaming state
            brace_count = 0  # Track nesting level within requirements array
            bracket_count = 0  # Track array nesting (for delivery_standards)
            in_string = False
            escape_next = False
            current_requirement_started = False  # Whether we've sent requirement_start for current object
            skip_current_token_processing = False

            def process_char_for_streaming(char: str):
                """Process a single character and yield streaming events."""
                nonlocal brace_count, bracket_count, in_string, escape_next
                nonlocal current_requirement_started, sent_requirement_count

                events = []

                # Handle escape sequences
                if escape_next:
                    escape_next = False
                    # Send the escaped char as part of requirement content
                    if current_requirement_started and brace_count >= 1:
                        events.append({'type': 'requirement_token', 'content': char, 'index': sent_requirement_count})
                    return events

                if char == '\\' and in_string:
                    escape_next = True
                    if current_requirement_started and brace_count >= 1:
                        events.append({'type': 'requirement_token', 'content': char, 'index': sent_requirement_count})
                    return events

                # Handle string boundaries
                if char == '"' and not escape_next:
                    in_string = not in_string
                    if current_requirement_started and brace_count >= 1:
                        events.append({'type': 'requirement_token', 'content': char, 'index': sent_requirement_count})
                    return events

                # Inside a string - stream content
                if in_string:
                    if current_requirement_started and brace_count >= 1:
                        events.append({'type': 'requirement_token', 'content': char, 'index': sent_requirement_count})
                    return events

                # Outside string - track structure
                if char == '{':
                    prev_brace_count = brace_count
                    brace_count += 1
                    # Entering a new requirement object (brace_count goes from 0 to 1)
                    if prev_brace_count == 0 and brace_count == 1:
                        current_requirement_started = True
                        events.append({'type': 'requirement_start', 'index': sent_requirement_count})
                    elif current_requirement_started:
                        events.append({'type': 'requirement_token', 'content': char, 'index': sent_requirement_count})
                elif char == '}':
                    brace_count -= 1
                    # Exiting a requirement object (brace_count goes from 1 to 0)
                    if brace_count == 0 and current_requirement_started:
                        events.append({'type': 'requirement_end', 'index': sent_requirement_count})
                        sent_requirement_count += 1
                        current_requirement_started = False
                    elif current_requirement_started:
                        events.append({'type': 'requirement_token', 'content': char, 'index': sent_requirement_count})
                elif char == '[':
                    bracket_count += 1
                    if current_requirement_started:
                        events.append({'type': 'requirement_token', 'content': char, 'index': sent_requirement_count})
                elif char == ']':
                    bracket_count -= 1
                    if current_requirement_started:
                        events.append({'type': 'requirement_token', 'content': char, 'index': sent_requirement_count})
                else:
                    # Regular character (comma, colon, whitespace, etc.)
                    if current_requirement_started and brace_count >= 1:
                        events.append({'type': 'requirement_token', 'content': char, 'index': sent_requirement_count})

                return events

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_response += token
                    yield {'type': 'token', 'content': token}

                    # Reset skip flag at the start of each token
                    skip_current_token_processing = False

                    # Real-time incremental JSON parsing
                    # Step 1: Detect JSON block start
                    if '```json' in full_response and not json_block_started:
                        json_block_started = True

                    # Step 2: Detect requirements array start
                    if json_block_started and not requirements_array_started:
                        if '"requirements"' in full_response and '[' in full_response[full_response.find('"requirements"'):]:
                            requirements_array_started = True
                            # Find where the array starts
                            req_pos = full_response.find('"requirements"')
                            array_start = full_response.find('[', req_pos)
                            if array_start != -1:
                                # Initialize state from content after the [
                                initial_content = full_response[array_start + 1:]
                                # Process the initial content to set up state correctly
                                for char in initial_content:
                                    for event in process_char_for_streaming(char):
                                        yield event
                                # Skip processing this token since we already processed it via full_response
                                skip_current_token_processing = True

                    # Step 3: Stream individual characters from the token
                    if requirements_array_started and not skip_current_token_processing:
                        for char in token:
                            for event in process_char_for_streaming(char):
                                yield event

            # Parse the complete response to extract requirements (fallback if not sent during stream)
            logger.info("Stream complete. Full response length: %d", len(full_response))
            parsed = self._parse_response(full_response)
            logger.info("Parsed requirements count: %d", len(parsed.requirements))

            # Clean the content for display (remove internal markers)
            clean_content = full_response
            clean_content = re.sub(r'#{1,3}\s*第[一二]部分[：:]\s*对话内容\s*', '', clean_content)
            clean_content = re.sub(r'#{1,3}\s*第[一二]部分[：:]\s*需求\s*JSON.*', '', clean_content, flags=re.IGNORECASE)
            clean_content = re.sub(r'#{1,3}\s*对话内容\s*\n?', '', clean_content)
            clean_content = re.sub(r'#{1,3}\s*需求\s*JSON.*', '', clean_content, flags=re.IGNORECASE | re.DOTALL)
            # Remove JSON code blocks
            clean_content = re.sub(r'```json\s*.*?\s*```', '', clean_content, flags=re.DOTALL)
            clean_content = re.sub(r'```\s*\{.*?\}\s*```', '', clean_content, flags=re.DOTALL)
            clean_content = clean_content.strip()

            # Only include requirements in done event if they weren't sent incrementally
            requirements_for_done = []
            if sent_requirement_count == 0:
                # No requirements were sent incrementally, include all in done event
                requirements_for_done = [
                    {'content': r.content, 'type': r.type, 'delivery_standards': r.delivery_standards}
                    for r in parsed.requirements
                ]

            yield {
                'type': 'done',
                'content': clean_content,
                'requirements': requirements_for_done
            }

        except Exception as e:
            logger.error(f"LLM stream failed: {e}")
            yield {'type': 'error', 'content': str(e)}

    def _mock_response(
        self,
        user_message: str,
        attachments: list[FileAttachment] | None = None,
    ) -> ChatResponse:
        """Generate mock response for testing."""
        # Simple mock that extracts some requirements
        preview = user_message[:100] + "..." if len(user_message) > 100 else user_message

        # Include attachment info in mock response
        attachment_info = ""
        if attachments:
            file_names = [att.filename for att in attachments]
            attachment_info = f"\n\n我注意到您上传了以下文件：\n- " + "\n- ".join(file_names)
            attachment_info += "\n\n我会参考这些文件来理解您的需求。"

        mock_content = f"""收到您的需求："{preview}"{attachment_info}

让我帮您整理一下：

1. 我理解您需要实现一个完整的解决方案
2. 我会帮您拆解具体的需求点
3. 每个需求都会有明确的交付标准

请问还有其他需要补充的吗？"""

        # Simple extraction for demo - keep full content
        requirements = []
        source_files = [att.filename for att in (attachments or [])]

        if len(user_message) > 20:
            requirements.append(ExtractedRequirement(
                content=user_message,  # Full content, no truncation
                type='requirement',
                delivery_standards=['完整实现功能', '通过基本测试', '有使用文档'],
                source_files=source_files,
            ))

        return ChatResponse(
            content=mock_content,
            requirements=requirements,
            metadata={'mock': True},
            referenced_files=source_files,
        )


class RequirementExtractor:
    """Extract and update requirements from conversation."""

    EXTRACTION_PROMPT = """请分析以下对话，提取所有的需求和交付标准。

## 对话内容：
{conversation}

## 输出格式

请以 JSON 格式输出：
```json
{{
  "requirements": [
    {{
      "content": "需求描述",
      "type": "requirement",
      "delivery_standards": ["交付标准1", "交付标准2"]
    }}
  ]
}}
```

只输出 JSON，不要其他内容。"""

    def __init__(self):
        """Initialize the extractor."""
        self._chat_service = AAChatService()

    def _format_conversation(self, messages: list[dict[str, str]]) -> str:
        """Format conversation for extraction."""
        lines = []
        for msg in messages:
            role = "用户" if msg['type'] == 'user' else "助手"
            lines.append(f"{role}: {msg['content']}")
        return "\n\n".join(lines)

    async def extract(
        self,
        messages: list[dict[str, str]],
    ) -> list[ExtractedRequirement]:
        """Extract all requirements from a conversation.

        Args:
            messages: All messages in format [{'type': 'user'|'assistant', 'content': str}]

        Returns:
            List of extracted requirements
        """
        if not messages:
            return []

        conversation_text = self._format_conversation(messages)
        prompt = self.EXTRACTION_PROMPT.format(conversation=conversation_text)

        llm, provider = self._chat_service._get_llm()

        if llm is None:
            # Mock extraction
            return self._mock_extract(messages)

        try:
            response = await llm.async_call([
                {'role': 'system', 'content': '你是需求分析专家，擅长从对话中提取结构化需求。'},
                {'role': 'user', 'content': prompt},
            ])
            response_text = response.get('content', '') if isinstance(response, dict) else str(response)

            # Parse JSON response
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                data = json.loads(response_text)

            requirements = []
            for req_data in data.get('requirements', []):
                requirements.append(ExtractedRequirement(
                    content=req_data.get('content', ''),
                    type=req_data.get('type', 'requirement'),
                    delivery_standards=req_data.get('delivery_standards', []),
                ))
            return requirements

        except Exception as e:
            logger.error(f"Requirement extraction failed: {e}")
            return []

    def extract_sync(self, messages: list[dict[str, str]]) -> list[ExtractedRequirement]:
        """Synchronous version of extract."""
        import asyncio
        return asyncio.run(self.extract(messages))

    def _mock_extract(self, messages: list[dict[str, str]]) -> list[ExtractedRequirement]:
        """Mock extraction for testing."""
        # Find user messages and create requirements from them
        requirements = []
        for msg in messages:
            if msg['type'] == 'user' and len(msg['content']) > 10:
                requirements.append(ExtractedRequirement(
                    content=msg['content'],  # Full content, no truncation
                    type='requirement',
                    delivery_standards=['完整实现功能', '通过测试验证'],
                ))
        return requirements


# Singleton instances
_chat_service = None
_extractor = None


def get_chat_service() -> AAChatService:
    """Get the singleton chat service instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = AAChatService()
    return _chat_service


def get_extractor() -> RequirementExtractor:
    """Get the singleton extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = RequirementExtractor()
    return _extractor
