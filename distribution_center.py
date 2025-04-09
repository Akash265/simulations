import simpy
import random

# Parameters
NUM_FORKLIFTS = 5
NUM_UNLOADING_DOCKS = 2
NUM_LOADING_DOCKS = 2
TRUCK_CAPACITY = 10  # Pallets
ASSEMBLY_AREA_CAPACITY = 20  # Pallets
SIMULATION_TIME = 100  # Minutes

# Processes
def truck_arrival(env, unloading_docks, forklifts, storage):
    """Truck arrives to unload pallets."""
    while True:
        yield env.timeout(random.expovariate(1/10))  # Interarrival time
        pallets = random.randint(5, TRUCK_CAPACITY)
        print(f"Truck arrives with {pallets} pallets at time {env.now:.2f}")
        env.process(unload_truck(env, unloading_docks, forklifts, storage, pallets))

def unload_truck(env, unloading_docks, forklifts, storage, pallets):
    """Unloading process."""
    with unloading_docks.request() as dock:
        yield dock
        print(f"Truck starts unloading at time {env.now:.2f}")
        for _ in range(pallets):
            with forklifts.request() as forklift:
                yield forklift
                yield env.timeout(1)  # Time to move one pallet
                storage.put(1)  # Add pallet to storage
                print(f"Pallet moved to storage at time {env.now:.2f}")

def assemble_order(env, forklifts, storage, assembly_area, order_size):
    """Order assembly process."""
    yield env.timeout(random.expovariate(1/15))  # Random time to start order
    print(f"Order assembly starts at time {env.now:.2f}")
    required_pallets = random.randint(1, order_size)

    # Check if enough pallets are available
    if storage.level >= required_pallets:
        with forklifts.request() as forklift:
            yield forklift
            yield storage.get(required_pallets)
            yield env.timeout(2 * required_pallets)  # Time to assemble
            assembly_area.put(required_pallets)  # Place order in assembly area
            print(f"Order assembled and placed at time {env.now:.2f}")
    else:
        print(f"Not enough pallets for order at time {env.now:.2f}")

def load_truck(env, loading_docks, forklifts, assembly_area):
    """Loading process."""
    while True:
        yield env.timeout(random.expovariate(1/20))  # Truck arrives for loading
        with loading_docks.request() as dock:
            yield dock
            print(f"Truck arrives for loading at time {env.now:.2f}")

            # Check if enough pallets to meet minimum capacity
            pallets_to_load = min(assembly_area.level, TRUCK_CAPACITY)
            if pallets_to_load >= TRUCK_CAPACITY / 2:
                with forklifts.request() as forklift:
                    yield forklift
                    yield assembly_area.get(pallets_to_load)
                    yield env.timeout(3 * pallets_to_load)  # Time to load pallets
                    print(f"Truck loaded with {pallets_to_load} pallets at time {env.now:.2f}")
            else:
                print(f"Truck leaves empty due to insufficient pallets at time {env.now:.2f}")

# Environment and resources
env = simpy.Environment()
unloading_docks = simpy.Resource(env, capacity=NUM_UNLOADING_DOCKS)
loading_docks = simpy.Resource(env, capacity=NUM_LOADING_DOCKS)
forklifts = simpy.Resource(env, capacity=NUM_FORKLIFTS)
storage = simpy.Container(env, capacity=100, init=50)  # Initial pallets in storage
assembly_area = simpy.Container(env, capacity=ASSEMBLY_AREA_CAPACITY, init=0)

# Run processes
env.process(truck_arrival(env, unloading_docks, forklifts, storage))
env.process(assemble_order(env, forklifts, storage, assembly_area, 5))
env.process(load_truck(env, loading_docks, forklifts, assembly_area))

# Run simulation
env.run(until=SIMULATION_TIME)


