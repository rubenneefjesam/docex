import docx

def read_docx(path: str) -> str:
    """
    Leest alle tekst uit een .docx-bestand en retourneert het als plain text.
    """
    try:
        doc = docx.Document(path)
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    except Exception as e:
        return f"[Fout bij lezen van .docx: {e}]"

def apply_replacements(doc_path: str, replacements: list[dict]) -> docx.Document:
    """
    Laadt een .docx-bestand, voert tekstvervangingen uit, en retourneert een aangepast docx.Document-object.
    Let op: dit retourneert het aangepaste documentobject, nog niet als bytes.
    """
    doc = docx.Document(doc_path)

    def replace_in_runs(runs):
        if not runs:
            return
        text = "".join(run.text for run in runs)
        for rep in replacements:
            text = text.replace(rep["find"], rep["replace"])
        runs[0].text = text
        for run in runs[1:]:
            run.text = ""

    for paragraph in doc.paragraphs:
        replace_in_runs(paragraph.runs)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    replace_in_runs(paragraph.runs)

    return doc
