import simpy
import random
import numpy as np
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional
from collections import defaultdict
import config

# Configure the logging system
logging.basicConfig(
    filename='simulation.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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
            'manufacturing_costs': 0,
            'opportunity_costs': 0,
            'backlog_costs': 0,
            'inventory_costs': 0,
            'service_level': 0,
            'unit_costs': 0,
            'unit_profit': 0,
            'mean_capacity_utilization': 0,
            'average_waiting_customer_orders': 0,
            'lead_time_summary': {'min': float('inf'), 'max': 0, 'avg': 0, 'std_dev': 0},
            'flow_time_summary': {'min': float('inf'), 'max': 0, 'avg': 0, 'std_dev': 0},

        }
        
        # Start statistics collection
        if config.TRACKING_CONFIG['COLLECT_QUEUE_STATS']:
            env.process(self.collect_statistics())

        logging.info("Simulation initialized.")

    def order_source(self):
        """Generate orders according to configured arrival pattern"""
        while self.batch_counter < config.SYSTEM_CONFIG['MAX_ORDERS']:
            batch_size = config.get_batch_size()
            self.batch_counter += 1
            
            for _ in range(batch_size):
                order = Order(
                    id=self.order_counter + 1,
                    arrival_time=self.env.now,
                    batch_id=self.batch_counter
                )
                self.order_counter += 1
                self.total_arrivals += 1
                self.stats['wip'] += 1
                logging.debug(f"Order {order.id} created at time {order.arrival_time}.")
                self.env.process(self.process_order(order))
        
            yield self.env.timeout(config.TIME_CONFIG['ARRIVAL_RATE'])

    def process_order(self, order):
        """Process an order through all machines."""
        for machine_name in config.MACHINE_CONFIG:
            order.current_machine = machine_name
            queue_name = f'Q{machine_name[1]}'

            # Push system: force the order into the queue regardless of capacity
            if config.SYSTEM_CONFIG['PUSH_SYSTEM']:
                queue_start_time = self.env.now
                self.queues[queue_name].items.append(order)  # Add order directly to queue
                logging.debug(f"Order {order.id} pushed to {queue_name} at time {self.env.now}.")
            else:  # Pull system: ensure the next stage has capacity before proceeding
                if len(self.queues[queue_name].items) >= self.queues[queue_name].capacity:
                    self.stats['blocked_orders'] += 1
                    if queue_name == 'Q1':
                        self.stats['wip'] -= 1
                    logging.warning(f"Order {order.id} blocked at {machine_name}.")
                    return
                queue_start_time = self.env.now
                yield self.queues[queue_name].put(order)

            with self.machines[machine_name].request() as request:
                yield request

                # Pull system: remove from queue during actual processing
                if not config.SYSTEM_CONFIG['PUSH_SYSTEM']:
                    yield self.queues[queue_name].get()

                wait_time = self.env.now - queue_start_time
                if machine_name == 'M1':
                    order.start_time = self.env.now
                    logging.debug(f"Order {order.id} started processing at time {order.start_time}.")
                self.stats['waiting_times'][queue_name].append(wait_time)
                logging.debug(f"Order {order.id} waited {wait_time:.2f} at {queue_name}.")

                process_start_time = self.env.now
                processing_time = config.get_processing_time(machine_name)
                yield self.env.timeout(processing_time)
                proc_time = self.env.now - process_start_time
                self.stats['processing_times'][machine_name].append(proc_time)
                logging.debug(f"Order {order.id} processed on {machine_name} in {proc_time:.2f}.")

        order.completion_time = self.env.now
        self.process_completed_order(order)


    def process_completed_order(self, order):
        """Handle completion of an order"""
        self.stats['completed_orders'] += 1
        self.stats['wip'] -= 1
        
        lead_time = order.completion_time - order.arrival_time
        flow_time = order.completion_time - order.start_time

        self.stats['lead_times'].append(lead_time)
        self.stats['flow_times'].append(flow_time)
        
        self.stats['total_revenue'] += config.FINANCIAL_CONFIG['REVENUE_PER_ORDER']
        self.stats['manufacturing_costs'] += config.FINANCIAL_CONFIG['COST_PER_ORDER']
        
        logging.info(
            f"Order {order.id} completed at {order.completion_time:.2f}. "
            f"Lead time: {lead_time:.2f}, Flow time: {flow_time:.2f}."
        )

    def collect_statistics(self):
        """Collect periodic statistics about the system"""
        while True:
            self.stats['backlog_costs']=0
            for queue_name, queue in self.queues.items():
                queue_length = len(queue.items)
                self.stats['queue_lengths'][queue_name].append(queue_length)

            
            for machine_name, machine in self.machines.items():
                utilization = machine.count / machine.capacity if machine.capacity > 0 else 0
                self.stats['machine_utilization'][machine_name].append(utilization)
                self.stats['mean_capacity_utilization'] = {
                                    machine_name: np.mean(utilization)
                                    for machine_name, utilization in self.stats['machine_utilization'].items()
                                }
            self.stats['inventory_costs'] += self.stats['wip'] * config.FINANCIAL_CONFIG['INVENTORY_COST_PER_UNIT']
            yield self.env.timeout(config.TRACKING_CONFIG['STATS_COLLECTION_INTERVAL'])

    def get_summary_statistics(self):
        """Calculate and return summary statistics"""
        logging.info("Calculating summary statistics.")
        self.stats['backlog_costs'] += config.FINANCIAL_CONFIG['BACKLOG_COST_PER_UNIT']*self.stats['blocked_orders']
        self.stats['total_costs'] = self.stats['manufacturing_costs'] + self.stats['backlog_costs']
        summary = {
                'Revenue, $': self.stats['total_revenue'],
                'Manufacturing Costs, $': self.stats['manufacturing_costs'],
                'Backlog, $': self.stats['backlog_costs'],
                'Total Costs, $': self.stats['manufacturing_costs'] + self.stats['backlog_costs'],
                'Profit, $': self.stats['total_revenue'] - self.stats['manufacturing_costs'] - self.stats['backlog_costs'],
                'Customer Orders': self.order_counter,
                'Output (orders)': self.stats['completed_orders'],
                'Backlog (orders)': self.stats['blocked_orders'],
                'WIP (orders)':self.stats['wip'],
                'Service Level, %': (self.stats['completed_orders'] / self.total_arrivals) * 100 if self.total_arrivals else 0,
                'Unit Costs, $': (self.stats['manufacturing_costs'] + self.stats['backlog_costs']) / self.stats['completed_orders'] if self.stats['completed_orders'] else 0,
                'Unit Profit, $': (
                    (self.stats['total_revenue'] - self.stats['manufacturing_costs'] - self.stats['backlog_costs']) / self.stats['completed_orders']
                    if self.stats['completed_orders'] else 0
                ),
                'Mean Capacity Utilization': {
                    machine: np.mean(utilization) * 100
                    for machine, utilization in self.stats['machine_utilization'].items()
                },
                'Average Waiting Customer times': np.mean([
                    np.mean(wait_times) for wait_times in self.stats['waiting_times'].values()
                ]) if self.stats['waiting_times'] else 0,
                'Average Lead Time': np.mean(self.stats['lead_times']) if self.stats['lead_times'] else 0,
                'Lead Time Min': min(self.stats['lead_times']) if self.stats['lead_times'] else 0,
                'Lead Time Max': max(self.stats['lead_times']) if self.stats['lead_times'] else 0,
                'Lead Time Std Dev': np.std(self.stats['lead_times']) if self.stats['lead_times'] else 0,
                'Average Flow Time': np.mean(self.stats['flow_times']) if self.stats['flow_times'] else 0,
                'Flow Time Min': min(self.stats['flow_times']) if self.stats['flow_times'] else 0,
                'Flow Time Max': max(self.stats['flow_times']) if self.stats['flow_times'] else 0,
                'Flow Time Std Dev': np.std(self.stats['flow_times']) if self.stats['flow_times'] else 0,
            }

        return summary
    

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