# README — Tests (Docgen Suite)

Dit bestand beschrijft de tests in deze repository: wat ze controleren, hoe je ze lokaal draait en wat te doen bij falende tests.

## Doel

De tests zijn **smoke & basic unit tests** die snel controleren of:

* het `webapp`-package importeerbaar is;
* de registry (`webapp.registry.ASSISTANTS`) de verwachte assistenten en tools bevat;
* alle geregistreerde pagina-modules importeerbaar zijn en een callable `render()` exporteren;
* de helper-functies in `webapp.core.tool_loader` op basisniveau werken.

Deze tests zijn niet bedoeld om Streamlit UI-interacties of end-to-end flows te valideren.

## Bestanden

* `tests/test_imports.py` – importability/smoke test (core).
* `tests/test_registry_content.py` – controleert dat verwachte assistenten in de registry staan.
* `tests/test_core_tool_loader.py` – unit-tests voor `tool_loader` helperfuncties.
* `tests/test_pages_modules.py` – controle op aanwezigheid van `render()` in hoofd-pagina's.

## Lokaal draaien

1. Zorg dat je in de projectroot staat (map met `webapp/`):

   ```bash
   cd /pad/naar/docex
   ```
2. (Optioneel) activeer je virtuele omgeving.
3. Installeer pytest als dat nog niet gedaan is:

   ```bash
   pip install -U pytest
   ```
4. Run de tests:

   ```bash
   pytest -q
   ```

**Verwacht resultaat:** meerdere `passed` regels (bijv. `7 passed`), geen fouten.

### Enkele handige flags

* `pytest -q` — korte output.
* `pytest -k <expr>` — run alleen tests die matchen op `<expr>`.
* `pytest tests/test_core_tool_loader.py::test_call_first_callable_with_callable -q` — run één test

## CI

Er is een GitHub Actions workflow (`.github/workflows/python-test.yml`) die bij push/PR de tests uitvoert met Python 3.12. Zorg dat de workflow up-to-date is met je gewenste Python-versie.

## Interpretatie van failures (veelvoorkomende problemen)

* **`ModuleNotFoundError: No module named 'webapp'`**

  * Start pytest vanuit de projectroot. De tests zelf voegen de projectroot aan `sys.path`, maar als je in een vreemde omgeving draait, controleer dat `webapp/__init__.py` bestaat.
* **`module X not importable`** of `missing callable render()`

  * Controleer of het `page_module`-pad in `webapp/registry.py` exact overeenkomt met de locatie van het Python-bestand.
  * Controleer op syntaxfouten (bijv. verkeerde karakters) in het doelbestand.
* **`SyntaxError` tijdens import**

  * Open het genoemde bestand, kijk rond de aangegeven regel en verwijder stray characters of herstel de heredoc.

## Richtlijnen voor nieuwe tests

* Houd tests klein en deterministisch.
* Vermijd het daadwerkelijk aanroepen van `render()` van Streamlit-pagina's in CI, tenzij je die `render()` expliciet safe maakt (zonder Streamlit-initialisatie) of je mockt Streamlit-API calls.
* Voor nieuwe assistenten/tools: voeg de `page_module` toe aan `webapp/registry.py` en voeg (indien nodig) een test die exact dat page\_module importeert.

## Troubleshooting stappen (kort)

1. `pytest -q` -> noteer eerste failure.
2. Run `python - <<'PY' ...` snippet om te checken of module importable is met `importlib.util.find_spec`.
3. Kijk of er een syntax error is (`python -m py_compile path/to/file.py`).
4. Verwijder `.pyc` / `__pycache__` en `importlib.invalidate_caches()`.

---

Als je wil, kan ik deze README meteen toevoegen aan de repository (`tests/README.md`) en committen. Geef even je voorkeur: niet committen (ik maak het lokaal en je commit zelf) of committen (dan geef ik de `git`-commando's).
