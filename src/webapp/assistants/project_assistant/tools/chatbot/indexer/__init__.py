# src/webapp/assistants/project_assistant/tools/chatbot/indexer/__init__.py
from .clients_indexer import index_clients_projects_from_csv
from .projects_indexer import index_projects_from_csv
from .documents_indexer import index_documents

__all__ = [
    "index_clients_projects_from_csv",
    "index_projects_from_csv",
    "index_documents",
]
