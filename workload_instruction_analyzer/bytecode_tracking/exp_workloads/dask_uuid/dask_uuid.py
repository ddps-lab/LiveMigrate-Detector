import uuid
import time
from dask.threaded import get

# Define simple functions for the example


def add(x, y):
    """A simple function to add two numbers."""
    print(f"Executing 'add': {x} + {y}")
    return x + y


def increment(x):
    """A simple function to increment a number by 1."""
    print(f"Executing 'increment': {x} + 1")
    return x + 1


# Start an infinite loop
while True:
    print("\n--- Starting new loop iteration: Rebuilding the entire graph ---")

    # 1. In each loop iteration, generate new unique keys using uuid.
    key_add_1 = f"add-task-{uuid.uuid4()}"
    key_inc_1 = f"increment-task-{uuid.uuid4()}"
    key_add_2 = f"add-task-{uuid.uuid4()}"

    # 2. 'Newly' define the Dask task graph as a dictionary.
    #    This operation is repeated in every loop.
    dsk = {
        key_add_1: (add, 5, 10),
        key_inc_1: (increment, key_add_1),
        key_add_2: (add, key_inc_1, 4)
    }

    # 3. Pass the 'newly created' graph to the Dask scheduler for execution.
    #    This is where the inefficiency lies.
    print("--- Executing Dask graph ---")
    final_result = get(dsk, key_add_2)
    print("-" * 26)

    print(f"Final Result: {final_result}")
    print(f"Graph keys used in this iteration: {list(dsk.keys())[:45]}...")

    # 4. Wait for 5 seconds
    print("\nWaiting for 5 seconds...")
    time.sleep(5)
