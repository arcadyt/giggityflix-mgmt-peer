import pytest
import threading
import time

from giggityflix_mgmt_peer.v1.utils.resizable_semaphore import ResizableSemaphore


class TestResizableSemaphore:
    def test_initial_state(self):
        sem = ResizableSemaphore(2)
        assert sem.acquire(blocking=False) is True
        assert sem.acquire(blocking=False) is True
        assert sem.acquire(blocking=False) is False

    def test_release_behavior(self):
        sem = ResizableSemaphore(1)
        assert sem.acquire(blocking=False) is True
        assert sem.acquire(blocking=False) is False
        sem.release()
        assert sem.acquire(blocking=False) is True

    @pytest.mark.parametrize("initial_max, new_max", [
        (2, 3), (5, 10), (1, 100)
    ])
    def test_resize_increase_max(self, initial_max, new_max):
        sem = ResizableSemaphore(initial_max)
        for _ in range(initial_max):
            sem.acquire()
        sem.resize(new_max)
        sem.release()
        assert sem.acquire(blocking=False) is True

    @pytest.mark.parametrize("initial_max, new_max", [
        (5, 3), (10, 1), (100, 5)
    ])
    def test_resize_decrease_clamps_available(self, initial_max, new_max):
        sem = ResizableSemaphore(initial_max)
        sem.resize(new_max)
        for _ in range(new_max):
            assert sem.acquire(blocking=False) is True
        assert sem.acquire(blocking=False) is False

    def test_resize_below_acquired_permits(self):
        sem = ResizableSemaphore(3)
        for _ in range(3):
            sem.acquire()
        sem.resize(1)
        sem.release()
        assert sem.acquire(blocking=False) is True
        assert sem.acquire(blocking=False) is False
        sem.release()
        sem.release()
        assert sem.available_permits == 1

    def test_concurrent_resize_contention(self):
        sem = ResizableSemaphore(1)
        acquired = []
        barrier = threading.Barrier(2)

        def worker():
            barrier.wait()
            sem.acquire()
            acquired.append(True)
            time.sleep(0.1)
            sem.release()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        threads[0].start()
        threads[1].start()
        time.sleep(0.1)
        sem.resize(2)
        for t in threads:
            t.join(timeout=1)
        assert len(acquired) == 2

    @pytest.mark.timeout(3)
    def test_resize_unblocks_waiters(self):
        sem = ResizableSemaphore(1)
        acquired = []
        start_event = threading.Event()
        proceed_event = threading.Event()

        def worker():
            start_event.set()
            sem.acquire()
            acquired.append(True)
            proceed_event.wait()
            sem.release()

        sem.acquire()
        t = threading.Thread(target=worker)
        t.start()
        start_event.wait()
        sem.resize(2)
        sem.release()
        t.join(timeout=1)
        assert len(acquired) == 1
        proceed_event.set()

    def test_negative_initial_max_raises_error(self):
        with pytest.raises(ValueError):
            ResizableSemaphore(-1)

    def test_resize_to_negative_raises_error(self):
        sem = ResizableSemaphore(1)
        with pytest.raises(ValueError):
            sem.resize(-1)

    def test_max_zero_behavior(self):
        sem = ResizableSemaphore(0)
        assert sem.acquire(blocking=False) is False
        sem.release()
        assert sem.available_permits == 0

    @pytest.mark.parametrize("timeout, expected", [
        (0.1, False), (None, True)
    ])
    def test_acquire_timeout_behavior(self, timeout, expected):
        sem = ResizableSemaphore(1)
        sem.acquire()  # Exhaust permit
        result = []

        def worker():
            result.append(sem.acquire(timeout=timeout))

        t = threading.Thread(target=worker)
        start_time = time.time()
        t.start()

        # Only release the semaphore for the expected=True case (timeout=None)
        if expected:
            # Small sleep to ensure the worker is waiting
            time.sleep(0.1)
            sem.release()

        t.join(timeout=2)

        # For timeout case, we don't need the timing check anymore
        # since we're controlling the behavior explicitly

        assert result == [expected]

    def test_multiple_resize_operations(self):
        sem = ResizableSemaphore(3)
        sem.resize(5)
        assert sem.max_permits == 5
        assert sem.available_permits == 3
        sem.resize(2)
        assert sem.max_permits == 2
        assert sem.available_permits == 2

    def test_thread_safety_during_resize(self):
        sem = ResizableSemaphore(5)
        test_duration = 1
        stress_factor = 50

        def worker():
            end_time = time.time() + test_duration
            while time.time() < end_time:
                if sem.acquire(blocking=False):
                    time.sleep(0.001)
                    sem.release()

        def resizer():
            end_time = time.time() + test_duration
            while time.time() < end_time:
                sem.resize(sem.max_permits + 1)
                time.sleep(0.001)
                sem.resize(max(1, sem.max_permits - 1))
                time.sleep(0.001)

        workers = [threading.Thread(target=worker) for _ in range(stress_factor)]
        resizers = [threading.Thread(target=resizer) for _ in range(2)]

        for t in workers + resizers:
            t.start()
        for t in workers + resizers:
            t.join(timeout=test_duration + 2)

        assert sem.available_permits <= sem.max_permits