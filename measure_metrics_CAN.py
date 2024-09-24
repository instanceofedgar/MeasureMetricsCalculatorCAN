import pandas as pd
import numpy as np
from enum import Enum

class Region(Enum):
    AB = 'AB'
    BC = 'BC'
    MB = 'MB'
    NB = 'NB'
    NL = 'NL'
    NT = 'NT'
    NS = 'NS'
    NU = 'NU'
    ON = 'ON'
    PE = 'PE'
    QC = 'QC'
    SK = 'SK'
    YT = 'YT'

class Fuel(Enum):
    ELECTRICITY = 'electricity'
    NATURAL_GAS = 'natural_gas'

class Units(Enum):
    SQ_M = 'm²'
    SQ_FT = 'ft²'

def load_region_emissions_intensity_data(
        region: Region, 
        fuel: Fuel
    ) -> tuple[pd.DataFrame, int|None]:
    '''
    Loads the region-specific carbon intensity data based on the fuel type.
    Returns a dictionary of year-to-intensity for electricity or a constant intensity for natural gas.
    '''
    # emissions intensity data path
    file_path = (
        'reference_data/elec_grid_kgCO2_per_kWh.csv' 
        if fuel is Fuel.ELECTRICITY 
        else 'reference_data/natural_gas_kgCO2_per_kWh.csv'
    )
    df = pd.read_csv(file_path)
    
    if fuel is Fuel.ELECTRICITY:
        region_data = df[df['region'] == region.value].iloc[0, 1:].to_dict()
        last_year = min(max(int(year) for year in df.columns[1:]), 2050)
        return region_data, last_year
    else:
        region_data = df[df['region'] == region.value]['all_years'].values[0]
        return region_data, None

def calculate_carbon_savings(
        region: Region, 
        kWh_savings: float, 
        measure_life: int, 
        implementation_year: int,
        fuel: Fuel
    ) -> list:
    '''
    Returns a list of carbon savings in tCO₂e for the specified fuel type
    over the measure life starting from the implementation year.
    '''
    # load region-specific carbon intensity data
    region_data, last_year = load_region_emissions_intensity_data(region, fuel)
    
    # get the range of years for the calculation
    years = list(range(implementation_year, implementation_year + measure_life))
    
    if fuel is Fuel.ELECTRICITY:
        # fill in values beyond the last available year (e.g., 2050) with the last year's value
        for year in years:
            if str(year) not in region_data:
                region_data[str(year)] = region_data[str(last_year)]
        
        # calculate carbon savings per year for electricity
        carbon_savings_per_year = [
            (kWh_savings * region_data[str(year)])/1000 
            for year in years
        ]
    else:
        # for natural gas, carbon intensity is constant for all years
        carbon_savings_per_year = [
            (kWh_savings * float(region_data))/1000 
            for _ in years
        ]
    
    return carbon_savings_per_year

def calculate_carbon_tax_savings(
        natural_gas_carbon_savings_per_year: list, 
        measure_life: int, 
        implementation_year: int,
        consumer_price_index: float,
    ) -> list:
    '''
    Returns a list of carbon tax savings based on natural gas carbon savings
    and carbon tax data over the measure life.
    '''
    # load the carbon tax data
    file_path = 'reference_data/canada_carbon_tax.csv'
    carbon_tax_data = pd.read_csv(file_path)
    
    # get the range of years for the calculation
    years = list(range(implementation_year, implementation_year + measure_life))
    last_year = min(max(int(year) for year in carbon_tax_data['year']), 2050)
    last_year_value = carbon_tax_data.loc[carbon_tax_data['year'] == last_year, '$_per_ton'].values[0]

    
    # fill in values beyond the last available year (e.g., 2050) with the last year's value
    for year in years:
        if year not in carbon_tax_data['year'].values:
            inflated_value = last_year_value * ((1 + consumer_price_index) ** (year - last_year))
            carbon_tax_data_beyond_2050 = pd.DataFrame({'year': [year], '$_per_ton': [inflated_value]})
            carbon_tax_data = pd.concat([carbon_tax_data, carbon_tax_data_beyond_2050], ignore_index=True)

    # convert carbon tax df to dict for lookup
    carbon_tax_savings_dict = dict(zip(carbon_tax_data['year'], carbon_tax_data['$_per_ton']))
    
    # calculate the carbon tax savings per year
    carbon_tax_savings_per_year = [
        round(natural_gas_carbon_savings_per_year[i] * carbon_tax_savings_dict[year],2) 
        for i, year in enumerate(years)
    ]
    
    return carbon_tax_savings_per_year

