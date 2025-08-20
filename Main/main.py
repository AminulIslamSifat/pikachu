#This function here staats the bot by running the main function from bot_core.py module




from bot_core import main
import asyncio
import atexit
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Logs.logs_creator import save_profiler_stats





if __name__=="__main__":
    #atexit.register(save_profiler_stats)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCaught keyboard interrupt. Exiting.")