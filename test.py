from dataclasses import dataclass
from typing import Dict, List, Optional
import random
import simpy
import numpy as np
from collections import defaultdict
import config
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class Order:
    """Represents a manufacturing order in the system"""
    id: int
    arrival_time: float
    batch_id: int
    start_time: Optional[float] = None
    completion_time: Optional[float] = None
    current_machine: Optional[str] = None
    withdrawn: bool = False

class ManufacturingLineSimulation:
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.order_counter = 0
        self.batch_counter = 0
        self.total_arrivals = 0
        
        # Create resources (machines)
        self.machines = {
            name: simpy.Resource(env, config.MACHINE_CONFIG[name].capacity)
            for name in config.MACHINE_CONFIG
        }
        
        # Create stores for queues with limited capacity
        self.queues = {
            name: simpy.Store(env, capacity=config.QUEUE_CONFIG[name].capacity)
            for name in config.QUEUE_CONFIG
        }
        
        # Statistics tracking
        self.stats = {
            'queue_lengths': defaultdict(list),
            'machine_utilization': defaultdict(list),
            'completed_orders': 0,
            'blocked_orders': 0,
            'wip': 0,
            'waiting_times': defaultdict(list),
            'processing_times': defaultdict(list),
            'lead_times': [],
            'flow_times': [],
            'total_revenue': 0,
            'total_costs': 0,
            'opportunity_costs': 0,
            'backlog_costs': 0,
            'inventory_costs': 0
        }
        
        # Start statistics collection
        if config.TRACKING_CONFIG['COLLECT_QUEUE_STATS']:
            env.process(self.collect_statistics())

    def order_source(self):
        """Generate orders according to configured arrival pattern"""
        while self.total_arrivals < config.SYSTEM_CONFIG['MAX_ORDERS']:
            # Generate batch of orders
            batch_size = config.get_batch_size()
            self.batch_counter += 1
            logging.info(f"Generated batch {self.batch_counter} with size {batch_size}")
            
            for _ in range(batch_size):
                if self.total_arrivals < config.SYSTEM_CONFIG['MAX_ORDERS']:
                    order = Order(
                        id=self.order_counter + 1,
                        arrival_time=self.env.now,
                        batch_id=self.batch_counter
                    )
                    self.order_counter += 1
                    self.total_arrivals += 1
                    self.stats['wip'] += 1
                    logging.info(f"Order {order.id} generated at time {self.env.now:.2f}")
                    
                    # Start processing the order
                    self.env.process(self.process_order(order))
            
            # Wait for next arrival according to rate
            yield self.env.timeout(config.TIME_CONFIG['ARRIVAL_RATE'])

    def process_order(self, order):
        """Process an order through all machines"""

        # Process through each machine in sequence
        for machine_name in config.MACHINE_CONFIG:
            order.current_machine = machine_name
            queue_name = f'Q{machine_name[1]}'
            
            # Try to enter queue
            if len(self.queues[queue_name].items) >= self.queues[queue_name].capacity:
                self.stats['blocked_orders'] += 1
                self.stats['opportunity_costs'] += config.FINANCIAL_CONFIG['OPPORTUNITY_COST_PER_BLOCKED_ORDER']
                logging.warning(f"Order {order.id} blocked at queue {queue_name}")
                return
            
            queue_start_time = self.env.now
            if order.start_time is None:
                order.start_time = queue_start_time
            yield self.queues[queue_name].put(order)
            logging.info(f"Order {order.id} entered queue {queue_name} at time {self.env.now:.2f}")
            
            # Request machine
            with self.machines[machine_name].request() as request:
                yield request
                
                # Remove from queue
                yield self.queues[queue_name].get()
                self.stats['waiting_times'][queue_name].append(self.env.now - queue_start_time)
                logging.info(f"Order {order.id} started processing on {machine_name} at time {self.env.now:.2f}")
                
                # Process the order
                processing_time = config.get_processing_time(machine_name)
                yield self.env.timeout(processing_time)
                logging.info(f"Order {order.id} processing on {machine_name} with time {processing_time:.2f}")
                
                self.stats['processing_times'][machine_name].append(
                    self.env.now - queue_start_time
                )

        # Order completed successfully
        order.completion_time = self.env.now
        logging.info(f"Order {order.id} completed at time {self.env.now:.2f}")
        self.process_completed_order(order)

    def process_completed_order(self, order):
        """Handle completion of an order"""
        self.stats['completed_orders'] += 1
        self.stats['wip'] -= 1
        
        # Calculate times
        lead_time = order.completion_time - order.arrival_time
        flow_time = order.completion_time - order.start_time
        
        self.stats['lead_times'].append(lead_time)
        self.stats['flow_times'].append(flow_time)
        
        # Calculate financials
        self.stats['total_revenue'] += config.FINANCIAL_CONFIG['REVENUE_PER_ORDER']
        self.stats['total_costs'] += config.FINANCIAL_CONFIG['COST_PER_ORDER']

    def collect_statistics(self):
        """Collect periodic statistics about the system"""
        while True:
            # Collect queue lengths
            for queue_name, queue in self.queues.items():
                self.stats['queue_lengths'][queue_name].append(len(queue.items))
                self.stats['backlog_costs'] += len(queue.items) * config.FINANCIAL_CONFIG['BACKLOG_COST_PER_UNIT']
            
            # Collect machine utilization
            for machine_name, machine in self.machines.items():
                utilization = machine.count / machine.capacity if machine.capacity > 0 else 0
                self.stats['machine_utilization'][machine_name].append(utilization)
            
            # Collect inventory costs
            self.stats['inventory_costs'] += self.stats['wip'] * config.FINANCIAL_CONFIG['INVENTORY_COST_PER_UNIT']
            
            yield self.env.timeout(config.TRACKING_CONFIG['STATS_COLLECTION_INTERVAL'])

    def get_summary_statistics(self):
        """Calculate and return summary statistics"""
        return {
            'Completed Orders': self.stats['completed_orders'],
            'Blocked Orders': self.stats['blocked_orders'],
            'Average Lead Time': np.mean(self.stats['lead_times']) if self.stats['lead_times'] else 0,
            'Average Flow Time': np.mean(self.stats['flow_times']) if self.stats['flow_times'] else 0,
            'Machine Utilization': {
                machine: np.mean(utilization) 
                for machine, utilization in self.stats['machine_utilization'].items()
            },
            'Average Queue Lengths': {
                queue: np.mean(lengths)
                for queue, lengths in self.stats['queue_lengths'].items()
            },
            'Average Waiting Times': {
                queue: np.mean(times) if times else 0
                for queue, times in self.stats['waiting_times'].items()
            },
            'Final WIP': self.stats['wip'],
            'Total Revenue': self.stats['total_revenue'],
            'Total Costs': self.stats['total_costs'],
            'Total Profit': self.stats['total_revenue'] - self.stats['total_costs'],
            'Opportunity Costs': self.stats['opportunity_costs'],
            'Backlog Costs': self.stats['backlog_costs'],
            'Inventory Costs': self.stats['inventory_costs']
        }

def run_simulation():
    """Run the complete simulation"""
    # Set random seed
    random.seed(config.SYSTEM_CONFIG['RANDOM_SEED'])
    
    # Create SimPy environment
    env = simpy.Environment()
    
    # Create and set up simulation
    simulation = ManufacturingLineSimulation(env)
    
    # Start order generation
    env.process(simulation.order_source())
    
    # Run simulation
    env.run(until=config.TIME_CONFIG['SIM_TIME'])
    
    return simulation.get_summary_statistics()

if __name__ == "__main__":
    # Run simulation and print results
    results = run_simulation()
    print("\nExperiment 1 Results:")
    for metric, value in results.items():
        if isinstance(value, dict):
            print(f"\n{metric}:")
            for k, v in value.items():
                print(f"  {k}: {v:.2f}")
        else:
            print(f"{metric}: {value:.2f}")



