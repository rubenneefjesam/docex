import streamlit as st


def render():
    """
    Dit is de eerste pagina, ook wel HOME genoemd.
    """
    st.header("Home")
    st.write("""
**Wat is DocGen Suite?**  
DocGen Suite is een intuïtief webplatform dat wordt aangedreven door AI-gestuurde “assistants” en gespecialiseerde tools, gebouwd met Streamlit. Het stelt je in staat om snel en eenvoudig allerlei soorten documenten te genereren, te analyseren en te beheren, zonder steeds met lege tekstbestanden te starten of ingewikkelde sjablonen op te tuigen.

**Wat kun je ermee?**  
- **Selecteer een assistant**: kies uit rollen zoals Legal Assistant, Project Assistant, General Support, Sustainability Advisor, etc.  
- **Kies een tool**: van Document Generator en Plan Creator tot Speech-to-Document, Doc Comparison en Risk Plan Generator.  
- **Genereer output**: professioneel geformatteerde teksten, gestructureerde plannen, samenvattingen of conversies van audio naar bruikbare documenten.

**Waarom is het waardevol?**  
- **Tijdbesparing**: geen eindeloze uren meer kwijt aan opmaak of literatuuronderzoek.  
- **Consistentie & Kwaliteit**: verminder fouten en zorg voor een uniforme stijl met AI-ondersteuning.  
- **Schaalbaarheid**: of je nu één rapport maakt of honderd offertes verwerkt, je workflow blijft soepel en herhaalbaar.  
- **Toegankelijkheid**: een eenvoudige webinterface betekent dat je team direct aan de slag kan, zonder lokale installatie of complexe configuratie.

**Hoe werkt het?**  
1. **Kies in het zijmenu** de gewenste “assistant” die bij jouw taak past.  
2. **Selecteer de tool** die de beoogde functionaliteit levert.  
3. **Voer je input** in (bijv. kerngegevens, spraakopnames of documenten ter vergelijking).  
4. **Genereer** met één druk op de knop een voltooid document of rapport, dat je daarna direct kunt downloaden of verder kunt bewerken.
""")
