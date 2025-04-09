import simpy
import random
import numpy as np

import scmsim.framework.inventory as inventory

class DemandPattern:

    d_productprogram :dict # key preference tuple, value probability
    qty_mu        :float #underlying normal distribution
    qty_sigma     :float #underlying normal distribution
    gaussian      :bool

    def __init__(self,
                 qty_mu :float,
                 qty_sigma :float,
                 gaussian :bool,
                 l_preferences :list, # list of tuples
                 l_probs :list  
                 ):

        self.qty_sigma = qty_sigma 
        self.qty_mu = qty_mu
        self.gaussian= gaussian
        self.d_productprogram = {l_preferences[i]: l_probs[i] for i in range(len(l_preferences))}
    
    def get_salesorders(self) -> list: # list of tuples

        qty_total= 0 
        if self.gaussian:
            qty_total = random.gauss(mu= self.qty_mu, sigma= self.qty_sigma)
        else:
            qty_total = np.random.lognormal(self.qty_mu, self.qty_sigma, 1)[0]

        l_return = []

        for t_pref in self.d_productprogram.keys():

            qty = round(qty_total*self.d_productprogram[t_pref])

            for _ in range(qty):
                
                l_return.append(t_pref)
        
        return l_return

class SalesOrder:

    t_pref         :tuple # tuple of str
    date           :int   # iteration of purchase
    product        :inventory.Product 
    fulfilled      :bool

    def __init__(self,
                t_pref  :tuple,  # tuple of strs,
                date    :int = None,
                product :inventory.Product = None
                ):
        
        self.t_pref      = t_pref
        self.date        = date
        self.product     = product
        
        if self.product:
            
            self.fulfilled  = True
        
        else:

            self.fulfilled = False
    
    def __repr__(self):

        if self.product:
                
            return f"preference: {self.t_pref} on date: {self.date} received product: {self.product.groupstr}, fulfilled: {self.fulfilled}"

        else:

            return f"preference: {self.t_pref} on date: {self.date} received product: {self.product}, fulfilled: {self.fulfilled}"