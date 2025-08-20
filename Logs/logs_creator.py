#A function to create a log with time consumption for each fucntion to make it easier to optimize


import cProfile
import pstats
import atexit
import os
import io








s = io.StringIO()

print("Starting profiler...")
profiler = cProfile.Profile()
profiler.enable()

def save_profiler_stats():
    profiler.disable()
    print("Saving profiler stats to profile.stats...")
    
    # Get the directory where this script is located.
    log_dir = os.path.dirname(os.path.abspath(__file__))
    stats_path = os.path.join(log_dir, "profile.stats")
    log_path = os.path.join(log_dir, "log.txt")

    profiler.dump_stats(stats_path)
    print("Profiler stats saved. ❤️")

    s = io.StringIO()
    stats = pstats.Stats(stats_path, stream=s)

    # Only include functions from your bot's files
    # Replace "pikachu" with the unique part of your module/folder name
    stats.sort_stats("cumulative")
    s.write("--- Top 100 Functions by Cumulative Time ---")
    stats.print_stats("pikachu")  # filters functions containing "pikachu" in path or name
    s.write("\n\n")

    stats.sort_stats("tottime")
    s.write("--- Top 100 Functions by Total Time ---")
    stats.print_stats("pikachu")  # same filter here

    with open(log_path, "w") as file:
        file.write(s.getvalue())

    os.remove(stats_path)
    print("Successfully saved the log file ✅")
