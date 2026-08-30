import time


class Timer:

    def __init__(self):
        self.start=time.time()


    def cost(self):

        return round(
            time.time()-self.start,
            3
        )