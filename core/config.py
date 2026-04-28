# core/config.py
import os

# Models
MODEL_FAST = "llama-3.1-8b-instant"     # Classifier, Visualizer, Researcher
MODEL_SMART = "llama-3.3-70b-versatile"  # Analyst, Devil, Synthesizer, Writer

# Retry settings
MAX_RETRIES = 4
RETRY_DELAY = 5

# Loop limits (lower = fewer API calls)
MAX_RESEARCH_LOOPS = 1
MAX_CRITIQUE_LOOPS = 1

# Response cache
CACHE_DIR = os.path.join(os.path.dirname(__file__), "../.cache")
CACHE_TTL_HOURS = 24