def calculate_natural_gas_base_kWh_rate(
        region: Region,
        natural_gas_kWh_rate: float,
        utility_rate_reference_year: int
    ) -> float:
    '''
    Returns the base value of the natural gas kWh rate without carbon tax, if applicable
    '''
    natural_gas_base_kWh_rate = natural_gas_kWh_rate 
    try:
        # load carbon tax data
        file_path = 'reference_data/canada_carbon_tax.csv'
        carbon_tax_data = pd.read_csv(file_path)

        # 'try' and get carbon tax data for a given utility rate reference year
        year_index = carbon_tax_data[carbon_tax_data['year']==utility_rate_reference_year].index[0].item()
        carbon_tax_value = carbon_tax_data.loc[year_index]['$_per_ton']

        # load natural gas emissions intensity for a give region
        file_path = 'reference_data/natural_gas_kgCO2_per_kWh.csv'
        df = pd.read_csv(file_path)
        natural_gas_emissions_intensity = df[df['region'] == region.value]['all_years'].values[0]

        natural_gas_base_kWh_rate -= (natural_gas_emissions_intensity * carbon_tax_value / 1000)

    except:
        pass
    
    return natural_gas_base_kWh_rate

def calculate_future_rate(
        utility_rate: float, 
        inflation_rate: float, 
        reference_year: int, 
        target_year: int
    ) -> float:
    '''
    Calculates the future value of a given utility rate based on the given inflation rate.
    '''
    years_delta = target_year - reference_year
    future_rate = float(utility_rate * ((1 + inflation_rate) ** (years_delta - 1)))
    
    return future_rate

def calculate_utility_savings(
        utility_kWh_savings: float,
        utility_kWh_rate: float,
        utility_inflation: float,
        utility_rate_reference_year: int,
        measure_life: int,
        implementation_year: int
    ) -> list:
    '''
    Returns a list of utility savings over the measure life.
    '''
    # utility rates escalated by inflation
    years = list(range(implementation_year, implementation_year + measure_life))
    future_rates = [
        calculate_future_rate(utility_kWh_rate, utility_inflation, utility_rate_reference_year, year) 
        for year in years
    ]
    
    # utility savings for each year
    utility_savings_per_year = [
        round(utility_kWh_savings * future_rate, 2) 
        for future_rate in future_rates
    ]
    
    return utility_savings_per_year

def calculate_incremental_npv(
        incremental_cost: float,
        cost_savings_per_year: list,
        discount_rate: float
    ) -> float:
    '''
    Calculates the incremental Net Present Value (NPV) of a measure.
    '''
    cash_flows = [-incremental_cost] + cost_savings_per_year
    cash_flows = np.array(cash_flows)
    periods = np.arange(len(cash_flows))
    npv = np.sum(cash_flows / (1 + discount_rate) ** periods)
   
    return round(npv, 2)

###################
# def calculate_measure_metrics(
#         # general inputs
#         present_year: int,
#         region: Region,
#         gross_floor_area: float,
#         gross_floor_area_unit: Units,
#         electricity_kWh_rate: float,
#         natural_gas_kWh_rate: float,
#         utility_rate_reference_year: int,
        
#         # financial scalars
#         discount_rate: float,
#         consumer_price_index: float,
#         electricity_inflation: float,
#         natural_gas_inflation: float,
        
