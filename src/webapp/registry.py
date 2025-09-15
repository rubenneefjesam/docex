# src/webapp/registry.py

ASSISTANTS = {
    "general_support": {
        "label": "General support",
        "tools": {
            "document_generator": {
                "label": "Document generator",
                "page_module_candidates": [
                    "webapp.assistants.general_support.tools.doc_generator.doc_generator",
                    "webapp.assistants.general_support.tools.doc_generator",
                ],
            },
            "document_comparison": {
                "label": "Document comparison",
                "page_module_candidates": [
                    "webapp.assistants.general_support.tools.doc_comparison.doc_comparison",
                    "webapp.assistants.general_support.tools.doc_comparison",
                ],
            },
        },
    },

    "tender_manager_assistant": {
        "label": "Tender Manager",
        "tools": {
            "TenderDocumentCreator": {
                "label": "Document Creator",
                "page_module": "tools.document_creator",
            },
            "DeadlineTracker": {
                "label": "Deadline Tracker",
                "page_module": "tools.deadline_tracker",
            },
            "BidScoringModel": {
                "label": "Bid Scoring",
                "page_module": "tools.bid_scoring",
            },
        },
    },

    "legal_assistant": {
        "label": "Legal Assistant",
        "tools": {
            "ContractAnalyzer": {
                "label": "Contract Analyzer",
                "page_module": "tools.contract_analyzer",
            },
            "ComplianceChecker": {
                "label": "Compliance Checker",
                "page_module": "tools.compliance_checker",
            },
            "CaseLawSearch": {
                "label": "Case Law Search",
                "page_module": "tools.case_law_search",
            },
        },
    },

    "project_assistant": {
        "label": "Project Assistant",
        "tools": {
            "TimelinePlanner": {
                "label": "Timeline Planner",
                "page_module": "tools.timeline_planner",
            },
            "StatusReporter": {
                "label": "Status Reporter",
                "page_module": "tools.status_reporter",
            },
            "TaskAllocator": {
                "label": "Task Allocator",
                "page_module": "tools.task_allocator",
            },
        },
    },

    "risk_assistant": {
        "label": "Risk Assistant",
        "tools": {
            "RiskIdentifier": {
                "label": "Risk Identifier",
                "page_module": "tools.risk_identifier",
            },
            "HeatmapGenerator": {
                "label": "Heatmap Generator",
                "page_module": "tools.heatmap_generator",
            },
            "MitigationAdvisor": {
                "label": "Mitigation Advisor",
                "page_module": "tools.mitigation_advisor",
            },
        },
    },

    "sustainability_advisor": {
        "label": "Sustainability Advisor",
        "tools": {
            "CarbonCalculator": {
                "label": "Carbon Calculator",
                "page_module": "tools.carbon_calculator",
            },
            "SustainabilityReportGenerator": {
                "label": "Report Generator",
                "page_module": "tools.sustainability_report_generator",
            },
            "EcoScoreAssessor": {
                "label": "Eco Score Assessor",
                "page_module": "tools.eco_score_assessor",
            },
            "LifecycleAnalyzer": {
                "label": "Lifecycle Analyzer",
                "page_module": "tools.lifecycle_analyzer",
            },
            "RenewableEnergyAdvisor": {
                "label": "Renewable Energy Advisor",
                "page_module": "tools.renewable_energy_advisor",
            },
        },
    },
}
