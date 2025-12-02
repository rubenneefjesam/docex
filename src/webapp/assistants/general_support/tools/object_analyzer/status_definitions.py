# tools/object_analyzer/status_definitions.py

STATUS_DEFINITIONS = {
    "intact": {
        "label": "Intact",
        "description": "Het object lijkt volledig en zonder zichtbare schade."
    },
    "beschadigd_licht": {
        "label": "Beschadigd licht",
        "description": "Kleine beschadiging zichtbaar, maar waarschijnlijk nog bruikbaar."
    },
    "beschadigd_zwaar": {
        "label": "Beschadigd zwaar",
        "description": "Ernstige schade zichtbaar waardoor het object niet bruikbaar lijkt."
    },
    "vervuild": {
        "label": "Vervuild",
        "description": "Het object is vuil of bedekt met materiaal dat gebruik kan beïnvloeden."
    },
    "onveilig_geplaatst": {
        "label": "Onveilig geplaatst",
        "description": "Het object staat instabiel of risicovol opgesteld."
    },
    "onherkenbaar": {
        "label": "Onherkenbaar",
        "description": "Het object kan niet goed worden geanalyseerd door slechte beeldkwaliteit of perspectief."
    }
}
