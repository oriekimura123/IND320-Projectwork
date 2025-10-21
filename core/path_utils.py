# /core/path_utils.py
# Utility functions for handling project paths

import os
import sys

def get_repo_root_path():
    """
    Returnerer den absolutte stien til prosjektets rotmappe.
    Dette er den mest robuste metoden for å finne roten (IND320-Projectwork-Orie2).
    
    Returnerer:
        str: Absolutt sti til rotmappen.
    """
    # 1. Henter stien til filen som kaller denne funksjonen
    # Dette er den sikreste måten å finne Roten fra hvor som helst.
    current_file_path = os.path.abspath(os.path.dirname(__file__))

    # 2. Navigerer én mappe opp fra 'core' mappen for å finne Roten
    repo_root = os.path.abspath(os.path.join(current_file_path, '..'))
    
    return repo_root

def get_absolute_path(relative_path: str) -> str:
    """
    Konverterer en sti relativt til Rotmappen til en absolutt sti.
    Eks: get_absolute_path('data/myfile.csv')
    
    Returnerer:
        str: Absolutt sti til den forespurte filen/mappen.
    """
    repo_root = get_repo_root_path()
    return os.path.join(repo_root, relative_path)

# VIKTIG: Legg Rotmappen til i sys.path for å sikre imports fra 'core/'
# Dette er for å hjelpe imports i f.eks. Streamlit-hovedfilen.
# if get_repo_root_path() not in sys.path:
#    sys.path.append(get_repo_root_path())