library(tidyverse)
library(reticulate)
library(shiny)
library(ggplot2)
rm(list=ls())
gc(T,T,T) # activates garbage collection

reticulate::virtualenv_create()
scmsim <- reticulate::import("scmsim_r")
virtualenv_install(requirements = "C:\\Users\\FELI03\\Desktop\\localdir\\github\\repos_linnart\\simpyprojects\\scm_yogurt\\requirements.txt")
# FRAMEWORK USED BY SERVER ----------------------------------------------------

# USER INTERFACE --------------------------------------------------------------
ui <- fluidPage(
  titlePanel("Yogurt supply chain simulator"),
  
  # USER INPUT --------------------------------------------------------------
  sidebarLayout(
    
    sidebarPanel(
      
      # button for starting simulation
      tabsetPanel(
        tabPanel("HOME", 
                 numericInput("simlength",           "Simulation runtime [days]: ",         value = 50,      step = 1),
                 actionButton("plotButton",          "Simulate!")
        ),
        tabPanel("PRODUCT DATA",
                 numericInput("lifetime",            "Validity duration [days]:",           value = 11,       step = 1)
        ),
        tabPanel("MANUFACTURING DATA",
                 numericInput("mfgqty_mu",           "Manufacturing output [un] (mean):",   value = 1950,    step = 1),
                 numericInput("mfgqty_sigma",        "Manufacturing output [un] (stddev):", value = 200,     step = 1),
                 checkboxInput("mfg_normal",         "Normal distribution model: ",         value = TRUE),
                 numericInput("mfgshare_strawberry", "Strawberry share:",                   value = 0.33,     step = 0.01),
                 numericInput("mfgshare_blueberry",  "Blueberry share:",                    value = 0.33,     step = 0.01),
                 numericInput("mfgshare_apple",      "Apple share:",                        value = 0.33,     step = 0.01)
        ),
        tabPanel("CONSUMER DEMAND DATA",
                 numericInput("dmndqty_mu",      "Daily total demand per store [un] (mean):",   value = 630, step = 1),
                 numericInput("dmndqty_sigma",   "Daily total demand per store [un] (stddev):", value = 80,  step = 1),
                 checkboxInput("dmnd_normal",    "Normal distribution model: ",             value = TRUE),
                 numericInput("dmndprefproc_s",  "Strawberry only:",                        value = 0.10,     step = 0.01),
                 numericInput("dmndprefproc_sb", "Strawberry, or Blueberry:",               value = 0.20,     step = 0.01),
                 numericInput("dmndprefproc_b",  "Blueberry only:",                         value = 0.10,     step = 0.01),
                 numericInput("dmndprefproc_bs", "Blueberry, or Strawberry:",               value = 0.20,     step = 0.01),
                 numericInput("dmndprefproc_a",  "Apply only:",                             value = 0.40,     step = 0.01)
        ),
        tabPanel("WAREHOUSE DATA",
                 numericInput("n_warehouses",             "Number of sales warehouses/stores:",                   value = 3,    step = 1),
                 numericInput("purchaseqty_mu",           "Daily repurchasing qty, all warehouses [un] (mean):",  value = 640,  step = 1),
                 numericInput("purchaseqty_sigma",        "Daily repurchasing qty, all warehouses [un] (sigma):", value = 81,   step = 1),
                 numericInput("purchaseshare_strawberry", "Strawberry share:",                                    value = 0.30, step = 0.01),
                 numericInput("purchaseshare_blueberry",  "Blueberry share:",                                     value = 0.30, step = 0.01),
                 numericInput("purchaseshare_apple",      "Apple share:",                                         value = 0.40, step = 0.01),
                 numericInput("deliveryleadtime",         "Delivery lead times [days]: ",                         value = 2,    step = 1)
        )
      )
    ),
    
    # SIMULATION RESULTS ------------------------------------------------------
    mainPanel(
      tabsetPanel(
        tabPanel("Distribution simulation",    
                  plotOutput("distbyentity_plot"),
                  plotOutput("distbyproduct_plot")
                 ),
        tabPanel("Availability: strawberry", 
                  plotOutput("availability_strawberry"),
                  plotOutput("availability_strawberryblueberry")
                 ),
        tabPanel("Availability: blueberry", 
                  plotOutput("availability_blueberry"),
                  plotOutput("availability_blueberrystrawberry")
        ),
        tabPanel("Availability: apple", 
                 plotOutput("availability_apple")
        )
      )
    )
  )
)

