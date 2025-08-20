
import pstats
import io

# The name of the stats file you generated
stats_file = 'profile.stats'
# The name of the output text file we'll create
output_file = 'profiler_report.txt'

# Create a stream to capture the output
s = io.StringIO()

# Load the stats file
try:
    stats = pstats.Stats(stats_file, stream=s)
except FileNotFoundError:
    print(f"Error: The file '{stats_file}' was not found. Please generate it first by running your bot.")
    exit()

# Sort the stats and print them to the stream
stats.sort_stats('cumulative')
s.write("--- Top 50 Functions by Cumulative Time ---")
stats.print_stats(50)

s.write("\n\n")

stats.sort_stats('tottime')
s.write("--- Top 50 Functions by Total Time (tottime) ---")
stats.print_stats(50)


# Write the captured output from the stream to the text file
try:
    with open(output_file, 'w') as f:
        f.write(s.getvalue())
    print(f"Successfully converted '{stats_file}' to '{output_file}'. You can open it now! ❤️")
except Exception as e:
    print(f"Error writing to file: {e}")

