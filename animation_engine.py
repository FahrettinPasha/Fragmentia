class Animation:
    def __init__(self, frames, frame_rate=0.1):
        self.frames = frames  # PNG listesi
        self.frame_rate = frame_rate
        self.timer = 0
        self.index = 0

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.frame_rate:
            self.timer = 0
            self.index = (self.index + 1) % len(self.frames)

    def get_current_frame(self):
        return self.frames[self.index]