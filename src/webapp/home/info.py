# pages/info.py
import streamlit as st


def render():
"""
Info-pagina voor DocGen Suite.
Hier vind je achtergrondinformatie over werking, architectuur en technologie.
"""
st.header("Info")
st.write("""
**Wat is DocGen Suite?**
DocGen Suite is een intuïtief webplatform dat wordt aangedreven door AI-gestuurde “assistants” en gespecialiseerde tools, ontwikkeld door Vibecoding met Streamlit. Het stelt je in staat om snel en eenvoudig documenten te genereren, analyseren en beheren.


**Wat kun je ermee?**
- **Selecteer een assistent**: kies uit rollen zoals Legal Assistant, Project Assistant, General Support, Sustainability Advisor, etc.
- **Kies een tool**: van Document Generator en Plan Creator tot Speech-to-Document, Doc Comparison en Risk Plan Generator.
- **Genereer output**: professioneel geformatteerde teksten, gestructureerde plannen, samenvattingen of conversies van audio naar bruikbare documenten.


**Hoe werkt het?**
1. **Framework**: gebouwd met Streamlit voor snelle UI-ontwikkeling.
2. **AI-integratie**: gebruik van OpenAI API’s voor geavanceerde taalverwerking.
3. **Architectuur**: modulair design door Vibecoding met schaalbare backend-services en componentgebaseerde frontend.
4. **Deployment**: gehost in de cloud voor maximale beschikbaarheid en performance.


**Bronnen & documentatie**:
- Handleiding gebruikersinterface: zie /docs/ui
- API-referentie: zie /docs/api
- GitHub-repository: https://github.com/vibecoding/docgensuite
""")