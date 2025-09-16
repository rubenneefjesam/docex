# pages/home.py
import streamlit as st

def render():
    """
    Home-pagina voor DocGen Suite.
    """
    st.header("Home")
    st.write("""
**DocGen Suite** is een krachtige tool die je ondersteunt bij administratieve zaken zoals rapportage, offertebeheer, planning en documentatie.  

- **Efficiëntie**: automatiseer routinetaken en houd meer tijd over voor strategisch werk.  
- **Flexibiliteit**: genereer moeiteloos offertes, rapporten, samenvattingen en actieplannen.  
- **Betrouwbaarheid**: AI-gestuurde assistents leveren consistente en foutloze output.  

**Waarom beter dan Copilot?**  
Copilot is een algemene AI-assistent gericht op code, terwijl DocGen Suite specifiek is ontworpen voor document- en planningswerk met gespecialiseerde "assistents" en tools, waardoor je direct bruikbare, professioneel geformatteerde documenten krijgt zonder extra sjablonen of handmatige aanpassingen.
""")