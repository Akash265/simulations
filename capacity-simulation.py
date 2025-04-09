import simpy
import random
import numpy as np
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Order:
    id: int
    arrival_time: float
    start_time: Optional[float] = None
    completion_time: Optional[float] = None
    is_lost: bool = False
    
class ManufacturingSystem:
    def __init__(self, env: simpy.Environment):
        # Environment setup
        self.env = env
        
        # Parameters
        self.ARRIVAL_RATE_MIN = 3
        self.ARRIVAL_RATE_MAX = 5
        self.ARRIVAL_TIME = 40
        self.EXIT_TIMEOUT = 80
        self.SERVICE_TIME_BASE = 20
        self.HOURLY_RATE_RPT = 90
        self.HOURLY_RATE_SERIAL = 30
        self.N_AGENTS = 3
        self.OPPORTUNITY_COSTS = 4000
        self.REVENUE_RPT = 9000
        self.SIMULATION_TIME = 439
        
        # Resources
        self.rpt_workers = simpy.Resource(env, capacity=self.N_AGENTS)
        
        # Statistics
        self.orders: List[Order] = []
        self.order_counter = 0
        self.serial_orders = 0
        self.worker_busy_time = 0
        
    def generate_service_time(self):
        """Triangular distribution for service time"""
        return random.triangular(0.25 * self.SERVICE_TIME_BASE, 
                               self.SERVICE_TIME_BASE, 
                               2 * self.SERVICE_TIME_BASE)
    
    def order_process(self, order: Order):
        """Process a single order through the system"""
        # Wait for available worker
        with self.rpt_workers.request() as request:
            # Record time waiting starts
            wait_start = self.env.now
            
            # Wait for worker or timeout
            result = yield request | self.env.timeout(self.EXIT_TIMEOUT)
            
            # If request not triggered, order is lost
            if request not in result:
                order.is_lost = True
                return
            
            # Record processing start time
            order.start_time = self.env.now
            
            # Process the order
            service_time = self.generate_service_time()
            self.worker_busy_time += service_time
            yield self.env.timeout(service_time)
            
            # Record completion
            order.completion_time = self.env.now
    
    def order_generator(self):
        """Generate orders according to arrival pattern"""
        while True:
            # Generate batch of orders
            n_orders = random.randint(self.ARRIVAL_RATE_MIN, self.ARRIVAL_RATE_MAX)
            
            for _ in range(n_orders):
                order = Order(id=self.order_counter, arrival_time=self.env.now)
                self.orders.append(order)
                self.order_counter += 1
                self.env.process(self.order_process(order))
            
            # Wait for next arrival
            yield self.env.timeout(self.ARRIVAL_TIME)
    
    def calculate_kpis(self):
        """Calculate all KPIs after simulation"""
        completed_orders = [o for o in self.orders if o.completion_time is not None]
        lost_orders = [o for o in self.orders if o.is_lost]
        
        # Calculate lead times for completed orders
        lead_times = [o.completion_time - o.arrival_time for o in completed_orders]
        delayed_orders = [o for o in completed_orders if o.completion_time - o.arrival_time > 120]
        otd_orders = [o for o in completed_orders if o.completion_time - o.arrival_time <= 120]
        
        # Calculate financial metrics
        revenue = len(otd_orders) * self.REVENUE_RPT + len(delayed_orders) * self.REVENUE_RPT * 0.8
        manufacturing_costs = self.N_AGENTS * self.HOURLY_RATE_RPT * self.SIMULATION_TIME
        
        # Calculate capacity utilization
        total_available_time = self.N_AGENTS * self.SIMULATION_TIME
        capacity_utilization = (self.worker_busy_time / total_available_time) * 100
        
        # Calculate serial orders (when RPT capacity is free)
        idle_time = total_available_time - self.worker_busy_time
        self.serial_orders = int(idle_time / self.SERVICE_TIME_BASE)
        
        # Calculate opportunity costs
        serial_opportunity_costs = (self.HOURLY_RATE_RPT - self.HOURLY_RATE_SERIAL) * idle_time
        lost_opportunity_costs = len(lost_orders) * self.OPPORTUNITY_COSTS
        
        # Total costs and profits
        total_costs = manufacturing_costs + serial_opportunity_costs + lost_opportunity_costs
        total_profit = revenue - total_costs
        
        return {
            "Service Level (%)": (len(completed_orders) / len(self.orders)) * 100,
            "OTD Orders": len(otd_orders),
            "Delayed Orders": len(delayed_orders),
            "Serial Orders": self.serial_orders,
            "Total Output RPT": len(completed_orders),
            "Total Input RPT": len(self.orders),
            "Lost Orders RPT": len(lost_orders),
            "Unit Profit ($)": total_profit / len(completed_orders) if completed_orders else 0,
            "Unit Manufacturing Costs ($)": manufacturing_costs / len(completed_orders) if completed_orders else 0,
            "Total Profit ($)": total_profit,
            "Revenue ($)": revenue,
            "Manufacturing Costs ($)": manufacturing_costs,
            "Lost Order Opportunity Costs ($)": lost_opportunity_costs,
            "Serial Order Opportunity Costs ($)": serial_opportunity_costs,
            "Total Costs ($)": total_costs,
            "Average Lead Time (hours)": np.mean(lead_times) if lead_times else 0,
            "Average Capacity Utilization (%)": capacity_utilization
        }

# Run simulation
def run_simulation():
    env = simpy.Environment()
    system = ManufacturingSystem(env)
    env.process(system.order_generator())
    env.run(until=system.SIMULATION_TIME)
    return system.calculate_kpis()

# Execute and print results
if __name__ == "__main__":
    kpis = run_simulation()
    print("\nSimulation Results:")
    print("-" * 50)
    for metric, value in kpis.items():
        if isinstance(value, float):
            print(f"{metric}: {value:.1f}")
        else:
            print(f"{metric}: {value}")