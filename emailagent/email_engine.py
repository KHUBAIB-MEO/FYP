"""
Email Generation Engine
Handles prompt engineering, subject generation, personalization, and tone control.
"""
from shared.ollama_client import OllamaClient
from shared.memory_manager import MemoryManager
from shared.settings import EMAIL_LENGTHS

class EmailEngine:
    """
    Core engine for generating emails using LLM.
    Features: tone control, auto-subject, personalization, context memory, length control.
    """

    def __init__(self, model=None):
        self.client = OllamaClient(model=model)
        self.memory = MemoryManager()

    def set_model(self, model_name):
        """Change the active LLM model"""
        self.client.set_model(model_name)

    def _build_system_prompt(self, tone, length):
        """Build system prompt based on tone and length"""
        length_desc = EMAIL_LENGTHS.get(length, EMAIL_LENGTHS["Medium"])

        tone_instructions = {
            "Professional": "Use formal business language, clear structure, and professional courtesy.",
            "Funny": "Use humor, witty remarks, and light-hearted tone while staying appropriate.",
            "Emotional": "Use heartfelt, sincere language that connects on a human level.",
            "Persuasive": "Use compelling arguments, benefits-focused language, and clear calls-to-action.",
            "Casual": "Use friendly, conversational language like talking to a friend."
        }

        tone_desc = tone_instructions.get(tone, tone_instructions["Professional"])

        return f"""You are an expert email copywriter with years of experience.

RULES:
- Tone: {tone}. {tone_desc}
- Length: {length_desc}
- Always generate an optimized subject line on the first line prefixed with SUBJECT: 
- Personalize using recipient name when provided
- Use proper greeting and professional sign-off
- Be concise, engaging, and relevant
- Format: Plain text, no markdown except line breaks"""

    def generate_email(self, topic, tone, length, recipient_name="", 
                      context="", signature="", previous_emails=None):
        """
        Generate a complete email with subject line.

        Args:
            topic: What the email is about
            tone: Selected tone from TONES list
            length: Short/Medium/Long
            recipient_name: Name for personalization
            context: Additional context/instructions
            signature: Footer signature to append
            previous_emails: Previous email versions for context memory

        Returns:
            dict with subject, body, tone, length, full_text
        """
        system = self._build_system_prompt(tone, length)

        prompt = f"""Write an email with the following details:

TOPIC: {topic}
RECIPIENT: {recipient_name if recipient_name else "Valued Contact"}
TONE: {tone}
LENGTH: {length}
"""

        if context:
            prompt += f"\nADDITIONAL CONTEXT: {context}\n"

        if previous_emails:
            prompt += f"\nPREVIOUS VERSION (for reference, write differently):\n{previous_emails}\n"

        prompt += """\nOUTPUT FORMAT (strictly follow this):
SUBJECT: <compelling subject line here>

<email body with greeting, content, and closing>

<signature placeholder>"""

        response = self.client.generate(prompt, system=system, temperature=0.8)

        # Parse subject and body
        subject = "No Subject"
        body = response

        if "SUBJECT:" in response.upper():
            lines = response.split("\n", 1)
            first_line = lines[0].strip()
            if "SUBJECT:" in first_line.upper():
                subject = first_line.split(":", 1)[1].strip()
                if len(lines) > 1:
                    body = lines[1].strip()

        # Append signature if provided
        full_body = body
        if signature:
            full_body += f"\n\n---\n{signature}"

        # Store in memory
        email_id = f"email_{hash(topic + tone + length + recipient_name) % 100000}"
        self.memory.add_context(email_id, {
            "topic": topic,
            "tone": tone,
            "length": length,
            "recipient": recipient_name,
            "subject": subject,
            "body": body
        })

        return {
            "id": email_id,
            "subject": subject,
            "body": body,
            "full_text": full_body,
            "tone": tone,
            "length": length,
            "recipient": recipient_name,
            "topic": topic
        }

    def regenerate_email(self, original_data, topic, tone, length, 
                         recipient_name="", context="", signature=""):
        """
        Regenerate an email with fresh wording while keeping same intent.
        Uses previous version as context but instructs model to be different.
        """
        previous = original_data.get("body", "")

        system = self._build_system_prompt(tone, length)
        system += "\n\nIMPORTANT: This is a REGENERATION. Use completely different wording and structure while keeping the same message intent. Do NOT copy phrases from the previous version."

        prompt = f"""Regenerate this email with completely fresh wording:

TOPIC: {topic}
RECIPIENT: {recipient_name if recipient_name else "Valued Contact"}
TONE: {tone}
LENGTH: {length}
"""

        if context:
            prompt += f"\nADDITIONAL CONTEXT: {context}\n"

        prompt += f"\nPREVIOUS VERSION (DO NOT COPY - write differently):\n{previous}\n"
        prompt += """\nOUTPUT FORMAT:
SUBJECT: <new compelling subject line>

<completely rewritten email body>

<signature placeholder>"""

        response = self.client.generate(prompt, system=system, temperature=0.9)

        subject = "No Subject"
        body = response

        if "SUBJECT:" in response.upper():
            lines = response.split("\n", 1)
            first_line = lines[0].strip()
            if "SUBJECT:" in first_line.upper():
                subject = first_line.split(":", 1)[1].strip()
                if len(lines) > 1:
                    body = lines[1].strip()

        full_body = body
        if signature:
            full_body += f"\n\n---\n{signature}"

        return {
            "id": original_data.get("id", "") + "_regen",
            "subject": subject,
            "body": body,
            "full_text": full_body,
            "tone": tone,
            "length": length,
            "recipient": recipient_name,
            "topic": topic
        }

    def get_memory_context(self, email_id=None):
        """Retrieve stored email context from memory"""
        if email_id:
            return self.memory.get_context(email_id)
        return self.memory.get_all_contexts()
