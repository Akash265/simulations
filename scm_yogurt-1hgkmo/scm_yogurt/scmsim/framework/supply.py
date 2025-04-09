import simpy
import random
import numpy as np

import scmsim.framework.inventory      as inventory
import scmsim.framework.manufacturing  as manufacturing

class SupplyPattern:

    """
    
    class is used to model purchase order planning / generation;
    instances or this class are used by warehouses to pull their daily purchasing plan

    """

    supplier            :manufacturing.Manufacturer
    qty_mu              :float  # daily production 
    qty_sigma           :float  # standard deviation from mean daily production output
    gaussian            :bool
    d_productprogram    :dict   # key: groupstr, value (probability)

    def __init__(self, 
                 supplier       :manufacturing.Manufacturer,
                 qty_mu         :float,
                 qty_sigma      :float,
                 gaussian       :bool,
                 l_groups       :list, # list of str
                 l_probs        :list  # list of float
                 ):
        
        self.supplier   = supplier
        self.qty_mu     = qty_mu
        self.qty_sigma  = qty_sigma
        self.gaussian   = gaussian
        self.d_productprogram = {l_groups[i]: l_probs[i] for i in range(len(l_groups))}
    
    def get_purchases(self, 
                       date_today :int
                       ) -> list:

        """ 

        creates daily instance of purchasing plan, and places these purchase orders at manufacutrer
        by taking them from manufacturers stock (calling respective manufacturer method, removal by FIFO)
        
        """

        qty_total = 0
        if self.gaussian:
            qty_total = random.gauss(mu = self.qty_mu, sigma= self.qty_sigma)
        else:
            qty_total = np.random.lognormal(self.qty_mu, self.qty_sigma, 1)[0]
    
        l_return = []

        for groupstr in self.d_productprogram.keys():

            qty = round(self.d_productprogram[groupstr]*qty_total)

            for _ in range(qty):

                p = self.supplier.distribution(t_pref= (groupstr, ))

                if p: l_return.append(p)

        return l_return        

class Delivery:
    
    date_arrival :int
    product      :inventory.Product

    def __init__(self,
                date_arrival :int,
                product      :inventory.Product
                ): 
        
        self.date_arrival = date_arrival
        self.product      = product