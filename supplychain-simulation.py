import simpy
import random
from dataclasses import dataclass
from typing import List, Dict
import statistics

@dataclass
class SimulationParams:
    # Interarrival times
    interarrival_time_bodies: float = 2.0
    interarrival_time_doors: float = 2.0
    interarrival_time_engines: float = 2.0
    
    # Quantity parameters
    max_quantity_per_arrival: int = 5
    min_quantity_per_arrival: int = 1
    
    # Process times for each machine
    process_time_M1: float = 1.0
    process_time_M2: float = 1.0
    process_time_M3: float = 1.0
    process_time_M4: float = 1.0
    
    # Order timeout (in time units)
    timeout: float = 14.0
    
    # Number of agents for resource 3 (M3)
    nagent3: int = 3
    
    # Other parameters
    transport_time_external: float = 1.0
    transport_time_internal: float = 1.0
    batch_size: int = 10

@dataclass
class SimulationMetrics:
    total_costs: float = 0
    total_revenue: float = 0
    total_profit: float = 0
    output: int = 0
    lost_orders: int = 0
    wip_inventory: List[int] = None
    supplier_engines_inventory: List[int] = None
    supplier_doors_inventory: List[int] = None
    machine_utilization: Dict[str, List[float]] = None
    
    def __post_init__(self):
        self.wip_inventory = []
        self.supplier_engines_inventory = []
        self.supplier_doors_inventory = []
        self.machine_utilization = {
            'M1': [], 'M2': [], 'M3': [], 'M4': []
        }
    
    @property
    def service_level(self) -> float:
        if self.output == 0:
            return 0
        return 100 * (self.output - self.lost_orders) / self.output
    
    @property
    def unit_profit(self) -> float:
        return self.total_profit / self.output if self.output > 0 else 0
    
    @property
    def unit_cost(self) -> float:
        return self.total_costs / self.output if self.output > 0 else 0
    
    @property
    def mean_wip_inventory(self) -> float:
        return statistics.mean(self.wip_inventory) if self.wip_inventory else 0
    
    @property
    def mean_inventory_supplier_engines(self) -> float:
        return statistics.mean(self.supplier_engines_inventory) if self.supplier_engines_inventory else 0
    
    @property
    def mean_inventory_supplier_doors(self) -> float:
        return statistics.mean(self.supplier_doors_inventory) if self.supplier_doors_inventory else 0
    
    @property
    def mean_capacity_utilization(self) -> float:
        all_utils = []
        for machine_utils in self.machine_utilization.values():
            if machine_utils:
                all_utils.extend(machine_utils)
        return statistics.mean(all_utils) if all_utils else 0

