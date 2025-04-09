import simpy
import random
import math
import logging
from enum import Enum
import numpy as np
# Simulation Parameters
SIM_TIME = 365  # Simulate for 1 year (365 days)
DAILY_DEMAND = 50  # Fixed daily demand per customer
SERVICE_LEVEL = 0.90  # Desired service level (90%)

# Customer Configuration
CUSTOMERS = {
    "Poznan": {"dc": "DC_Berlin"},
    "Hanover": {"dc": "DC_Berlin"},
    "Hamburg": {"dc": "DC_Berlin"},
    "Vienna": {"dc": "DC_Prague"},
    "Nuremberg": {"dc": "DC_Prague"},
    "Munich": {"dc": "DC_Prague"}
}

# Product Configuration with Customer Allocation
PRODUCTS = {
    "PC": {
        "customers": {
            "Poznan": DAILY_DEMAND,
            "Vienna": DAILY_DEMAND
        },
        "selling_price": 1150,
        "cost_price": 350,
        "volume": 0.1  # m3
    },
    "Monitor": {
        "customers": {
            "Hanover": DAILY_DEMAND,
            "Nuremberg": DAILY_DEMAND
        },
        "selling_price": 850,
        "cost_price": 250,
        "volume": 0.1  # m3
    },
    "MFP": {
        "customers": {
            "Hamburg": DAILY_DEMAND,
            "Munich": DAILY_DEMAND
        },
        "selling_price": 700,
        "cost_price": 200,
        "volume": 0.1  # m3
    }
    
}

# Distribution Center Configuration
DCS = {
    "DC_Berlin": {
        "fixed_cost_per_day": 2500,
        "locations_served": ["Poznan", "Hanover", "Hamburg"]
    },
    "DC_Prague": {
        "fixed_cost_per_day": 1500,
        "locations_served": ["Vienna", "Nuremberg", "Munich"]
    }
}

# Cost Parameters
INTEREST_RATE = 0.1  # 10% per year
CARRYING_COST_PER_M3_PER_DAY = 0.01  # $0.01 per m3 per day
TRANSPORT_COST_PER_UNIT  = 1
# Lead Times
SUPPLIER_TO_DC_LEADTIME = 0.7  # days
DC_TO_CUSTOMER_LEADTIME_MIN = 1.8  # days
DC_TO_CUSTOMER_LEADTIME_MAX = 1.95  # days

# Inventory Control Policies
INVENTORY_POLICY = {
    "type": "s_S",
    "s": 57,  # Minimum level
    "S": 113  # Maximum level
}

# Transportation Policies
TRANSPORT_POLICIES = {
    "supplier_to_dc": {"min_load": 60, "max_load": 60},  # Full Truckload (60 m3)
    "dc_to_customer": {"min_load": 0, "max_load": 20}    # Less Than Truckload (20 m3)
}


# Configure logging
logging.basicConfig(
    filename='simulation.log',  # Name of the log file
    level=logging.INFO,         # Log level (INFO, DEBUG, WARNING, etc.)
    format='%(asctime)s - %(levelname)s - %(message)s'  # Log message format
)

# Function to replace print statements with logs
def log(message, level="info"):
    if level == "info":
        logging.info(message)
    elif level == "warning":
        logging.warning(message)
    elif level == "debug":
        logging.debug(message)
    elif level == "error":
        logging.error(message)
    else:
        logging.info(message)


# Add new inventory policy types
class InventoryPolicyType(Enum):
    MIN_MAX = "min_max"
    MIN_MAX_SAFETY = "min_max_safety"
    RQ = "rq"
    UNLIMITED = "unlimited"
    ORDER_ON_DEMAND = "order_on_demand"
    MRP = "mrp"
    REGULAR = "regular"
    REGULAR_SAFETY = "regular_safety"
    NO_REPLENISHMENT = "no_replenishment"
    XDOCK = "xdock"

