# Auto-generated info module voor de 'sustainability_advisor' assistant

def get_sustainability_advisor_info():
    return {
        "title": "Sustainability_advisor",
        "description": "Beschrijvingstekst voor de sustainability_advisor assistant."
    }

"""
Assistant: Sustainability Advisor

Beschrijving:
    Berekent CO₂-voetafdruk en adviseert over duurzaamheidskaders.
    De Sustainability Advisor helpt organisaties bij het analyseren van
    hun milieu-impact, het opstellen van duurzame strategieën en
    het genereren van helder leesbare rapportages.

Tools:
    - CarbonCalculator: meet emissies per activiteit en berekent totale CO₂-uitstoot
    - SustainabilityReportGenerator: genereert volledige duurzaamheidsrapporten
    - EcoScoreAssessor: kent scores toe op milieu-impact en vergelijkt met benchmarks
    - LifecycleAnalyzer: voert levenscyclusanalyses (LCA) uit voor producten of processen
    - RenewableEnergyAdvisor: adviseert over de inzet van hernieuwbare energiebronnen

Voorbeeld gebruik:
    >>> from assistants.sustainability_advisor.assistant import Assistant
    >>> assistant = Assistant()
    >>> emissions = assistant.use_tool('CarbonCalculator', {
    ...     'activities': [
    ...         {'name': 'Zakelijke reis vliegtuig', 'distance_km': 1200, 'mode': 'plane'},
    ...         {'name': 'Kantoor stroomverbruik', 'kwh': 3500}
    ...     ]
    ... })
    >>> print(emissions)  # {'total_co2_kg': 850.4, 'breakdown': {...}}

    >>> report = assistant.use_tool('SustainabilityReportGenerator', {
    ...     'company_name': 'Acme Corp',
    ...     'year': 2025,
    ...     'data': emissions
    ... })
    >>> print(report.summary)

    >>> score = assistant.use_tool('EcoScoreAssessor', {
    ...     'emissions': emissions,
    ...     'industry': 'manufacturing'
    ... })
    >>> print(f"Eco Score: {score['score']}")

"""

def get_sustainability_advisor_info():
    return {
        "title": "Sustainability_advisor",
        "description": (
            "De Sustainability Advisor berekent emissies, voert lifecycle-analyses uit "
            "en genereert duurzaamheidsrapporten om organisaties te helpen bij hun "
            "transitie naar een lagere ecologische voetafdruk."
        ),
        "tools": [
            {"name": "CarbonCalculator", "description": "Meet emissies per activiteit en berekent totale CO₂-uitstoot."},
            {"name": "SustainabilityReportGenerator", "description": "Genereert volledige duurzaamheidsrapporten inclusief grafieken en aanbevelingen."},
            {"name": "EcoScoreAssessor", "description": "Kent scores toe op milieu-impact en vergelijkt deze met branchebenchmarks."},
            {"name": "LifecycleAnalyzer", "description": "Voert levenscyclusanalyses uit voor producten of processen."},
            {"name": "RenewableEnergyAdvisor", "description": "Adviseert over optimale inzet van hernieuwbare energiebronnen."}
        ],
        "examples": [
            {
                "code": "assistant.use_tool('CarbonCalculator', {'activities': [...]})",
                "explanation": "Berekent de CO₂-uitstoot voor een lijst activiteiten."
            },
            {
                "code": "assistant.use_tool('SustainabilityReportGenerator', {'company_name': 'Acme', 'year': 2025, 'data': emissions})",
                "explanation": "Genereert een duurzaamheidsrapport voor 2025 met de berekende emissiedata."
            },
            {
                "code": "assistant.use_tool('EcoScoreAssessor', {'emissions': emissions, 'industry': 'manufacturing'})",
                "explanation": "Kent een Eco Score toe op basis van emissies en branche."
            }
        ],
    }
