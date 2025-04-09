# config.py
from pydantic import BaseModel
from typing import Dict, List

class CustomerConfig(BaseModel):
    dc: str

class ProductCustomer(BaseModel):
    customers: Dict[str, int]
    selling_price: float
    cost_price: float 
    volume: float

class DCConfig(BaseModel):
    fixed_cost_per_day: float
    locations_served: List[str]

class TransportPolicy(BaseModel):
    min_load: int
    max_load: int

class InventoryPolicy(BaseModel):
    type: str
    s: int  # Minimum level
    S: int  # Maximum level

class SimulationConfig(BaseModel):
    sim_time: int = 365
    daily_demand: int = 50
    service_level: float = 0.90
    customers: Dict[str, CustomerConfig]
    products: Dict[str, ProductCustomer]
    dcs: Dict[str, DCConfig]
    interest_rate: float = 0.1
    carrying_cost_per_m3_per_day: float = 0.01
    transport_cost_per_unit: float = 1
    supplier_to_dc_leadtime: float = 0.7
    dc_to_customer_leadtime_min: float = 1.8
    dc_to_customer_leadtime_max: float = 1.95
    inventory_policy: InventoryPolicy
    transport_policies: Dict[str, TransportPolicy]

# Default configuration
default_config = SimulationConfig(
    customers={
        "Poznan": CustomerConfig(dc="DC_Berlin"),
        "Hanover": CustomerConfig(dc="DC_Berlin"),
        "Hamburg": CustomerConfig(dc="DC_Berlin"),
        "Vienna": CustomerConfig(dc="DC_Prague"),
        "Nuremberg": CustomerConfig(dc="DC_Prague"),
        "Munich": CustomerConfig(dc="DC_Prague")
    },
    products={
        "PC": ProductCustomer(
            customers={"Poznan": 50, "Vienna": 50},
            selling_price=1150,
            cost_price=350,
            volume=0.1
        ),
        "Monitor": ProductCustomer(
            customers={"Hanover": 50, "Nuremberg": 50},
            selling_price=850,
            cost_price=250,
            volume=0.1
        ),
        "MFP": ProductCustomer(
            customers={"Hamburg": 50, "Munich": 50},
            selling_price=700,
            cost_price=200,
            volume=0.1
        )
    },
    dcs={
        "DC_Berlin": DCConfig(
            fixed_cost_per_day=2500,
            locations_served=["Poznan", "Hanover", "Hamburg"]
        ),
        "DC_Prague": DCConfig(
            fixed_cost_per_day=1500,
            locations_served=["Vienna", "Nuremberg", "Munich"]
        )
    },
    inventory_policy=InventoryPolicy(
        type="s_S",
        s=57,
        S=113
    ),
    transport_policies={
        "supplier_to_dc": TransportPolicy(min_load=60, max_load=60),
        "dc_to_customer": TransportPolicy(min_load=0, max_load=20)
    }
)