class InventoryPolicy:
    def __init__(self, policy_type, **kwargs):
        self.policy_type = policy_type
        self.params = kwargs
        
        # Initialize safety stock calculations if needed
        if 'service_level' in kwargs:
            self.z_score = self._calculate_z_score(kwargs['service_level'])
    
    def _calculate_z_score(self, service_level):
        """Convert service level to Z-score for safety stock calculations."""
        from scipy.stats import norm
        return norm.ppf(service_level)
    
    def _calculate_safety_stock(self, lead_time_std, demand_std):
        """Calculate safety stock based on lead time and demand variability."""
        return self.z_score * math.sqrt(lead_time_std**2 + demand_std**2)
    
    def _calculate_eoq(self, annual_demand, ordering_cost, holding_cost):
        """Calculate Economic Order Quantity."""
        return math.sqrt((2 * annual_demand * ordering_cost) / holding_cost)
    
    def calculate_order_quantity(self, current_inventory, params):
        """Calculate order quantity based on policy type."""
        if self.policy_type == InventoryPolicyType.MIN_MAX:
            if current_inventory <= self.params['s']:
                return self.params['S'] - current_inventory
            return 0
            
        elif self.policy_type == InventoryPolicyType.MIN_MAX_SAFETY:
            safety_stock = self._calculate_safety_stock(
                params['lead_time_std'],
                params['demand_std']
            )
            if current_inventory <= (self.params['s'] + safety_stock):
                return (self.params['S'] + safety_stock) - current_inventory
            return 0
            
        elif self.policy_type == InventoryPolicyType.RQ:
            if current_inventory <= self.params['R']:
                return self.params['Q']
            return 0
            
        elif self.policy_type == InventoryPolicyType.UNLIMITED:
            return params['demanded_quantity']
            
        elif self.policy_type == InventoryPolicyType.ORDER_ON_DEMAND:
            return params['demanded_quantity']
            
        elif self.policy_type == InventoryPolicyType.MRP:
            safety_stock = self._calculate_safety_stock(
                params['lead_time_std'],
                params['demand_std']
            )
            projected_inventory = current_inventory - params['forecasted_demand']
            if projected_inventory < safety_stock:
                return safety_stock - projected_inventory
            return 0
            
        elif self.policy_type == InventoryPolicyType.REGULAR:
            if params['current_time'] % self.params['period'] == 0:
                return self.params['q']
            return 0
            
        elif self.policy_type == InventoryPolicyType.REGULAR_SAFETY:
            safety_stock = self._calculate_safety_stock(
                params['lead_time_std'],
                params['demand_std']
            )
            if params['current_time'] % self.params['period'] == 0:
                return self.params['q'] + (safety_stock - current_inventory)
            return 0
            
        elif self.policy_type == InventoryPolicyType.NO_REPLENISHMENT:
            return 0
            
        elif self.policy_type == InventoryPolicyType.XDOCK:
            return params['demanded_quantity']
            
        return 0

# Update the INVENTORY_POLICY configuration
INVENTORY_POLICIES = {
    "PC": {
        "type": InventoryPolicyType.MIN_MAX,
        "params": {"s": 57, "S": 113}
    },
    "Monitor": {
        "type": InventoryPolicyType.MIN_MAX,
        "params": {"s": 57, "S": 113}
    },
    "MFP": {
        "type": InventoryPolicyType.MIN_MAX,
        "params": {"s": 57, "S": 113}
    }

}



class TransportMode(Enum):
    FTL = "ftl"  # Full Truckload
    LTL = "ltl"  # Less Than Truckload

