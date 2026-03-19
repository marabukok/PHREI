
PHREIs (PHREEQC-based Reinjection Evaluation of Injectivity and scaling) is an open-source Python tool designed to quantify geochemical clogging and its hydraulic consequences in the near-wellbore zone. PHREIs couples equilibrium geochemical simulations performed with PHREEQC with a porosity–permeability relationship based on the Kozeny–Carman equation, enabling computation of mineral precipitation, porosity loss, and permeability decline within a unified framework.

The Python based simplified Graphical User Interface uses a previously developed and published geochemical model setup [Markó, Á., Brehme, M., Pedretti, D., Zimmermann, G., & Huenges, E. (2024). Controls of low injectivity caused by interaction of reservoir and clogging processes in a sedimentary geothermal aquifer (Mezőberény, Hungary). Geothermal Energy, 12(1), 40.]. The setup aims to reproduce the main geochemical processes of a geothermal loop from production until reinjection into the aquifer. The forming scale cumulated over time is then used to estimate the porosity and permeability degradation in the near-wellbore zone. 

PHREIs supports deterministic and stochastic modeling modes. 

PHREIs is applicable without creating new hydrogeochemical model setups by entering the parameters in pop-up windows: fluid composition of production well and reservoir fluid, mineral composition of the reservoir, flow rate, initial porosity and dimensions of gravel pack or the near well-bore zone, reinjection and reservoir temperature. Outcome of the model provides first estimate of clogging risk in doublet systems, as an example a theoretical period of time in which porosity is decreased by half. 

Pre-publication of the pure deterministic PHREI version in conference abstract: https://doi.org/10.5194/egusphere-egu25-3613  
Upgraded version was uploaded on 19.03.2026