#         # measure inputs
#         like_for_like_cost: float,
#         measure_cost: float,
#         implementation_year: int,
#         measure_life: int,
#         electricity_kWh_savings: float,
#         natural_gas_kWh_savings: float
#     ):

def calculate_average_carbon_savings(
        region: Region,
        electricity_kWh_savings: float,
        natural_gas_kWh_savings: float,
        implementation_year: int,
        measure_life: int,
    )-> tuple[float, float]:
    '''
    Calculates the average annual carbon savings for a given fuel over the life of a measure.
    '''
    # initialize to 0
    average_electricity_carbon_savings = 0
    average_natural_gas_carbon_savings = 0

    fuels = [Fuel.ELECTRICITY, Fuel.NATURAL_GAS]

    for fuel in fuels:

        # selects fuel-specific kWh savings
        kWh_savings = electricity_kWh_savings if fuel is Fuel.ELECTRICITY else natural_gas_kWh_savings
        
        carbon_savings_per_year = calculate_carbon_savings(
            region, 
            kWh_savings, 
            measure_life, 
            implementation_year, 
            fuel
        )
        annual_average_carbon_savings = sum(carbon_savings_per_year)/len(carbon_savings_per_year) if carbon_savings_per_year else 0
        
        if fuel is Fuel.ELECTRICITY:
            average_electricity_carbon_savings = annual_average_carbon_savings
        else:
            average_natural_gas_carbon_savings = annual_average_carbon_savings
    
    return average_electricity_carbon_savings, average_natural_gas_carbon_savings

