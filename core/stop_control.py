import threading


class StopController:
    def __init__(self):
        self.event = threading.Event()

    def reset(self):
        self.event.clear()

    def stop(self):
        self.event.set()

    def is_stopped(self):
        return self.event.is_set()