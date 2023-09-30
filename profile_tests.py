import sys
import unittest
import cProfile
import pstats


num_runs = 10 if len(sys.argv) == 1 else int(sys.argv[1])
combined_stats = pstats.Stats()

for i in range(num_runs):
    current_run = cProfile.Profile()

    with current_run:
        test_suite = unittest.defaultTestLoader.discover("test")
        unittest.TextTestRunner().run(test_suite)

    combined_stats.add(current_run)

combined_stats.dump_stats("profile_run.pstats")

# Optional: You can also save the combined profile to a file if needed
# combined_stats.dump_stats('combined_profile.pstats')
