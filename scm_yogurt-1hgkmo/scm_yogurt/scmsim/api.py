import simpy
import pandas as pd
from collections import deque

#import framework.demand as demand
import scmsim.framework.demand         as demand
import scmsim.framework.supply         as supply
import scmsim.framework.warehousing    as warehousing
import scmsim.framework.inventory      as inventory
import scmsim.framework.manufacturing  as manufacturing

def run(
         mfgqty_mu            :float,
         mfgqty_sigma        :float,
         mfg_normal          :bool, # if false, then log normal
         l_mfggroups         :list,
         l_mfgshares         :list,
         lifetime            :int,
         dmndqty_mu          :float,
         dmndqty_sigma       :float,
         dmnd_normal         :bool, # if false, then log normal
         l_dmndprefs         :list,
         l_dmndprefprobs     :list,
         n_warehouses        :int,
         supplierqty_mu      :float,
         supplierqty_sigma   :float,
         supplier_normal     :bool, # if false, then log normal
         l_supplyprodgroups  :list,
         l_supplyprodshares  :list,
         l_deliveryleadtimes :list,
         simlength           :int
         ): # -> pandas.DataFrame
    """
    
    API encapsulating simulation applicaiton, returning results

    returns:
    - pandas.DataFrame with simulation results

    """

    env = simpy.Environment()

    # setup supplying manufacturers
    s = manufacturing.Manufacturer(
                                id = 1,
                                env = env, 
                                qty_mu= mfgqty_mu, 
                                qty_sigma= mfgqty_sigma,
                                gaussian =  mfg_normal,
                                l_groups= l_mfggroups, 
                                l_probs= l_mfgshares, 
                                shelflife= inventory.ShelfLife(lifetime= lifetime)
                                )
    env.process(s.production())

    # setup end-warehouses
    whs = []
    for i_wh in range(n_warehouses):

        dm = demand.DemandPattern(
                                qty_mu= dmndqty_mu, 
                                qty_sigma= dmndqty_sigma,
                                gaussian = dmnd_normal, 
                                l_preferences= l_dmndprefs, 
                                l_probs= l_dmndprefprobs
                                )
        
        sm = supply.SupplyPattern(
                                supplier= s, 
                                qty_mu= supplierqty_mu,
                                qty_sigma= supplierqty_sigma,
                                gaussian = supplier_normal,  
                                l_groups= l_supplyprodgroups, 
                                l_probs= l_supplyprodshares
                                )

        wh = warehousing.Warehouse(
                                id = i_wh+1,
                                env= env, 
                                demandmodel= dm, 
                                supplymodel= sm, 
                                leadtime= l_deliveryleadtimes[i_wh]
                                )

        env.process(wh.warehousing())

        whs.append(wh)

    # run simulation
    env.run(until= simlength)

    # write simulation results and return as pandas dataframe
    
    data = []
    
    for so in s.l_processedorders:

        data.append([str(s), so.date, str(so.t_pref), str(so.product), so.fulfilled])

    for wh in whs:

        for so in wh.l_processedorders:

            data.append([str(wh), so.date, str(so.t_pref), str(so.product), so.fulfilled])

    return pd.DataFrame(data, columns= ["entity", "time", "preference", "product", "fulfilled"])