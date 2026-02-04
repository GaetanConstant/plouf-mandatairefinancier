# 🗳️ Plouf - Mandataire Financier

Application de gestion financière pour les campagnes électorales. Elle permet de suivre les recettes, les dépenses, de gérer les concours en nature et de générer les reçus fiscaux signés pour les donateurs.

## 🏗️ Architecture
- **Backend** : FastAPI (Python) + DuckDB (Base de données locale ultra-rapide)
- **Frontend** : React + Vite + Tailwind CSS + Lucide React
- **Gestionnaire de paquets** : `uv` (Python) et `npm` (Node.js)

---

## 🚀 Installation et Lancement

### 1. Backend (Python)

Le backend utilise `uv` pour une gestion rapide des performances et des dépendances.

```bash
cd backend
# Installation des dépendances et lancement
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Le serveur sera disponible sur : `http://localhost:8000`

### 2. Frontend (React)

```bash
cd frontend
# Installation des dépendances
npm install
# Lancement en mode développement
npm run dev
```
L'application sera accessible sur : `http://localhost:5173` (ou le port affiché dans le terminal)

---

## 📂 Structure du projet

- `/backend` : Code API, modèles Pydantic, et utilitaires de génération PDF.
- `/frontend` : Interface utilisateur React.
- `/data` : Contient la base de données SQLite/DuckDB (`campagne.db`) et les justificatifs (exclu du Git).
- `.gitignore` : Configuration pour ne jamais envoyer les données de campagne (base de données, justificatifs, excels) sur GitHub.

---

## 📝 Fonctionnalités clés
- **Tableau de bord** : Vue consolidée du plafond légal, de la trésorerie et de la marge restante.
- **Gestion des dons** : Suivi des plafonds par donateur (4600€) et génération de reçus fiscaux PDF personnalisés.
- **Dépenses & Justificatifs** : Enregistrement avec upload de fichiers et catégorisation CNCCFP.
- **Concours en Nature** : Prise en compte dans le plafond légal sans impacter la trésorerie bancaire.
- **Attestations** : Suivi des envois aux donateurs avec horodatage.

---

## 🔒 Sécurité & Confidentialité
Le projet est configuré pour que **vos données restent locales**. Les fichiers `.db`, `.xlsx` et les signatures ne sont jamais synchronisés sur le dépôt distant (GitHub).

---
*Développé pour Gaëtan CONSTANT MAGNARD - Mandataire Financier.*
