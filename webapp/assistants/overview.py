from flask import Blueprint, render_template

assistant_bp = Blueprint('assistants', __name__, url_prefix='/assistants')

# === OPGEBOWDE IMPORTS ===
from webapp.assistants.__pycache__.info import get___pycache___info
from webapp.assistants.calculator_assistant.info import get_calculator_assistant_info
from webapp.assistants.general_support.info import get_general_support_info
from webapp.assistants.legal_assistant.info import get_legal_assistant_info
from webapp.assistants.project_assistant.info import get_project_assistant_info
from webapp.assistants.risk_assistant.info import get_risk_assistant_info
from webapp.assistants.sustainability_advisor.info import get_sustainability_advisor_info
from webapp.assistants.tender_manager_assistant.info import get_tender_manager_assistant_info

# === ROUTES ===
@assistant_bp.route('/')
def list_assistants():
    # Hier kun je een lijst van alle assistants renderen
    return render_template('assistants/list.html')

@assistant_bp.route('/__pycache__/info')
def __pycache___info():
    info = get___pycache___info()
    return render_template('assistants/info.html', info=info)

@assistant_bp.route('/calculator_assistant/info')
def calculator_assistant_info():
    info = get_calculator_assistant_info()
    return render_template('assistants/info.html', info=info)

@assistant_bp.route('/general_support/info')
def general_support_info():
    info = get_general_support_info()
    return render_template('assistants/info.html', info=info)

@assistant_bp.route('/legal_assistant/info')
def legal_assistant_info():
    info = get_legal_assistant_info()
    return render_template('assistants/info.html', info=info)

@assistant_bp.route('/project_assistant/info')
def project_assistant_info():
    info = get_project_assistant_info()
    return render_template('assistants/info.html', info=info)

@assistant_bp.route('/risk_assistant/info')
def risk_assistant_info():
    info = get_risk_assistant_info()
    return render_template('assistants/info.html', info=info)

@assistant_bp.route('/sustainability_advisor/info')
def sustainability_advisor_info():
    info = get_sustainability_advisor_info()
    return render_template('assistants/info.html', info=info)

@assistant_bp.route('/tender_manager_assistant/info')
def tender_manager_assistant_info():
    info = get_tender_manager_assistant_info()
    return render_template('assistants/info.html', info=info)

