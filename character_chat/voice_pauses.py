"""Limit near-silent PCM pauses without waiting for a whole TTS clip."""
from array import array
import sys

class PcmPauseCompactor:
    def __init__(self, sample_rate):
        self.onset_limit=round(sample_rate*.06)
        self.pause_limit=round(sample_rate*.24)
        self.silent_samples=0
        self.heard_voice=False

    def feed(self, content):
        samples=array("h")
        samples.frombytes(content)
        if sys.byteorder!="little":samples.byteswap()
        output=array("h")
        for sample in samples:
            if abs(sample)>64:
                self.heard_voice=True
                self.silent_samples=0
                output.append(sample)
            else:
                self.silent_samples+=1
                # Keep a short onset and 240 ms of natural punctuation silence.
                limit=self.pause_limit if self.heard_voice else self.onset_limit
                if self.silent_samples<=limit:output.append(sample)
        if sys.byteorder!="little":output.byteswap()
        return output.tobytes()
