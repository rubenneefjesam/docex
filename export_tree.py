#!/usr/bin/env python3
import os

def write_tree(root_dir: str, out_file: str):
    with open(out_file, 'w', encoding='utf-8') as f:
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # bereken indent-niveau
            level = dirpath.replace(root_dir, '').count(os.sep)
            indent = '    ' * level
            # schrijf de directory
            f.write(f"{indent}{os.path.basename(dirpath)}/\n")
            # schrijf de bestanden
            for filename in filenames:
                f.write(f"{indent}    {filename}\n")

if __name__ == "__main__":
    project_root = os.path.abspath(os.path.dirname(__file__))
    output_file = os.path.join(project_root, 'project_structure.txt')
    write_tree(project_root, output_file)
    print(f"Structuur geschreven naar {output_file}")
