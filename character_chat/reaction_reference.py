"""Length planning for optional short-reference repetition; no audio/GPU imports."""
def reference_repeat_count(frames, sample_rate, max_repeats=3):
    if sample_rate<=0 or frames<=0:raise ValueError("Invalid reference duration")
    if frames>5*sample_rate:return 1
    overlap=min(round(sample_rate*.02),frames//4)
    for repeats in range(2,max_repeats+1):
        if repeats*frames-(repeats-1)*overlap>5*sample_rate:return repeats
    raise ValueError("Reference is too short even after three repeats. Upload a sample of at least 2 seconds.")
