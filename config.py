from dataclasses import dataclass
from typing import Dict, List, Tuple
import random
from scipy.stats import truncnorm

@dataclass
class MachineConfig:
    """Configuration for each machine in the production line"""
    min_time: float
    mode_time: float
    max_time: float
    capacity: int

@dataclass
class QueueConfig:
    """Configuration for queues in the production line"""
    capacity: int

# Time-related configurations
TIME_CONFIG = {
    'SIM_TIME': 100,  # 100 days
    'ARRIVAL_RATE': 1,  # 1 per second
    'MIN_BATCH_SIZE': 3,
    'MAX_BATCH_SIZE': 7,
}

# Machine configurations with triangular distributions
MACHINE_CONFIG = {
    'M1': MachineConfig(min_time=1, mode_time=2, max_time=3, capacity=2),
    'M2': MachineConfig(min_time=0.5, mode_time=1, max_time=1.5, capacity=1),
    'M3': MachineConfig(min_time=0.5, mode_time=1, max_time=1.5, capacity=1),
    'M4': MachineConfig(min_time=0.5, mode_time=1, max_time=1.5, capacity=1),
}

# Queue configurations
QUEUE_CONFIG = {
    'Q1': QueueConfig(capacity=50),
    'Q2': QueueConfig(capacity=50),
    'Q3': QueueConfig(capacity=50),
    'Q4': QueueConfig(capacity=50),
}

# System configuration
SYSTEM_CONFIG = {
    'PUSH_SYSTEM': False,  # Force pushing enabled
    'DISPATCH_RULE': 'FIFO',
    'MAX_ORDERS': 100,
    'RANDOM_SEED': 42,
}

# Financial and cost-related configurations
FINANCIAL_CONFIG = {
    'REVENUE_PER_ORDER': 15,
    'COST_PER_ORDER': 11,
    'OPPORTUNITY_COST_PER_BLOCKED_ORDER': 20,
    'BACKLOG_COST_PER_UNIT': 4,
    'INVENTORY_COST_PER_UNIT': 3,
}

# Helper functions
def get_batch_size() -> int:
    """Generate random batch size using uniform discrete distribution"""
    return random.randint(TIME_CONFIG['MIN_BATCH_SIZE'], 
                         TIME_CONFIG['MAX_BATCH_SIZE'])

def get_processing_time(machine: str) -> float:
    """Get processing time using triangular distribution for specified machine"""
    config = MACHINE_CONFIG[machine]
    return random.triangular(config.min_time, config.mode_time, config.max_time)

# Performance tracking configuration
TRACKING_CONFIG = {
    'COLLECT_QUEUE_STATS': True,
    'COLLECT_UTILIZATION_STATS': True,
    'STATS_COLLECTION_INTERVAL': 1.0
}