## __main__ **
def calculate_measure_metrics(
        # general inputs
        present_year: int,
        gross_floor_area: float,
        gross_floor_area_unit: Units,
        region: Region,
        electricity_kWh_rate: float,
        natural_gas_kWh_rate: float,
        utility_rate_reference_year: int,

        # financial scalars
        discount_rate: float,
        consumer_price_index: float,
        electricity_inflation: float,
        natural_gas_inflation: float,

        # measure inputs
        like_for_like_cost: float,
        measure_cost: float,
        implementation_year: int,
        measure_life: int,
        electricity_kWh_savings: float,
        natural_gas_kWh_savings: float
    ) -> dict:
    '''
    Calculates various metrics for a given measure including:
        - Average Emissions Intensity Reduction (kgCO₂e/ft²)
        - Average Annual Electricity Carbon Savings (tCO₂e)
        - Average Annual Natural Gas Carbon Savings (tCO₂e)
        - Average Annual Carbon Tax Savings
        - Average Annual Electricity Cost Savings
        - Average Annual Natural Gas Cost Savings
        - Incremental NPV
        - Incremental ROI
        - Incremental MAC
    '''

    # average annual carbon savings
    average_electricity_carbon_savings, average_natural_gas_carbon_savings = calculate_average_carbon_savings(
        region,
        electricity_kWh_savings,
        natural_gas_kWh_savings,
        implementation_year,
        measure_life
    )

    # average carbon tax savings
    natural_gas_carbon_savings_per_year = calculate_carbon_savings(
        region, 
        natural_gas_kWh_savings, 
        measure_life, 
        implementation_year, 
        Fuel.NATURAL_GAS
    )
    carbon_tax_savings_per_year = calculate_carbon_tax_savings(
        natural_gas_carbon_savings_per_year, 
        measure_life, 
        implementation_year,
        consumer_price_index
    )
    average_carbon_tax_savings = sum(carbon_tax_savings_per_year) / len(carbon_tax_savings_per_year) if carbon_tax_savings_per_year else 0

    # average utility cost savings: electricity
    electricity_cost_savings_per_year = calculate_utility_savings(
        electricity_kWh_savings, 
        electricity_kWh_rate, 
        electricity_inflation, 
        utility_rate_reference_year, 
        measure_life, 
        implementation_year
    )
    average_electricity_cost_savings = sum(electricity_cost_savings_per_year) / len(electricity_cost_savings_per_year) if electricity_cost_savings_per_year else 0

    # average utility cost savings: natural gas
    natural_gas_base_kWh_rate = calculate_natural_gas_base_kWh_rate(
        region,
        natural_gas_kWh_rate,
        utility_rate_reference_year
    )
    natural_gas_cost_savings_per_year = calculate_utility_savings(
        natural_gas_kWh_savings, 
        natural_gas_base_kWh_rate, 
        natural_gas_inflation, 
        utility_rate_reference_year, 
        measure_life, 
        implementation_year
    )
    average_natural_gas_cost_savings = sum(natural_gas_cost_savings_per_year) / len(natural_gas_cost_savings_per_year) if natural_gas_cost_savings_per_year else 0

    # incremental cost
    incremental_cost = (measure_cost - like_for_like_cost) * (1 + consumer_price_index)**(implementation_year - present_year)

    # total cost savings per year (utilities and carbon tax)
    total_cost_savings_per_year = [
        carbon_tax_cost + electricity_cost + natural_gas_cost
        for carbon_tax_cost, electricity_cost, natural_gas_cost 
        in zip(carbon_tax_savings_per_year, electricity_cost_savings_per_year, natural_gas_cost_savings_per_year)
    ]

    # incremental NPV
    incremental_npv = calculate_incremental_npv(
        incremental_cost,
        total_cost_savings_per_year,
        discount_rate
    )

    # total carbon savings (electricity and natural gas)
    total_carbon_savings = measure_life * (average_electricity_carbon_savings + average_natural_gas_carbon_savings)
    
    # incrmental ROI
    incremental_roi = incremental_npv / (incremental_cost * (1 + consumer_price_index)**(implementation_year - present_year))

    # incremetal Marginal Abatement Cost (MAC)
    incremental_mac = - incremental_npv / total_carbon_savings

    # emissions intensity reduction
    avg_kgCO2_intensity_reduction = 1000 * total_carbon_savings / measure_life / gross_floor_area
    avg_kgCO2_intensity_reduction *= 1 if gross_floor_area_unit is Units.SQ_FT else 10.7639

    return {
        'avg_emissions_intensity_reduction': avg_kgCO2_intensity_reduction,
        'avg_electricity_carbon_savings': average_electricity_carbon_savings,
        'avg_natural_gas_carbon_savings': average_natural_gas_carbon_savings,
        'avg_carbon_tax_savings': average_carbon_tax_savings,
        'avg_electricity_cost_savings': average_electricity_cost_savings,
        'avg_natural_gas_cost_savings': average_natural_gas_cost_savings,
        'incremental_npv': incremental_npv,
        'incremental_roi': incremental_roi,
        'incremental_mac': incremental_mac
    }

def print_measure_metrics(measure_metrics: dict):
    '''
    Prints the calculated measure metrics.
    '''
    print(f"Average Emissions Intensity Reduction (kgCO₂e/ft²): {measure_metrics['avg_emissions_intensity_reduction']:,.3f}")
    print(f"Average Annual Electricity Carbon Savings (tCO₂e): {measure_metrics['avg_electricity_carbon_savings']:,.2f}")
    print(f"Average Annual Natural Gas Carbon Savings (tCO₂e): {measure_metrics['avg_natural_gas_carbon_savings']:,.2f}")
    print(f"Average Annual Carbon Tax Savings: ${round(measure_metrics['avg_carbon_tax_savings'],-1):,.0f}")
    print(f"Average Annual Electricity Cost Savings: ${round(measure_metrics['avg_electricity_cost_savings'],-1):,.0f}")
    print(f"Average Annual Natural Gas Cost Savings: ${round(measure_metrics['avg_natural_gas_cost_savings'],-1):,.0f}")
    print(f"Incremental NPV: ${measure_metrics['incremental_npv']:,.0f}")
    print(f"Incremental ROI: {measure_metrics['incremental_roi']*100:,.1f}%")
    print(f"Incremental MAC: ${measure_metrics['incremental_mac']:,.0f}/tCO₂e")