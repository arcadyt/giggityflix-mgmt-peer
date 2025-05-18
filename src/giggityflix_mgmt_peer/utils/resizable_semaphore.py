import threading

class ResizableSemaphore:
    def __init__(self, max_permits):
        if max_permits < 0:
            raise ValueError("Semaphore initial max permits must be non-negative")
        self._cond = threading.Condition()
        self._max_permits = max_permits
        self._available_permits = max_permits

    def acquire(self, blocking=True, timeout=None):
        with self._cond:
            if not blocking:
                if self._available_permits > 0:
                    self._available_permits -= 1
                    return True
                else:
                    return False
            end_time = None
            if timeout is not None:
                end_time = threading.time() + timeout
            while self._available_permits <= 0:
                remaining = None
                if end_time is not None:
                    remaining = end_time - threading.time()
                    if remaining <= 0:
                        return False
                if not self._cond.wait(remaining):
                    return False
            self._available_permits -= 1
            return True

    def release(self):
        with self._cond:
            if self._available_permits < self._max_permits:
                self._available_permits += 1
                self._cond.notify()

    def resize(self, new_max):
        if new_max < 0:
            raise ValueError("Semaphore max permits cannot be negative")
        with self._cond:
            if new_max < self._available_permits:
                self._available_permits = new_max
            self._max_permits = new_max
            self._cond.notify_all()

    @property
    def max_permits(self):
        return self._max_permits

    @property
    def available_permits(self):
        return self._available_permits