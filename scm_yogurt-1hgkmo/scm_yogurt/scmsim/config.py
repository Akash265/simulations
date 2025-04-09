# number of warehouses
warehouses = 3

# inbound delivery lead time per warehouse
leadtimes = [7, 7, 7]

# product lifetime 
lifetime = 42

# manufacturing settings
mfgqty_mu = 6.91 # average output per iteration
mfgqty_sigma = 0.001
mfg_normal = False
mfg_groups = ["OPos", "ONeg", "APos", "ANeg", "BPos", "BNeg", "ABPos", "ABNeg"]
mfg_shares = [0.38, 0.07, 0.34, 0.06, 0.09, 0.02, 0.03, 0.01]

# end warehouse consumer demand settings
dmndqty_mu= 5.8
dmndqty_sigma= 0.0001
dmnd_normal= False
dmnd_prefs = [("OPos","ONeg"),          #OPos receipt possibilities
              ("ONeg",),                #ONeg
              ("APos","OPos","ONeg" ),  #apos
              ("ANeg","ONeg"),          #Aneg
              ("BPos","OPos","ONeg"),   #BPos
              ("BNeg","ONeg"),          #BNeg
              ("ABPos","ABNeg","APos","ANeg","BPos","BNeg","OPos","ONeg"), #ABPos
              ("ABNeg","ANeg","BNeg","ONeg")
              ]
dmnd_probs = [0.38, 0.07, 0.34, 0.06, 0.09, 0.02, 0.03, 0.01]

# end warehouse purchase planning settings
supqty_mu = 5.8 # average output per iteration
supqty_sigma = 0.01
sup_normal = False
sup_groups = ["OPos", "ONeg", "APos", "ANeg", "BPos", "BNeg", "ABPos", "ABNeg"]
sup_shares = [0.38, 0.07, 0.34, 0.06, 0.09, 0.02, 0.03, 0.01]

# length of simulation run
simlength = 300