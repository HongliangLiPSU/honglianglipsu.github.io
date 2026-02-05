---
layout: archive
title: "Project"
permalink: /project/
author_profile: true
---

## Gird-interactive System Level Energy Efficient Digital Twin Dashboard
<iframe 
  src="https://mpc-dashboard-snowy.vercel.app/" 
  width="80%" 
  height="800px"
  frameborder="0"
  style="border: 1px solid #ddd; border-radius: 8px;"
></iframe>

## Diffusion-Based Real-Time Electricity Price Distribution Learning
This project uses a diffusion model to learn the probability distribution of PJM real-time electricity prices and generate realistic multi-hour price scenarios. Instead of predicting only one point forecast, it produces full distributions and tail behavior, which are directly useful for stochastic and chance-constrained optimization. The workflow includes model training, scenario generation, and diagnostic visualization to check how well generated prices match historical PJM patterns.
![My figure](/images/diffusion_qq.png)
![My figure](/images/diffusion_process.png)
![My figure](/images/diffusion_ecdf.png)
![My figure](/images/diffusion_hist.png)