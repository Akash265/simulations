from scmsim import api

import pandas as pd

if __name__ == "__main__":
    
    from scmsim import config

    data = api.run(
         mfgqty_mu= config.mfgqty_mu,
         mfgqty_sigma= config.mfgqty_sigma,
         mfg_normal= config.mfg_normal,
         l_mfggroups= config.mfg_groups,
         l_mfgshares= config.mfg_shares,
         lifetime= config.lifetime,
         dmndqty_mu= config.dmndqty_mu,
         dmndqty_sigma= config.dmndqty_sigma,
         dmnd_normal= config.dmnd_normal,
         l_dmndprefs= config.dmnd_prefs,
         l_dmndprefprobs= config.dmnd_probs,
         n_warehouses= config.warehouses,
         supplierqty_mu= config.supqty_mu,
         supplierqty_sigma= config.supqty_sigma,
         supplier_normal= config.sup_normal,
         l_supplyprodgroups= config.sup_groups,
         l_supplyprodshares= config.sup_shares,
         l_deliveryleadtimes= config.leadtimes,
         simlength= config.simlength)

    # test statistics for verification
    print(f"available products purchased at MANUFACTURER 1 throughput simulation {data.loc[(data['entity'] == 'manufacturer 1')]['fulfilled'].sum()}")
    print(f"available products purchased at WAREHOUSE 1 throughput simulation {data.loc[(data['entity'] == 'warehouse 1')]['fulfilled'].sum()}")
    print(f"available products purchased at WAREHOUSE 2 throughput simulation {data.loc[(data['entity'] == 'warehouse 2')]['fulfilled'].sum()}")
    print(f"available products purchased at WAREHOUSE 3 throughput simulation {data.loc[(data['entity'] == 'warehouse 3')]['fulfilled'].sum()}")

def run(
        mfgqty_mu           :float,
        mfgqty_sigma        :float,
        mfg_normal          :bool,
        l_mfggroups         :list,
        l_mfgshares         :list,
        lifetime            :int,
        dmndqty_mu          :float,
        dmndqty_sigma       :float,
        dmnd_normal         :bool,
        l_dmndprefs         :list,
        l_dmndprefprobs     :list,
        n_warehouses        :int,
        supplierqty_mu      :float,
        supplierqty_sigma   :float,
        supplier_normal     :bool,
        l_supplyprodgroups  :list,
        l_supplyprodshares  :list,
        l_deliveryleadtimes :list,
        simlength           :int
        ) -> pd.DataFrame:
    
    return api.run(
        mfgqty_mu,
        mfgqty_sigma,
        mfg_normal,
        l_mfggroups,
        l_mfgshares,
        lifetime,
        dmndqty_mu,
        dmndqty_sigma,
        dmnd_normal,
        l_dmndprefs,
        l_dmndprefprobs,
        n_warehouses,
        supplierqty_mu,
        supplierqty_sigma,
        supplier_normal,
        l_supplyprodgroups,
        l_supplyprodshares,
        l_deliveryleadtimes,
        simlength
        )