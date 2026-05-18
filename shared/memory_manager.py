"""
Memory Manager - Stores email context and conversation history
Uses JSON file for persistence across sessions
"""
import json
import os
from datetime import datetime
from shared.settings import MEMORY_FILE

class MemoryManager:
    """
    Manages persistent memory for email contexts.
    Stores generated emails, topics, and recipient information.
    """

    def __init__(self):
        self.memory_file = MEMORY_FILE
        self.memory = self._load()

    def _load(self):
        """Load memory from JSON file"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return self._default_memory()
        return self._default_memory()

    def _default_memory(self):
        """Default memory structure"""
        return {
            "emails": {},
            "templates": [],
            "recipients": {},
            "last_updated": datetime.now().isoformat()
        }

    def save(self):
        """Save memory to JSON file"""
        self.memory["last_updated"] = datetime.now().isoformat()
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.memory, f, indent=2, ensure_ascii=False)

    def add_context(self, email_id, context_data):
        """
        Store email generation context

        Args:
            email_id: Unique identifier for the email
            context_data: Dict with subject, body, tone, etc.
        """
        if "emails" not in self.memory:
            self.memory["emails"] = {}

        context_data["timestamp"] = datetime.now().isoformat()
        self.memory["emails"][email_id] = context_data
        self.save()

    def get_context(self, email_id):
        """Retrieve specific email context"""
        return self.memory.get("emails", {}).get(email_id, {})

    def get_all_contexts(self):
        """Get all stored email contexts"""
        return self.memory.get("emails", {})

    def delete_context(self, email_id):
        """Remove an email from memory"""
        if "emails" in self.memory and email_id in self.memory["emails"]:
            del self.memory["emails"][email_id]
            self.save()
            return True
        return False

    def add_recipient(self, email, name="", notes=""):
        """Store recipient information"""
        if "recipients" not in self.memory:
            self.memory["recipients"] = {}
        self.memory["recipients"][email] = {
            "name": name,
            "notes": notes,
            "last_contact": datetime.now().isoformat()
        }
        self.save()

    def get_recipient(self, email):
        """Get recipient info"""
        return self.memory.get("recipients", {}).get(email, {})

    def add_template(self, name, content, tone="Professional"):
        """Save a reusable template"""
        if "templates" not in self.memory:
            self.memory["templates"] = []
        self.memory["templates"].append({
            "name": name,
            "content": content,
            "tone": tone,
            "created": datetime.now().isoformat()
        })
        self.save()

    def get_templates(self):
        """Get all saved templates"""
        return self.memory.get("templates", [])
