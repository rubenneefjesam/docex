# Auto-generated info module voor de 'sustainability_advisor' assistant

def get_sustainability_advisor_info():
    return {
        "title": "Sustainability Advisor",
        "description": (
            "De Sustainability Advisor berekent emissies, voert lifecycle-analyses uit "
            "en genereert duurzaamheidsrapporten om organisaties te helpen bij hun "
            "transitie naar een lagere ecologische voetafdruk."
        ),
        "tools": [
            {"name": "CarbonCalculator",             "description": "Meet emissies per activiteit en berekent totale CO₂-uitstoot."},
            {"name": "SustainabilityReportGenerator","description": "Genereert volledige duurzaamheidsrapporten inclusief grafieken en aanbevelingen."},
            {"name": "EcoScoreAssessor",             "description": "Kent scores toe op milieu-impact en vergelijkt met branchebenchmarks."},
            {"name": "LifecycleAnalyzer",            "description": "Voert levenscyclusanalyses uit voor producten of processen."},
            {"name": "RenewableEnergyAdvisor",       "description": "Adviseert over optimale inzet van hernieuwbare energiebronnen."}
        ],
        "examples": [
            {
                "code": "assistant.use_tool('CarbonCalculator', {'activities':[{'name':'Vliegreis','distance_km':1200}]})",
                "explanation": "Berekent de CO₂-uitstoot voor een lijst activiteiten."
            }
        ],
    }
