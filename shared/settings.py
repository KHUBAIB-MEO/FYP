"""
Configuration settings for AI Email Agent & Content Scripting Platform
"""
import os

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# File paths
MEMORY_FILE = os.path.join(DATA_DIR, "memory.json")
ANALYTICS_DB = os.path.join(DATA_DIR, "analytics.db")
THEME_FILE = os.path.join(DATA_DIR, "theme.txt")

# Ollama Configuration
OLLAMA_HOST = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:7b"

# Fallback models (used if Ollama is not running)
FALLBACK_MODELS = [
    "qwen2.5:7b",
    "llama3.1:8b",
    "mistral:7b",
    "gemma2:9b",
    "phi3:medium",
    "codellama:7b"
]

# Email Configuration Defaults
DEFAULT_SMTP_SERVER = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587

# Application Settings
APP_NAME = "AI TASKFORCE"
APP_VERSION = "1.0.0"

# Email Length Definitions
EMAIL_LENGTHS = {
    "Short": "50-80 words, concise and to the point",
    "Medium": "150-200 words, balanced detail",
    "Long": "300-400 words, comprehensive coverage"
}

# Content Length Definitions
CONTENT_LENGTHS = {
    "Short": "100-200 words, brief and focused",
    "Medium": "400-600 words, well-developed content",
    "Long": "800-1200 words, in-depth coverage",
    "Extra Long": "1500-2000 words, comprehensive guide"
}

# Email Tone Options
EMAIL_TONES = [
    "Professional",
    "Funny",
    "Emotional",
    "Persuasive",
    "Casual"
]

# Content Tone Options
CONTENT_TONES = [
    "Professional",
    "Casual",
    "Creative",
    "Persuasive",
    "Technical",
    "Humorous"
]

# Content Type Options
CONTENT_TYPES = [
    "Blog Post",
    "Social Media",
    "Ad Copy",
    "Video Script",
    "Product Description",
    "Email Newsletter",
    "General Content"
]

# Light Theme Colors
LIGHT_THEME = {
    "primary": "#6366f1",
    "primary_dark": "#4f46e5",
    "secondary": "#8b5cf6",
    "success": "#10b981",
    "danger": "#ef4444",
    "warning": "#f59e0b",
    "bg": "#f1f5f9",
    "card": "#ffffff",
    "sidebar": "#ffffff",
    "text": "#1e293b",
    "text_light": "#64748b",
    "text_secondary": "#475569",
    "border": "#e2e8f0",
    "hover": "#f8fafc",
    "input_bg": "#ffffff",
    "input_border": "#e2e8f0",
    "menu_bg": "#ffffff",
    "chart_bg": "#ffffff",
    "overlay": "rgba(255,255,255,0.85)",
    "stat_card_bg": "#ffffff",
    "group_title": "#6366f1",
    "nav_active_bg": "#eff6ff",
    "nav_active_text": "#6366f1",
    "nav_inactive_text": "#64748b",
    "nav_hover": "#f1f5f9",
    "scrollbar": "#cbd5e1",
    "scrollbar_hover": "#94a3b8",
    "hint_text": "#94a3b8",
    "code_bg": "#f8fafc",
    "separator": "#e2e8f0",
    "placeholder": "#94a3b8",
    "selection_bg": "#c7d2fe",
}

# Dark Theme Colors
DARK_THEME = {
    "primary": "#818cf8",
    "primary_dark": "#6366f1",
    "secondary": "#a78bfa",
    "success": "#34d399",
    "danger": "#f87171",
    "warning": "#fbbf24",
    "bg": "#0f172a",
    "card": "#1e293b",
    "sidebar": "#1e293b",
    "text": "#f1f5f9",
    "text_light": "#94a3b8",
    "text_secondary": "#cbd5e1",
    "border": "#334155",
    "hover": "#334155",
    "input_bg": "#1e293b",
    "input_border": "#334155",
    "menu_bg": "#1e293b",
    "chart_bg": "#1e293b",
    "overlay": "rgba(15,23,42,0.90)",
    "stat_card_bg": "#1e293b",
    "group_title": "#818cf8",
    "nav_active_bg": "#1e293b",
    "nav_active_text": "#818cf8",
    "nav_inactive_text": "#94a3b8",
    "nav_hover": "#334155",
    "scrollbar": "#475569",
    "scrollbar_hover": "#64748b",
    "hint_text": "#64748b",
    "code_bg": "#1e293b",
    "separator": "#334155",
    "placeholder": "#64748b",
    "selection_bg": "#4338ca",
}

def get_theme():
    """Load saved theme or default to light"""
    if os.path.exists(THEME_FILE):
        try:
            with open(THEME_FILE, 'r') as f:
                theme_name = f.read().strip()
                if theme_name == "dark":
                    return DARK_THEME
        except:
            pass
    return LIGHT_THEME

def save_theme(is_dark):
    """Save theme preference"""
    try:
        with open(THEME_FILE, 'w') as f:
            f.write("dark" if is_dark else "light")
    except:
        pass
