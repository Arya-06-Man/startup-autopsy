import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from autopsy.models import Run

class Store:
    def __init__(self, root='data'):
        self.root = Path(root)
        (self.root / 'runs').mkdir(parents=True, exist_ok=True)
        (self.root / 'cache').mkdir(exist_ok=True)

    def save(self, run):
        path = self.root / 'runs' / (run.id + '.json')
        tmp = path.with_suffix('.tmp')
        tmp.write_text(run.model_dump_json(indent=2))
        tmp.replace(path)

    def runs(self):
        result = []
        for p in sorted((self.root / 'runs').glob('*.json'), reverse=True):
            try:
                result.append(Run.model_validate_json(p.read_text()))
            except (ValueError, OSError):
                continue
        return sorted(result, key=lambda r: r.created_at, reverse=True)

    def cache_path(self, path, payload):
        key = hashlib.sha256((path + json.dumps(payload, sort_keys=True)).encode()).hexdigest()
        return self.root / 'cache' / (key + '.json')

    def cached(self, path, payload, hours):
        p = self.cache_path(path, payload)
        if p.exists():
            try:
                data = json.loads(p.read_text())
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(data['retrieved_at'])).total_seconds()
                if 0 <= age < hours * 3600 and 'data' in data:
                    return data
            except (ValueError, KeyError, TypeError, OSError):
                pass
        return None

    def put_cache(self, path, payload, data):
        self.cache_path(path, payload).write_text(json.dumps(data))
