import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    api_key: str = ''
    max_calls: int = 20
    max_credits: float = 30.0
    max_iterations: int = 2
    cache_hours: float = 24
    gemini_key: str = ''
    gemini_model: str = ''
    refresh_data: bool = False

    @classmethod
    def load(cls):
        load_dotenv(override=True)
        return cls(os.getenv('CRUSTDATA_API_KEY', ''), int(os.getenv('MAX_API_CALLS', '20')),
                   float(os.getenv('MAX_CREDITS', '30')), int(os.getenv('MAX_ITERATIONS', '2')),
                   float(os.getenv('CACHE_TTL_HOURS', '24')), os.getenv('GEMINI_API_KEY', ''), os.getenv('GEMINI_MODEL', ''))
