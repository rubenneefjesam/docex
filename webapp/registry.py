# webapp/registry.py

ASSISTANTS = {
    "general_support": {
        "label": "General support",
        "tools": {
            "document_generator": {
                "label": "Document generator",
                "page_module": "webapp.assistants.general_support.document_generator",
            },
            "document_comparison": {
                "label": "Document comparison",
                "page_module": "webapp.assistants.general_support.document_comparison",
            },
        },
    },

    # --- Voeg hier de Tender Manager Assistant toe ---
    "tender_manager_assistant": {
        "label": "Tender Manager",
        "tools": {
            "TenderDocumentCreator": {
                "label": "Document Creator",
                "page_module": "webapp.assistants.tender_manager_assistant.document_creator",
            },
            "DeadlineTracker": {
                "label": "Deadline Tracker",
                "page_module": "webapp.assistants.tender_manager_assistant.deadline_tracker",
            },
            "BidScoringModel": {
                "label": "Bid Scoring",
                "page_module": "webapp.assistants.tender_manager_assistant.bid_scoring",
            },
        },
    },

    # --- Vul op dezelfde manier de andere modules in ---
    "legal_assistant": {
        "label": "Legal Assistant",
        "tools": {
            "ContractAnalyzer": {
                "label": "Contract Analyzer",
                "page_module": "webapp.assistants.legal_assistant.contract_analyzer",
            },
            "ComplianceChecker": {
                "label": "Compliance Checker",
                "page_module": "webapp.assistants.legal_assistant.compliance_checker",
            },
            "CaseLawSearch": {
                "label": "Case Law Search",
                "page_module": "webapp.assistants.legal_assistant.case_law_search",
            },
        },
    },

    "project_assistant": {
        "label": "Project Assistant",
        "tools": {
            "TimelinePlanner": {
                "label": "Timeline Planner",
                "page_module": "webapp.assistants.project_assistant.timeline_planner",
            },
            "StatusReporter": {
                "label": "Status Reporter",
                "page_module": "webapp.assistants.project_assistant.status_reporter",
            },
            "TaskAllocator": {
                "label": "Task Allocator",
                "page_module": "webapp.assistants.project_assistant.task_allocator",
            },
        },
    },

    "risk_assistant": {
        "label": "Risk Assistant",
        "tools": {
            "RiskIdentifier": {
                "label": "Risk Identifier",
                "page_module": "webapp.assistants.risk_assistant.risk_identifier",
            },
            "HeatmapGenerator": {
                "label": "Heatmap Generator",
                "page_module": "webapp.assistants.risk_assistant.heatmap_generator",
            },
            "MitigationAdvisor": {
                "label": "Mitigation Advisor",
                "page_module": "webapp.assistants.risk_assistant.mitigation_advisor",
            },
        },
    },

    "sustainability_advisor": {
        "label": "Sustainability Advisor",
        "tools": {
            "CarbonCalculator": {
                "label": "Carbon Calculator",
                "page_module": "webapp.assistants.sustainability_advisor.carbon_calculator",
            },
            "SustainabilityReportGenerator": {
                "label": "Report Generator",
                "page_module": "webapp.assistants.sustainability_advisor.sustainability_report_generator",
            },
            "EcoScoreAssessor": {
                "label": "Eco Score Assessor",
                "page_module": "webapp.assistants.sustainability_advisor.eco_score_assessor",
            },
            "LifecycleAnalyzer": {
                "label": "Lifecycle Analyzer",
                "page_module": "webapp.assistants.sustainability_advisor.lifecycle_analyzer",
            },
            "RenewableEnergyAdvisor": {
                "label": "Renewable Energy Advisor",
                "page_module": "webapp.assistants.sustainability_advisor.renewable_energy_advisor",
            },
        },
    },
}
