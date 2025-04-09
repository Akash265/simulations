import simpy
import random
import numpy as np
from collections import deque
import scmsim.framework.inventory as inventory
import scmsim.framework.demand    as demand

class Manufacturer:

    """
    
    used for modelling upstream manufacturing plant supplying warehouses

    """

    id                      :int
    env                     :simpy.Environment
    qty_mu                  :float
    qty_sigma               :float
    gaussian                :bool
    d_productionprogram     :dict      # key: groupstr, value (probability)
    inventory               :inventory.Inventory
    shelflife               :inventory.ShelfLife
    l_processedorders       :deque # list of demand.SalesOrder

    def __init__(self,
                 id         :int,
                 env        :simpy.Environment,
                 qty_mu     :float,
                 qty_sigma  :float,
                 gaussian   :bool,
                 l_groups   :list,  # list of str
                 l_probs    :list,  # list of float
                 shelflife  :inventory.ShelfLife
                 ):

        self.id                  = id
        self.env                 = env
        self.qty_mu              = qty_mu
        self.qty_sigma           = qty_sigma
        self.gaussian            = gaussian
        self.d_productionprogram = {l_groups[i]: l_probs[i] for i in range(len(l_groups))}
        self.inventory           = inventory.Inventory(env= self.env)
        self.shelflife           = shelflife
        self.l_processedorders   = deque([])

    def __repr__(self):

        return f"manufacturer {self.id}"
    
    def production(self) -> None:
        """
        
        implement simpy process for producing according to production program, on stock (if warehousing capacity available);
        before production, expired stock in stock is deleted

        """

        while True:
            
            # daily housekeeping
            self.inventory.checkvalidity()

            # daily production on stock
            qty_total= 0
            if self.gaussian:

                qty_total = random.gauss(self.qty_mu, self.qty_sigma)
            
            else:
                
                qty_total = np.random.lognormal(self.qty_mu, self.qty_sigma, 1)[0]

            for groupstr in self.d_productionprogram.keys():

                qty = round(self.d_productionprogram[groupstr]*qty_total)
                
                for _ in range(qty):

                    self.inventory.putaway(inventory.Product(groupstr= groupstr, date_mfg= self.env.now, date_val= self.env.now+self.shelflife.get_lifetime()))  
            
            yield self.env.timeout(1)
    
    def distribution(self,
                    t_pref :tuple
                    ) -> inventory.Product:
        
        p = self.inventory.retrieve(t_pref= t_pref)
                                       
        self.l_processedorders.append(demand.SalesOrder(t_pref= t_pref, date= self.env.now, product= p))

        return p