class TransportPolicy:
    def __init__(self, mode, capacity, min_fill_rate=0.0, max_wait_time=float('inf')):
        self.mode = mode
        self.capacity = capacity  # in m3
        self.min_fill_rate = min_fill_rate  # minimum fill rate to dispatch
        self.max_wait_time = max_wait_time  # maximum waiting time for consolidation
        self.current_load = 0
        self.waiting_orders = []
        self.wait_start_time = None

    def can_dispatch(self, current_time):
        """Determine if shipment should be dispatched based on policy."""
        if self.mode == TransportMode.FTL:
            # Dispatch if full or max wait time reached
            return (self.current_load >= self.capacity * self.min_fill_rate or
                   (self.wait_start_time and 
                    current_time - self.wait_start_time >= self.max_wait_time))
        else:  # LTL
            # Dispatch immediately for LTL
            return True

    def add_order(self, order, current_time):
        """Add order to current load and return whether to dispatch."""
        if self.current_load == 0:
            self.wait_start_time = current_time
        
        self.current_load += order['volume']
        self.waiting_orders.append(order)
        
        return self.can_dispatch(current_time)

    def get_transport_cost(self):
        """Calculate transport cost based on mode and utilization."""
        if self.mode == TransportMode.FTL:
            return TRANSPORT_COST_PER_UNIT * math.ceil(self.current_load / self.capacity)
        else:  # LTL
            # LTL typically costs more per unit
            ltl_premium = 1.5
            return TRANSPORT_COST_PER_UNIT * ltl_premium * (self.current_load / self.capacity)

    def clear_shipment(self):
        """Clear current shipment and return orders."""
        orders = self.waiting_orders
        self.current_load = 0
        self.waiting_orders = []
        self.wait_start_time = None
        return orders

# Update transport policies configuration
TRANSPORT_POLICIES = {
    "supplier_to_dc": {
        "mode": TransportMode.FTL,
        "capacity": 60,  # m3
        "min_fill_rate": 0.9,  # 90% minimum fill rate
        "max_wait_time": 3  # maximum 3 days wait
    },
    "dc_to_customer": {
        "mode": TransportMode.LTL,
        "capacity": 20,  # m3
        "min_fill_rate": 0.0,  # no minimum for LTL
        "max_wait_time": 1  # maximum 1 day wait
    }
}


        

