"""
Content Scripting Engine - AI-powered content generation
Handles blogs, social media, ad copy, scripts, and more
"""
from shared.ollama_client import OllamaClient
from shared.memory_manager import MemoryManager
from shared.settings import CONTENT_LENGTHS

class ContentEngine:
    """
    Core engine for generating various types of content using LLM.
    Features: tone control, auto-formatting, length control, context memory.
    """

    def __init__(self, model=None):
        self.client = OllamaClient(model=model)
        self.memory = MemoryManager()

    def set_model(self, model_name):
        """Change the active LLM model"""
        self.client.set_model(model_name)

    def _build_system_prompt(self, tone, content_type, length):
        """Build system prompt based on tone, type and length"""
        length_desc = CONTENT_LENGTHS.get(length, CONTENT_LENGTHS["Medium"])

        tone_instructions = {
            "Professional": "Use formal, polished language suitable for business and corporate contexts.",
            "Casual": "Use friendly, conversational language like talking to a friend.",
            "Creative": "Use imaginative, vivid, and engaging language with storytelling elements.",
            "Persuasive": "Use compelling arguments, benefits-focused language, and clear calls-to-action.",
            "Technical": "Use precise, detailed language with industry terminology and structured explanations.",
            "Humorous": "Use witty, light-hearted language with appropriate humor and personality."
        }

        type_instructions = {
            "Blog Post": "Write a well-structured blog post with engaging intro, body paragraphs, and conclusion. Use headers if appropriate.",
            "Social Media": "Write short, punchy content optimized for social media. Use hashtags and emojis where appropriate. Include hooks.",
            "Ad Copy": "Write compelling advertising copy focused on benefits, urgency, and call-to-action. Keep it persuasive and concise.",
            "Video Script": "Write a video script with clear sections: Hook, Introduction, Main Content, and Call-to-Action. Use conversational tone.",
            "Product Description": "Write detailed product descriptions highlighting features, benefits, and unique selling points.",
            "Email Newsletter": "Write an engaging newsletter with a catchy subject line, valuable content, and clear call-to-action.",
            "General Content": "Write high-quality content that is clear, engaging, and well-structured for the given topic."
        }

        tone_desc = tone_instructions.get(tone, tone_instructions["Professional"])
        type_desc = type_instructions.get(content_type, type_instructions["General Content"])

        return f"""You are an expert content writer and copywriter with years of experience.

RULES:
- Content Type: {content_type}. {type_desc}
- Tone: {tone}. {tone_desc}
- Length: {length_desc}
- Format: Plain text with clear structure
- Be original, engaging, and relevant to the topic
- Use proper formatting with line breaks for readability
- No markdown formatting (use plain text with line breaks only)"""

    def generate_content(self, topic, content_type, tone, length, 
                        context="", keywords="", previous_content=None):
        """
        Generate content based on user requirements.

        Args:
            topic: What the content should be about
            content_type: Blog Post, Social Media, Ad Copy, etc.
            tone: Selected tone
            length: Short/Medium/Long/Extra Long
            context: Additional instructions/context
            keywords: SEO keywords to include (comma-separated)
            previous_content: Previous version for regeneration

        Returns:
            dict with title, content, type, tone, length, topic
        """
        system = self._build_system_prompt(tone, content_type, length)

        prompt = f"""Write {content_type.lower()} about the following topic:

TOPIC: {topic}
TONE: {tone}
LENGTH: {length}
"""

        if keywords:
            prompt += f"\nKEYWORDS TO INCLUDE: {keywords}\n"

        if context:
            prompt += f"\nADDITIONAL INSTRUCTIONS: {context}\n"

        if previous_content:
            prompt += f"\nPREVIOUS VERSION (for reference, write differently):\n{previous_content}\n"

        prompt += """\nOUTPUT FORMAT:
TITLE: <compelling title here>

<full content here with proper structure>
"""

        response = self.client.generate(prompt, system=system, temperature=0.8, max_tokens=4000)

        # Parse title and content
        title = "Untitled"
        content = response

        if "TITLE:" in response.upper():
            lines = response.split("\n", 1)
            first_line = lines[0].strip()
            if "TITLE:" in first_line.upper():
                title = first_line.split(":", 1)[1].strip()
                if len(lines) > 1:
                    content = lines[1].strip()

        # Store in memory
        content_id = f"content_{hash(topic + tone + length + content_type) % 100000}"
        self.memory.add_context(content_id, {
            "topic": topic,
            "tone": tone,
            "length": length,
            "content_type": content_type,
            "title": title,
            "content": content,
            "keywords": keywords
        })

        return {
            "id": content_id,
            "title": title,
            "content": content,
            "tone": tone,
            "length": length,
            "content_type": content_type,
            "topic": topic,
            "keywords": keywords
        }

    def regenerate_content(self, original_data, topic, content_type, tone, length,
                          context="", keywords=""):
        """
        Regenerate content with fresh wording while keeping same intent.
        """
        previous = original_data.get("content", "")

        system = self._build_system_prompt(tone, content_type, length)
        system += "\n\nIMPORTANT: This is a REGENERATION. Use completely different wording, structure, and examples while keeping the same message intent. Do NOT copy phrases from the previous version."

        prompt = f"""Regenerate this {content_type.lower()} with completely fresh content:

TOPIC: {topic}
TONE: {tone}
LENGTH: {length}
"""

        if keywords:
            prompt += f"\nKEYWORDS TO INCLUDE: {keywords}\n"

        if context:
            prompt += f"\nADDITIONAL INSTRUCTIONS: {context}\n"

        prompt += f"\nPREVIOUS VERSION (DO NOT COPY - write differently):\n{previous}\n"
        prompt += """\nOUTPUT FORMAT:
TITLE: <new compelling title>

<completely rewritten content>"""

        response = self.client.generate(prompt, system=system, temperature=0.9, max_tokens=4000)

        title = "Untitled"
        content = response

        if "TITLE:" in response.upper():
            lines = response.split("\n", 1)
            first_line = lines[0].strip()
            if "TITLE:" in first_line.upper():
                title = first_line.split(":", 1)[1].strip()
                if len(lines) > 1:
                    content = lines[1].strip()

        return {
            "id": original_data.get("id", "") + "_regen",
            "title": title,
            "content": content,
            "tone": tone,
            "length": length,
            "content_type": content_type,
            "topic": topic,
            "keywords": keywords
        }

    def get_memory_context(self, content_id=None):
        """Retrieve stored content context from memory"""
        if content_id:
            return self.memory.get_context(content_id)
        return self.memory.get_all_contexts()
