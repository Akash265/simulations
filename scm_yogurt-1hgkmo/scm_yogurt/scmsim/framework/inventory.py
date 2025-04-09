import simpy
from collections import deque

class Product:

    groupstr :str
    date_mfg :int
    date_val :int

    def __init__(self,
                 groupstr :str,
                 date_mfg :int,
                 date_val :int
                ):
        
        self.groupstr = groupstr
        self.date_mfg = date_mfg
        self.date_val = date_val
    
    def __repr__(self):

        return self.groupstr

class ShelfLife:

    lifetime :int

    def __init__(self, 
                 lifetime :int
                ):
        
        self.lifetime = lifetime
    
    def get_lifetime(self) -> int:

        return self.lifetime

class InventoryGroup:

    env      :simpy.Environment
    groupstr :str
    l_stock  :deque
    qty      :int

    def __init__(self,
                 env :simpy.Environment,
                 groupstr :str
                 ) -> None:
        
        self.env = env
        self.groupstr = groupstr
        self.l_stock = deque([])
        self.qty     = 0
    
    def putaway(self,
                product :Product
                ) -> None:
        
        self.l_stock.append(product)
        self.qty += 1
    
    def retrieve(self) -> Product:
        
        if self.qty > 0:

            self.qty -= 1
            return self.l_stock.popleft() # removes product from the inventory
        
        return None

    def checkvalidity(self) -> int:

        diff = 0

        for p in list(self.l_stock):

            if self.env.now > p.date_val:

                self.l_stock.remove(p)
                self.qty -= 1
                diff += 1
        
        return diff

class Inventory:

    env           :simpy.Environment
    d_invgroups   :dict  # key groupstr, value InventoryGroup instance
    qty           :int
    
    def __init__(self, 
                 env: simpy.Environment
                ):
        
        self.env = env
        self.d_invgroups = {} # key: groupstr, val: InventoryGroup
        self.qty = 0
    
    def putaway(self, 
                p: Product
                ) -> None:

        if p.groupstr not in self.d_invgroups.keys():

            self.d_invgroups[p.groupstr] = InventoryGroup(env= self.env, groupstr= p.groupstr)
        
        self.d_invgroups[p.groupstr].putaway(product= p)
        
        self.qty += 1
    
    def retrieve(self, 
                 t_pref   :tuple
                )        -> Product:

        for groupstr in t_pref:

            if groupstr in self.d_invgroups.keys():
                
                if self.d_invgroups[groupstr].qty > 0:

                    self.qty -= 1
                    return self.d_invgroups[groupstr].retrieve()
        
        return None

    def checkvalidity(self) -> None:

        for invgroup in self.d_invgroups.values():

            self.qty -= invgroup.checkvalidity()