import subprocess

import toml

# Ouverture du fichier pyproject.toml
with open("pyproject.toml") as file:
    # Parsing du fichier TOML
    pyproject = toml.loads(file.read())

# Récupération des dépendances de développement
dev_dependencies = pyproject["project"]["dependencies"]

# Boucle pour extraire les noms des packages sans la version
packages = []
for package in dev_dependencies:
    package_name = package.split("==")[0].strip()
    packages.append(package_name)

subprocess.run(
    [
        "pip-licenses",
        "--from",
        "meta",
        "-f",
        "md",
        "-a",
        "-u",
        "-d",
        "--output-file",
        "third_party.md",
        "-p",
    ]
    + packages
)
