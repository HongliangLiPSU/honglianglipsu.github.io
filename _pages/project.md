---
layout: archive
title: "Project"
permalink: /project/
author_profile: true
---

## Gird-interactive System Level Energy Efficient Digital Twin Dashboard
We developed a React + Vite based web dashboard that visualizes a grid-interactive manufacturing system using a model predictive control (MPC) simulation. It runs a 3-day (72-hour) synthetic digital-twin scenario and shows buffer levels, process rates, production-vs-target performance, electricity price, power demand, and energy cost through interactive charts. The goal is to give a quick operational view of throughput, energy efficiency, peak demand, and total cost in one interface.
<iframe 
  src="https://mpc-dashboard-snowy.vercel.app/" 
  width="80%" 
  height="800px"
  frameborder="0"
  style="border: 1px solid #ddd; border-radius: 8px;"
></iframe>

## Diffusion-Based Real-Time Electricity Price Distribution Learning
This project uses a diffusion model to learn the probability distribution of PJM real-time electricity prices and generate realistic multi-hour price scenarios. Instead of predicting only one point forecast, it produces full distributions and tail behavior, which are directly useful for stochastic and chance-constrained optimization. The workflow includes model training, scenario generation, and diagnostic visualization to check how well generated prices match historical PJM patterns.
![My figure](/images/website_chance_constraint_tradeoff.png)
![My figure](/images/website_quantile_fan_chart.png)
![My figure](/images/website_scenario_trajectories.png)
![My figure](/images/website_tail_exceedance_validation.png)