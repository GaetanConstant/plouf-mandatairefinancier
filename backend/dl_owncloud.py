import owncloud
import os

def download_file_from_owncloud(url, password, remote_file, local_file):
    """
    Télécharge un fichier depuis OwnCloud/NextCloud via un lien public
    
    Args:
        url: URL du lien public
        password: Mot de passe du lien public
        remote_file: Nom du fichier distant
        local_file: Chemin complet du fichier local de destination
    """
    oc = owncloud.Client.from_public_link(url, folder_password=password)
    oc.get_file(remote_file, local_file)
    print(f"✅ Fichier téléchargé avec succès : {local_file}")


if __name__ == "__main__":
    # Configuration
    hostname = 'nouveau.cloud117.fr'
    downloaded_url = "https://nouveau.cloud117.fr/s/NLEHT4s8rBCZYpQ"
    username = 'gaetanc@pm.me'
    password = 't88M^v$@scFE' 
    
    # Chemins des fichiers
    local_filename = 'Budget 2026.xlsx'
    remote_filename = 'Budget 2026.xlsx'
    
    # Définir le chemin d'export (dossier parent du backend)
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    export_path = os.path.dirname(backend_dir)  # Dossier mandatairefinancier
    local_file_path = os.path.join(export_path, local_filename)
    
    print(f"📥 Téléchargement de '{remote_filename}' depuis OwnCloud...")
    print(f"📁 Destination : {local_file_path}")
    
    try:
        download_file_from_owncloud(downloaded_url, password, remote_filename, local_file_path)
    except Exception as e:
        print(f"❌ Erreur lors du téléchargement : {e}")