# ... (rest of the original code remains the same)
class DistributionCenter:
    def __init__(self, env, name, products):
        self.env = env
        self.name = name
        self.fixed_cost_per_day = DCS[name]["fixed_cost_per_day"]
        self.locations_served = DCS[name]["locations_served"]
        self.total_fixed_cost = 0
        self.total_carrying_cost = 0
        self.total_interest_cost = 0
        self.total_revenue_cost = 0
        self.total_order_count = 0
        # Debug counters
        self.debug_order_count = 0
        self.debug_stockout_count = 0
        self.debug_min_inventory = float('inf')
        self.debug_max_inventory = 0
        
        # Initialize product tracking with location-specific metrics
        self.products = {product: {
            'inventory': 57,  # Initial inventory
            'orders_fulfilled': {location: 0 for location in self.locations_served},
            'orders_backlogged': {location: 0 for location in self.locations_served},
            'transport_cost': 0,
            'inventory_cost': 0,
            'revenue': 0,
            'cogs': 0,
            'daily_carrying_cost': 0,
            'daily_interest_cost': 0,
            # Debug metrics
            'debug_total_ordered': 0,
            'debug_stockout_days': 0,
            'debug_inventory_history': []
        } for product in products if self.serves_product(product)}
        # Initialize inventory policies for each product
        self.inventory_policies = {
            product: InventoryPolicy(
                INVENTORY_POLICIES[product]["type"],
                **INVENTORY_POLICIES[product]["params"]
            )
            for product in products if self.serves_product(product)
        }
        # Initialize transport policies
        self.transport_policies = {
            "inbound": TransportPolicy(
                mode=TRANSPORT_POLICIES["supplier_to_dc"]["mode"],
                capacity=TRANSPORT_POLICIES["supplier_to_dc"]["capacity"],
                min_fill_rate=TRANSPORT_POLICIES["supplier_to_dc"]["min_fill_rate"],
                max_wait_time=TRANSPORT_POLICIES["supplier_to_dc"]["max_wait_time"]
            ),
            "outbound": TransportPolicy(
                mode=TRANSPORT_POLICIES["dc_to_customer"]["mode"],
                capacity=TRANSPORT_POLICIES["dc_to_customer"]["capacity"],
                min_fill_rate=TRANSPORT_POLICIES["dc_to_customer"]["min_fill_rate"],
                max_wait_time=TRANSPORT_POLICIES["dc_to_customer"]["max_wait_time"]
            )
        }
        
        # Add transportation metrics
        self.transport_metrics = {
            "inbound": {
                "total_shipments": 0,
                "total_volume": 0,
                "total_cost": 0,
                "avg_utilization": 0
            },
            "outbound": {
                "total_shipments": 0,
                "total_volume": 0,
                "total_cost": 0,
                "avg_utilization": 0
            }
        }

   
        # Start processes
        for product in self.products:
            self.env.process(self.replenish_inventory(product))
            self.env.process(self.fulfill_orders(product))
            self.env.process(self.monitor_inventory(product))  # New monitoring process
        self.env.process(self.calculate_daily_costs())
        self.env.process(self.print_daily_summary())  # New daily summary process
    

    def serves_product(self, product):
        """Check if this DC serves any customers for this product."""
        return any(location in self.locations_served 
                  for location in PRODUCTS[product]['customers'].keys())

    def get_daily_demand(self, product):
        """Calculate total daily demand for a product from served locations."""
        return sum(PRODUCTS[product]['customers'].get(location, 0) 
                  for location in self.locations_served 
                  if location in PRODUCTS[product]['customers'])

    def monitor_inventory(self, product):
            """Monitor and record inventory levels."""
            while True:
                current_inventory = self.products[product]['inventory']
                self.products[product]['debug_inventory_history'].append({
                    'day': round(self.env.now, 2),
                    'level': current_inventory
                })
                
                # Update min/max inventory levels
                self.debug_min_inventory = min(self.debug_min_inventory, current_inventory)
                self.debug_max_inventory = max(self.debug_max_inventory, current_inventory)
                
                # Check for stockout
                if current_inventory <= 0:
                    self.products[product]['debug_stockout_days'] += 1
                    log(f"⚠️ {round(self.env.now,2)}: STOCKOUT WARNING - {self.name} has no {product} in stock!")
                
                yield self.env.timeout(1)

    def print_daily_summary(self):
        """Print daily summary of key metrics."""
        while True:
            if int(self.env.now) % 7 == 0:  # Weekly summary
                log(f"\n📊 Weekly Summary for {self.name} - Day {int(self.env.now)}")
                for product in self.products:
                    inv = self.products[product]['inventory']
                    backlog = sum(self.products[product]['orders_backlogged'].values())
                    fulfilled = sum(self.products[product]['orders_fulfilled'].values())
                    log(f"""
                        {product}:
                        - Current Inventory: {inv} units
                        - Orders Fulfilled: {fulfilled}
                        - Backlogged Orders: {backlog}
                        - Stockout Days: {self.products[product]['debug_stockout_days']}
                        - Total Ordered: {self.products[product]['debug_total_ordered']}
                        - Min/Max Inventory: {min([h['level'] for h in self.products[product]['debug_inventory_history']])}/{max([h['level'] for h in self.products[product]['debug_inventory_history']])}
                        """)
            yield self.env.timeout(1)
    
    def calculate_daily_costs(self):
        """Calculate daily fixed and carrying costs."""
        while True:
            self.total_fixed_cost += self.fixed_cost_per_day
            
            for product in self.products:
                inventory = self.products[product]['inventory']
                volume = PRODUCTS[product]['volume']
                cost_price = PRODUCTS[product]['cost_price']
                
                # Calculate carrying cost based on volume
                carrying_cost = inventory * volume * CARRYING_COST_PER_M3_PER_DAY
                self.products[product]['daily_carrying_cost'] += carrying_cost
                self.total_carrying_cost += carrying_cost
                
                # Calculate interest cost based on inventory value
                daily_interest = (inventory * cost_price * INTEREST_RATE) / 365
                self.products[product]['daily_interest_cost'] += daily_interest
                self.total_interest_cost += daily_interest
                
            yield self.env.timeout(1)

    def get_leadtime_to_customer(self):
        """Calculate variable lead time based on DC operations."""
        return random.uniform(DC_TO_CUSTOMER_LEADTIME_MIN, DC_TO_CUSTOMER_LEADTIME_MAX)

    def replenish_inventory(self, product):
            """Replenish inventory based on the selected policy."""
            while True:
                current_inventory = self.products[product]['inventory']
                
                # Calculate order quantity based on policy
                order_params = {
                    'current_time': self.env.now,
                    'lead_time_std': 0.1,  # Example value
                    'demand_std': 10,      # Example value
                    'forecasted_demand': self.get_daily_demand(product),
                    'demanded_quantity': self.get_daily_demand(product)
                }
                
                order_quantity = self.inventory_policies[product].calculate_order_quantity(
                    current_inventory,
                    order_params
                )
                
                if order_quantity > 0:
                    self.debug_order_count += 1
                    self.products[product]['debug_total_ordered'] += order_quantity
                    log(f"""
                        🔄 REPLENISHMENT ORDER - Day {round(self.env.now,2)}
                        DC: {self.name}
                        Product: {product}
                        Policy: {self.inventory_policies[product].policy_type.value}
                        Current Inventory: {current_inventory}
                        Order Quantity: {order_quantity}
                        Total Orders Made: {self.debug_order_count}
                        """)
                    yield self.env.process(self.place_order(product, order_quantity))
                
                yield self.env.timeout(1)


    def place_order(self, product, quantity):
        """Place order with supplier considering FTL constraints."""
        cost = quantity * PRODUCTS[product]['cost_price']
        self.products[product]['cogs'] += cost
        
        # Create order
        order = {
            'product': product,
            'quantity': quantity,
            'volume': quantity * PRODUCTS[product]['volume'],
            'order_time': self.env.now
        }
        
        # Add to inbound transport policy
        should_dispatch = self.transport_policies["inbound"].add_order(order, self.env.now)
        
        if should_dispatch:
            # Calculate transport metrics
            transport_cost = self.transport_policies["inbound"].get_transport_cost()
            utilization = self.transport_policies["inbound"].current_load / self.transport_policies["inbound"].capacity
            
            # Update metrics
            self.transport_metrics["inbound"]["total_shipments"] += 1
            self.transport_metrics["inbound"]["total_volume"] += self.transport_policies["inbound"].current_load
            self.transport_metrics["inbound"]["total_cost"] += transport_cost
            self.transport_metrics["inbound"]["avg_utilization"] = (
                (self.transport_metrics["inbound"]["avg_utilization"] * 
                 (self.transport_metrics["inbound"]["total_shipments"] - 1) + 
                 utilization) / self.transport_metrics["inbound"]["total_shipments"]
            )
            
            # Process orders
            orders = self.transport_policies["inbound"].clear_shipment()
            
            log(f"""
                📦 CONSOLIDATED SHIPMENT DISPATCHED - Day {round(self.env.now,2)}
                DC: {self.name}
                Transport Mode: {self.transport_policies["inbound"].mode.value}
                Orders: {len(orders)}
                Total Volume: {sum(o['volume'] for o in orders):.2f} m3
                Utilization: {utilization:.2%}
                Transport Cost: ${transport_cost:,.2f}
                Expected Arrival: Day {round(self.env.now + SUPPLIER_TO_DC_LEADTIME,2)}
                """)
            
            yield self.env.timeout(SUPPLIER_TO_DC_LEADTIME)
            
            # Process received orders
            for order in orders:
                self.products[order['product']]['inventory'] += order['quantity']
                
                log(f"""
                    ✅ ORDER RECEIVED - Day {round(self.env.now,2)}
                    DC: {self.name}
                    Product: {order['product']}
                    Quantity: {order['quantity']}
                    New Inventory: {self.products[order['product']]['inventory']}
                    Order-to-Delivery Time: {round(self.env.now - order['order_time'],2)} days
                    """)

    def fulfill_orders(self, product):
        """Fulfill customer orders with LTL shipping."""
        while True:
            for location in self.locations_served:
                if location in PRODUCTS[product]['customers']:
                    daily_demand = PRODUCTS[product]['customers'][location]
                    current_inventory = self.products[product]['inventory']
                    
                    # Increment total order count once per order
                    self.total_order_count += 1
                    
                    if current_inventory >= daily_demand:
                        # Fulfill the order
                        self.products[product]['orders_fulfilled'][location] += 1
                        self.products[product]['inventory'] -= daily_demand
                        
                        # Calculate revenue
                        revenue = daily_demand * PRODUCTS[product]['selling_price']
                        self.products[product]['revenue'] += revenue
                        self.total_revenue_cost += revenue
                        
                        log(f"""
                            ✅ ORDER FULFILLED - Day {round(self.env.now,2)}
                            DC: {self.name}
                            Product: {product}
                            Location: {location}
                            Quantity: {daily_demand}
                            Revenue: ${revenue:,.2f}
                            Remaining Inventory: {self.products[product]['inventory']}
                            Total Orders Fulfilled: {sum(self.products[product]['orders_fulfilled'].values())}
                            """)
                    else:
                        # Backlog the order
                        self.products[product]['orders_backlogged'][location] += 1
                        log(f"""
                            ❌ ORDER BACKLOGGED - Day {round(self.env.now,2)}
                            DC: {self.name}
                            Product: {product}
                            Location: {location}
                            Demanded: {daily_demand}
                            Available: {current_inventory}
                            Total Orders Backlogged: {sum(self.products[product]['orders_backlogged'].values())}
                            """)
            
            yield self.env.timeout(1)

    def calculate_kpis(self):
        """Calculate KPIs including transportation costs."""
        kpis = {
            "DC_Fixed_Cost": self.total_fixed_cost,
            "Total_Carrying_Cost": self.total_carrying_cost,
            "Total_Interest_Cost": self.total_interest_cost,
            "Total_Revenue_Cost": self.total_revenue_cost,  # This should now include revenue
            "Products": {}
        }
        
        total_transport_cost = 0
        total_orders_fulfilled = 0
        total_orders_backlogged = 0
        
        for product in self.products:
            transport_cost = self.products[product]['transport_cost']
            total_transport_cost += transport_cost
            
            product_kpis = {
                "Revenue": self.products[product]['revenue'],
                "COGS": self.products[product]['cogs'],
                "Transport_Cost": transport_cost,
                "Gross_Profit": (self.products[product]['revenue'] - 
                                self.products[product]['cogs'] - 
                                transport_cost),
                "Carrying_Cost": self.products[product]['daily_carrying_cost'],
                "Interest_Cost": self.products[product]['daily_interest_cost'],
                "Current_Inventory": self.products[product]['inventory'],
                "Location_Performance": {}
            }

            # Calculate location-specific metrics
            for location in self.locations_served:
                if location in PRODUCTS[product]['customers']:
                    fulfilled = self.products[product]['orders_fulfilled'][location]
                    backlogged = self.products[product]['orders_backlogged'][location]
                    service_level = fulfilled / (fulfilled + backlogged) if (fulfilled + backlogged) > 0 else 0
                    total_orders_fulfilled += fulfilled
                    total_orders_backlogged += backlogged
                    product_kpis["Location_Performance"][location] = {
                        "Orders_Fulfilled": fulfilled,
                        "Orders_Backlogged": backlogged,
                        "Service_Level": service_level
                    }
            
            kpis["Products"][product] = product_kpis
        
        # Calculate total profit including transport costs
        total_revenue = sum(kpis["Products"][p]["Revenue"] for p in self.products)
        total_cogs = sum(kpis["Products"][p]["COGS"] for p in self.products)
        total_costs = (total_cogs + 
                    self.total_fixed_cost + 
                    self.total_carrying_cost + 
                    self.total_interest_cost + 
                    total_transport_cost)
        
        kpis["Total_Transport_Cost"] = total_transport_cost
        kpis["Total_Profit"] = total_revenue - total_costs
        kpis["Total_Revenue"] = total_revenue
        kpis["Total_Revenue_Cost"] = total_revenue  # Update to reflect total revenue
        kpis["Total_Orders_Fulfilled"] = total_orders_fulfilled
        kpis["Total_Orders_Backlogged"] = total_orders_backlogged
        kpis["Total_Orders_Count"] = self.total_order_count
        
        # Verify that the sum of fulfilled and backlogged orders equals the total order count
        assert kpis["Total_Orders_Fulfilled"] + kpis["Total_Orders_Backlogged"] == kpis["Total_Orders_Count"], \
            "Total orders fulfilled and backlogged do not match the total order count."
        
        # Add transport KPIs
        kpis["Transport_Metrics"] = {
            "Inbound": {
                "Total_Shipments": self.transport_metrics["inbound"]["total_shipments"],
                "Total_Volume": self.transport_metrics["inbound"]["total_volume"],
                "Total_Cost": self.transport_metrics["inbound"]["total_cost"],
                "Avg_Utilization": self.transport_metrics["inbound"]["avg_utilization"]
            },
            "Outbound": {
                "Total_Shipments": self.transport_metrics["outbound"]["total_shipments"],
                "Total_Volume": self.transport_metrics["outbound"]["total_volume"],
                "Total_Cost": self.transport_metrics["outbound"]["total_cost"],
                "Avg_Utilization": self.transport_metrics["outbound"]["avg_utilization"]
            }
        }
        
        return kpis
