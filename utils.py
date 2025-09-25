import threading
import time

class RateLimiter:
    def __init__(self, limit_per_minute=10):
        self.limit = limit_per_minute
        self.users = {}
        self.lock = threading.Lock()

    def check(self, user_id):
        now = int(time.time())
        with self.lock:
            data = self.users.get(user_id, [])
            # keep only last 60 seconds
            data = [t for t in data if now - t < 60]
            if len(data) >= self.limit:
                return False
            data.append(now)
            self.users[user_id] = data
            return True

rate_limiter = RateLimiter()
