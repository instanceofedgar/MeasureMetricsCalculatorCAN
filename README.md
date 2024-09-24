# Measure Metrics Calculation for Canada

## Overview

This repository contains code for calculating financial and other metrics for decarbonization measures in Canadian buildings.

Th calculation take into account:

- **time value of money**: future savings are discounted to present value for a given discount rate
- **measure life**: the projected savings and costs are spread over the expected life of the measure
- **carbon tax**: Canada's escalating carbon tax is included in the financial savings with 2050 value of $300
- **utility cost escalation**: utility rates for electricity and natural gas are adjusted for given inflation rates
- **electricity grid decarbonization**: electricity carbon savings are calculated based on projections from ECCC data directory

### Project Structure

The repository consists of two primary files:

**measure_metrics_CAN.ipynb**: this Jupyter Notebook is used to define inputs and call the methods to calculate the metrics
**measure_metrics_CAN.py**: this Python script contains all the methods necessary for performing the calculations

### Reference Data

The project uses three CSV files located in the `reference_data` folder to provide region-specific data:
**canada_carbon_tax.csv**: contains the projected carbon tax rates in Canada.
**elec_grid_kgCO2_per_kWh.csv**: contains electricity grid decarbonization projections by province and year (kg CO₂/kWh)
**natural_gas_kgCO2_per_kWh.csv**: contains carbon intensity values for natural gas consumption by province (kg CO₂/kWh) 

### INPUTS

1. **General Inputs**: These include the present year, gross floor area, region, and current utility rates. These inputs define the baseline for the measure calculations.
   
2. **Financial Scalars**: These inputs define key financial parameters such as the discount rate (for time value of money), consumer price inflation, and utility inflation rates (for electricity and natural gas).

3. **Measure Inputs**: These inputs define the specifics of the energy efficiency measure, including costs, expected savings in energy (electricity and natural gas), the implementation year, and the measure life (in years).

4. **Calculations**: The `calculate_measure_metrics` function performs the following:
   - Computes average annual carbon savings based on energy savings and decarbonization projections.
   - Estimates annual cost savings, including the impact of an escalating carbon tax.
   - Calculates the Net Present Value (NPV) and Return on Investment (ROI) based on cost and savings projections.
   - Determines the Marginal Abatement Cost (MAC), representing the cost per ton of CO₂ saved.
   - Evaluates the emissions intensity reduction over the life of the measure.

### How to Use

- open **measure_metrics_CAN.ipynb**
- define all the inputs and run the cell 