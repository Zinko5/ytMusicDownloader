import sys

def select_from_list(items, title="Seleccione una opción:", allow_all=True, all_label="[TODAS]"):
    """Generic list selector."""
    if not items:
        print("No hay elementos disponibles.")
        return None
        
    print(f"\n{title}")
    if allow_all:
        print(f"0. {all_label}")
        
    for i, item in enumerate(items, 1):
        print(f"{i}. {item}")
    
    while True:
        try:
            choice = input(f"\nSeleccione un número (0-{len(items)}): ").strip()
            if not choice:
                return None
            idx = int(choice)
            if idx == 0 and allow_all:
                return "__ALL__"
            if 1 <= idx <= len(items):
                return items[idx-1]
            else:
                print("Número fuera de rango.")
        except ValueError:
            print("Entrada no válida.")

def confirm_action(prompt="¿Desea continuar? (s/N): "):
    """Standard Y/N confirmation."""
    choice = input(prompt).strip().lower()
    return choice == 's'

def run_with_preview(items, process_func, item_label="archivo", action_label="procesar"):
    """
    Standard workflow: 
    1. List items to be changed.
    2. Ask for confirmation.
    3. Process.
    """
    if not items:
        print(f"No hay nada para {action_label}.")
        return
        
    print(f"\nSe han encontrado {len(items)} {item_label}(s) para {action_label}:")
    for item in items[:15]: # Show first 15
        # If it's a dictionary with a 'path' key, use that for display
        display_val = item['path'].name if isinstance(item, dict) and 'path' in item else item
        # If it's still a Path object, get its name
        if hasattr(display_val, 'name'):
            display_val = display_val.name
        print(f"  - {display_val}")
    
    if len(items) > 15:
        print(f"  ... y {len(items)-15} más.")
        
    if confirm_action(f"\n¿Desea {action_label} estos {len(items)} {item_label}(s)? (s/N): "):
        print(f"\nIniciando {action_label}...")
        success = 0
        for item in items:
            if process_func(item):
                success += 1
        print(f"\nFinalizado. Exitosos: {success} | Errores: {len(items)-success}")
    else:
        print("Operación cancelada.")

def menu_select_folder():
    """Helper to select a music folder from the library."""
    from .filesystem import get_music_folders
    folders = get_music_folders()
    return select_from_list(folders, "Seleccione carpeta de música:")

def menu_select_playlist():
    """Helper to select a saved playlist from the configuration."""
    from .youtube import load_playlists
    playlists = load_playlists()
    keys = sorted(playlists.keys())
    name = select_from_list(keys, "Seleccione una playlist guardada:")
    if name == "__ALL__":
        return "__ALL__", "__ALL__"
    if name:
        return playlists[name], name
    return None, None

def run_folder_workflow(gather_func, item_label, action_label, process_func):
    """
    The ultimate modular workflow:
    1. Asks for folder.
    2. Scans with live feedback (handling __ALL__ automatically).
    3. Runs preview and confirmation.
    4. Executes process_func on confirmed items.
    """
    from .config import MUSIC_BASE_DIR
    from .filesystem import get_music_folders
    
    folder = menu_select_folder()
    if folder is None:
        return

    all_items = []
    if folder == "__ALL__":
        subfolders = get_music_folders()
        print(f"\nEscaneando biblioteca completa para {action_label}...")
        for sub in subfolders:
            print(f"  > Analizando: {sub}")
            all_items.extend(gather_func(MUSIC_BASE_DIR / sub, sub))
    else:
        print(f"\nEscaneando: {folder}...")
        all_items.extend(gather_func(MUSIC_BASE_DIR / folder, folder))

    run_with_preview(all_items, process_func, item_label, action_label)