# SERVER ----------------------------------------------------------------------
server <- function(input, output) {
  
  # trigger simulation only when button is clicked
  simulationresults <- eventReactive(input$plotButton, {
    
    # get the simulated results as a dataframe
    return(scmsim$run(
        mfgqty_mu     = input$mfgqty_mu, 
        mfgqty_sigma  = input$mfgqty_sigma, 
        mfg_normal    = input$mfg_normal,
        l_mfggroups   = list(
                           "strawberry", 
                           "blueberry", 
                           "apple"), 
        l_mfgshares   = list(input$mfgshare_strawberry, 
                            input$mfgshare_blueberry, 
                            input$mfgshare_apple),
        lifetime      = input$lifetime, 
        dmndqty_mu    = input$dmndqty_mu,
        dmndqty_sigma = input$dmndqty_sigma,
        dmnd_normal   = input$dmnd_normal,
        l_dmndprefs   = list(
                          tuple("strawberry"),
                          tuple("strawberry", "blueberry"),
                          tuple("blueberry"),
                          tuple("blueberry", "strawberry"),
                          tuple("apple")
                        ),
        l_dmndprefprobs = list(
                            input$dmndprefproc_s, 
                            input$dmndprefproc_sb,
                            input$dmndprefproc_b,
                            input$dmndprefproc_bs,
                            input$dmndprefproc_a
                            ),
        n_warehouses        = as.integer(input$n_warehouses),
        supplierqty_mu      = input$purchaseqty_mu,
        supplierqty_sigma   = input$purchaseqty_sigma,
        supplier_normal     = input$mfg_normal,
        l_supplyprodgroups  = list(
                                "strawberry",
                                "blueberry",
                                "apple"
                                ),
        l_supplyprodshares  = list(
                                input$purchaseshare_strawberry,
                                input$purchaseshare_blueberry,
                                input$purchaseshare_apple
                                ),
        l_deliveryleadtimes = list(
                                input$deliveryleadtime,
                                input$deliveryleadtime,
                                input$deliveryleadtime
                                ),
        simlength           = input$simlength
      )
    )

  })
  
  # DISTRIBUTION PLOTS
  # distbyentity_plot ---------------------------------------------
  output$distbyentity_plot <- renderPlot({
      
      df      = simulationresults()
      df$time = as.integer(df$time)
      df      = df %>%
        filter(entity != "manufacturer 1") %>%
        group_by(entity, time, preference) %>%
        summarize(shipped= sum(fulfilled))
      
      ggplot(df) +
        geom_col(mapping= aes(x= time, y= shipped, fill=entity), alpha= 0.2) +
        labs(title = "Daily shipping volumes by final warehouses/stores",
             x = "time",
             y = "shipped [un]"
        )
  })
  
  # distbyproduct_plot ---------------------------------------------
  output$distbyproduct_plot <- renderPlot({
    
    df      = simulationresults()
    df$time = as.integer(df$time)
    df      = df %>%
      filter(entity != "manufacturer 1") %>%
      group_by(entity, time, product) %>%
      summarize(shipped= sum(fulfilled))
    
    ggplot(df) +
      geom_col(mapping= aes(x= time, y= shipped, fill= product), alpha=0.2) +
      labs(title = "Daily shipping volumes by product group, at manufacturer",
           x = "time",
           y = "shipped [un]"
      )
    
  })
  
  # AVAILABILITY PLOTS --------------------------------------------
  output$availability_strawberry <- renderPlot({
    
    df      = simulationresults()
    df$time = as.integer(df$time)
    df      = df %>%
      filter(
              entity != "manufacturer 1",
              as.character(preference) == as.character(tuple("strawberry"))
             ) %>%
      group_by(time) %>%
      summarize(shipped=     sum(fulfilled),
                unfulfilled= sum(!fulfilled))
    
    ggplot(df) +
      geom_col(mapping= aes(x= time, y= shipped), fill="green", alpha= 0.2) +
      geom_col(mapping= aes(x= time, y= unfulfilled), fill="red", alpha= 0.2) +
      labs(title = "Daily sales and unavailable orders for (strawberry) preference",
           x = "time",
           y = "sales (green) and unavailable orders (red) [un]"
      )
    
  })

  output$availability_strawberryblueberry <- renderPlot({
    
    df      = simulationresults()
    df$time = as.integer(df$time)
    df      = df %>%
      filter(
        entity != "manufacturer 1",
        as.character(preference) == as.character(tuple("strawberry", "blueberry"))
      ) %>%
      group_by(time) %>%
      summarize(shipped=     sum(fulfilled),
                unfulfilled= sum(!fulfilled))
    
    ggplot(df) +
      geom_col(mapping= aes(x= time, y= shipped), fill="green", alpha= 0.2) +
      geom_col(mapping= aes(x= time, y= unfulfilled), fill="red", alpha= 0.2) +
      labs(title = "Daily sales and unavailable orders for (strawberry, blueberry) preference",
           x = "time",
           y = "sales (green) and unavailable orders (red) [un]"
      )
    
  })
  
  output$availability_blueberry <- renderPlot({
    
    df      = simulationresults()
    df$time = as.integer(df$time)
    df      = df %>%
      filter(
        entity != "manufacturer 1",
        as.character(preference) == as.character(tuple("blueberry"))
      ) %>%
      group_by(time) %>%
      summarize(shipped=     sum(fulfilled),
                unfulfilled= sum(!fulfilled))
    
    ggplot(df) +
      geom_col(mapping= aes(x= time, y= shipped), fill="green", alpha= 0.2) +
      geom_col(mapping= aes(x= time, y= unfulfilled), fill="red", alpha= 0.2) +
      labs(title = "Daily sales and unavailable orders for (blueberry) preference",
           x = "time",
           y = "sales (green) and unavailable orders (red) [un]"
      )
    
  })
  
  output$availability_blueberrystrawberry <- renderPlot({
    
    df      = simulationresults()
    df$time = as.integer(df$time)
    df      = df %>%
      filter(
        entity != "manufacturer 1",
        as.character(preference) == as.character(tuple("blueberry", "strawberry"))
      ) %>%
      group_by(time) %>%
      summarize(shipped=     sum(fulfilled),
                unfulfilled= sum(!fulfilled))
    
    ggplot(df) +
      geom_col(mapping= aes(x= time, y= shipped), fill="green", alpha= 0.2) +
      geom_col(mapping= aes(x= time, y= unfulfilled), fill="red", alpha= 0.2) +
      labs(title = "Daily sales and unavailable orders for (blueberry, strawberry) preference",
           x = "time",
           y = "sales (green) and unavailable orders (red) [un]"
      )
    
  })
  
  output$availability_apple <- renderPlot({
    
    df      = simulationresults()
    df$time = as.integer(df$time)
    df      = df %>%
      filter(
        entity != "manufacturer 1",
        as.character(preference) == as.character(tuple("apple"))
      ) %>%
      group_by(time) %>%
      summarize(shipped=     sum(fulfilled),
                unfulfilled= sum(!fulfilled))
    
    ggplot(df) +
      geom_col(mapping= aes(x= time, y= shipped), fill="green", alpha= 0.2) +
      geom_col(mapping= aes(x= time, y= unfulfilled), fill="red", alpha= 0.2) +
      labs(title = "Daily sales and unavailable orders for (apple) preference",
           x = "time",
           y = "sales (green) and unavailable orders (red) [un]"
      )
    
  })
  
}

# APPLICATION -----------------------------------------------------------------
shinyApp(ui = ui, server = server)