import time

def generate_small_talk(reply):

    for char in reply:

        yield f"event: token\ndata: {char}\n\n"

        time.sleep(0.05)