class CarManufacturingSimulation:
    def __init__(self, env: simpy.Environment, params: SimulationParams):
        self.env = env
        self.params = params
        self.metrics = SimulationMetrics()
        
        # Financial parameters
        self.REVENUE_PER_CAR = 30
        self.MANUFACTURING_COST_PER_CAR = 10
        self.TRANSPORT_COST_PER_DELIVERY = 30
        self.INVENTORY_COST_PER_WIP = 5
        self.OPPORTUNITY_COST_PER_LOST_ORDER = 4
        
        # Resources
        self.machines = {
            'M1': simpy.Resource(env, capacity=1),
            'M2': simpy.Resource(env, capacity=1),
            'M3': simpy.Resource(env, capacity=params.nagent3),  # Variable capacity for M3
            'M4': simpy.Resource(env, capacity=1)
        }
        
        # Storage
        self.body_queue = simpy.Store(env)
        self.door_queue = simpy.Store(env)
        self.engine_queue = simpy.Store(env)
        self.assembly_queue = simpy.Store(env)
        self.final_queue = simpy.Store(env)
        self.batch_queue = simpy.Store(env)
        
    def triangular_process_time(self, mean_time):
        return random.triangular(0.7 * mean_time, 1.3 * mean_time, mean_time)
    
    def generate_component(self, store, component_type):
        interarrival_time = {
            'body': self.params.interarrival_time_bodies,
            'door': self.params.interarrival_time_doors,
            'engine': self.params.interarrival_time_engines
        }[component_type]
        
        while True:
            yield self.env.timeout(interarrival_time)
            # Generate random quantity for this arrival
            quantity = random.randint(
                self.params.min_quantity_per_arrival,
                self.params.max_quantity_per_arrival
            )
            
            for _ in range(quantity):
                yield store.put(component_type)
            
            # Update inventory metrics
            if component_type == 'engine':
                self.metrics.supplier_engines_inventory.append(len(store.items))
            elif component_type == 'door':
                self.metrics.supplier_doors_inventory.append(len(store.items))
    
    def process_body(self):
        while True:
            # Get body from queue
            start_wait_time = self.env.now
            body = yield self.body_queue.get()
            
            # Check if order timeout occurred
            if self.env.now - start_wait_time > self.params.timeout:
                self.metrics.lost_orders += 1
                continue
            
            start_time = self.env.now
            # Process at M1
            with self.machines['M1'].request() as req:
                yield req
                yield self.env.timeout(self.triangular_process_time(self.params.process_time_M1))
                
                # Record utilization
                self.metrics.machine_utilization['M1'].append(
                    (self.env.now - start_time) / self.params.process_time_M1
                )
                
                yield self.env.timeout(self.params.transport_time_internal)
                yield self.assembly_queue.put('processed_body')
    
    def assemble_components(self):
        while True:
            start_wait_time = self.env.now
            
            # Wait for all components
            yield self.assembly_queue.get()
            # Get 4 doors
            for _ in range(4):
                yield self.door_queue.get()
            # Get engine
            yield self.engine_queue.get()
            
            # Check for timeout
            if self.env.now - start_wait_time > self.params.timeout:
                self.metrics.lost_orders += 1
                continue
            
            # M2: Door Assembly
            start_time = self.env.now
            with self.machines['M2'].request() as req:
                yield req
                yield self.env.timeout(self.triangular_process_time(self.params.process_time_M2))
                self.metrics.machine_utilization['M2'].append(
                    (self.env.now - start_time) / self.params.process_time_M2
                )
            
            # M3: Engine Assembly
            start_time = self.env.now
            with self.machines['M3'].request() as req:
                yield req
                yield self.env.timeout(self.triangular_process_time(self.params.process_time_M3))
                self.metrics.machine_utilization['M3'].append(
                    (self.env.now - start_time) / self.params.process_time_M3
                )
            
            # M4: Final Assembly
            start_time = self.env.now
            with self.machines['M4'].request() as req:
                yield req
                yield self.env.timeout(self.triangular_process_time(self.params.process_time_M4))
                self.metrics.machine_utilization['M4'].append(
                    (self.env.now - start_time) / self.params.process_time_M4
                )
            
            yield self.env.timeout(self.params.transport_time_internal)
            yield self.final_queue.put('completed_car')
            
            # Update WIP inventory
            self.metrics.wip_inventory.append(
                len(self.assembly_queue.items) + len(self.final_queue.items)
            )
    
    def batch_and_ship(self):
        batch = []
        while True:
            car = yield self.final_queue.get()
            batch.append(car)
            
            if len(batch) == self.params.batch_size:
                # Ship the batch
                yield self.env.timeout(self.params.transport_time_external)
                
                # Update metrics
                self.metrics.output += self.params.batch_size
                self.metrics.total_revenue += self.params.batch_size * self.REVENUE_PER_CAR
                self.metrics.total_costs += (
                    self.params.batch_size * self.MANUFACTURING_COST_PER_CAR +
                    self.TRANSPORT_COST_PER_DELIVERY
                )
                
                batch = []
    
    def run_simulation(self, duration=450):
        # Start component generation
        self.env.process(self.generate_component(self.body_queue, 'body'))
        self.env.process(self.generate_component(self.door_queue, 'door'))
        self.env.process(self.generate_component(self.engine_queue, 'engine'))
        
        # Start processing
        self.env.process(self.process_body())
        self.env.process(self.assemble_components())
        self.env.process(self.batch_and_ship())
        
        # Run simulation
        self.env.run(until=duration)
        
        # Calculate final metrics
        wip_at_end = (len(self.assembly_queue.items) + 
                     len(self.final_queue.items))
        self.metrics.total_costs += wip_at_end * self.INVENTORY_COST_PER_WIP
        self.metrics.total_profit = (
            self.metrics.total_revenue - self.metrics.total_costs
        )

# Run the simulation
if __name__ == "__main__":
    # Create simulation parameters
    params = SimulationParams(
        interarrival_time_bodies=2.0,
        interarrival_time_doors=2.0,
        interarrival_time_engines=2.0,
        max_quantity_per_arrival=1,
        min_quantity_per_arrival=1,
        process_time_M1=1.0,
        process_time_M2=1.0,
        process_time_M3=1.0,
        process_time_M4=1.0,
        timeout=14.0,
        nagent3=3
    )
    
    env = simpy.Environment()
    simulation = CarManufacturingSimulation(env, params)
    simulation.run_simulation()

    # Print results
    metrics = simulation.metrics
    print(f"Total Costs: ${metrics.total_costs:.2f}")
    print(f"Unit Profit: ${metrics.unit_profit:.2f}")
    print(f"Unit Cost: ${metrics.unit_cost:.2f}")
    print(f"Total Profit: ${metrics.total_profit:.2f}")
    print(f"Total Revenue: ${metrics.total_revenue:.2f}")
    print(f"Output: {metrics.output}")
    print(f"Lost Orders: {metrics.lost_orders}")
    print(f"Service Level: {metrics.service_level:.2f}%")
    print(f"Mean Capacity Utilization: {metrics.mean_capacity_utilization:.2f}%")
    print(f"Mean WIP Inventory: {metrics.mean_wip_inventory:.2f}")
    print(f"Mean Inventory Supplier Engines: {metrics.mean_inventory_supplier_engines:.2f}")
    print(f"Mean Inventory Supplier Doors: {metrics.mean_inventory_supplier_doors:.2f}")