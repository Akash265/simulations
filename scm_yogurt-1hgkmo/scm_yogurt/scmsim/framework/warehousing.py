import simpy
import random
from collections import deque
import scmsim.framework.inventory as inventory
import scmsim.framework.demand    as demand
import scmsim.framework.supply    as supply
        
class Warehouse:

    id                  :int

    env                 :simpy.Environment
    demandmodel         :demand.DemandPattern
    supplymodel         :supply.SupplyPattern
    leadtime            :int  # supply leadtime to this warehouse

    inventory           :inventory.Inventory
    l_deliveries        :deque # list of supply.Delivery
    l_processedorders   :deque # list of demand.SalesOrder

    def __init__(self,
                 id            :int,
                 env           :simpy.Environment,
                 demandmodel   :demand.DemandPattern, 
                 supplymodel   :supply.SupplyPattern,
                 leadtime      :int
                 ):
        
        self.id                = id

        self.env               = env
        self.demandmodel       = demandmodel
        self.supplymodel       = supplymodel
        self.leadtime          = leadtime
        
        self.inventory         = inventory.Inventory(env= self.env)
        self.l_deliveries      = deque([])
        self.l_processedorders = deque([])

    def __repr__(self):

        return f"warehouse {self.id}"

    def warehousing(self):

        while True: # runs for duration of simulation

            # randomize the order that warehouses order in, so that when several warehouses order at the same supplier the order is random
            t_diff = random.uniform(0.0001, 0.001)
            yield self.env.timeout(t_diff)

            # create one supply sample, update incoming deliveries
            for p in self.supplymodel.get_purchases(date_today= self.env.now):

                self.l_deliveries.append(supply.Delivery(date_arrival= self.env.now + self.leadtime, product= p))

            # check deliveries and update inventory and deliveries
            for d in list(self.l_deliveries):

                if d.date_arrival <= self.env.now:
                    
                    self.inventory.putaway(d.product)
                    self.l_deliveries.remove(d)

            # check validity and update inventory
            self.inventory.checkvalidity()

            # create on demand sample; consume demand, update inventory, update l_processedorders
            for t_pref in self.demandmodel.get_salesorders(): 
                
                self.l_processedorders.append(demand.SalesOrder(t_pref= t_pref, date= self.env.now, product= self.inventory.retrieve(t_pref)))
                
            # yield one step iteration
            yield self.env.timeout(1-t_diff)
