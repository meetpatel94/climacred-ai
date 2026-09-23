"""
Emissions calculation module (re-export for clarity)
Keeps emissions logic centralized
"""
from app.utils.calculations import calculate_emissions_metrics, calculate_energy_metrics

def get_emissions_analysis(assessment: dict):
    return calculate_emissions_metrics(assessment)

def get_energy_analysis(assessment: dict, profile: dict = None):
    return calculate_energy_metrics(assessment, profile)