def run_simulation():
    env = simpy.Environment()
    dcs = [DistributionCenter(env, name, PRODUCTS.keys()) for name in DCS]
    env.run(until=SIM_TIME)
    return {dc.name: dc.calculate_kpis() for dc in dcs}

if __name__ == "__main__":
    results = run_simulation()
    for dc_name, kpis in results.items():
        print(f"\nResults for {dc_name}:")
        print(f"Fixed Cost: ${kpis['DC_Fixed_Cost']:,.2f}")
        print(f"Total Carrying Cost: ${kpis['Total_Carrying_Cost']:,.2f}")
        print(f"Total Interest Cost: ${kpis['Total_Interest_Cost']:,.2f}")
        print(f"Total Profit: ${kpis['Total_Profit']:,.2f}")
        print(f"Total Revenue Cost: ${kpis['Total_Revenue_Cost']:,.2f}")
        print(f"Total Orders Fulfilled: {kpis['Total_Orders_Fulfilled']:,.2f}")
        print(f"Total Orders Backlogged: {kpis['Total_Orders_Backlogged']:,.2f}")
        print(f"Total Orders Count: {kpis['Total_Orders_Count']:,.2f}")
        print("\nProduct-specific metrics:")
        for product, metrics in kpis["Products"].items():
            print(f"\n{product}:")
            print(f"Revenue: ${metrics['Revenue']:,.2f}")
            print(f"COGS: ${metrics['COGS']:,.2f}")
            print(f"Gross Profit: ${metrics['Gross_Profit']:,.2f}")
            print("\nLocation Performance:")
            for location, performance in metrics["Location_Performance"].items():
                print(f"  {location}:")
                print(f"    Orders Fulfilled: {performance['Orders_Fulfilled']}")
                print(f"    Orders Backlogged: {performance['Orders_Backlogged']}")
                print(f"    Service Level: {performance['Service_Level']:.2%}")