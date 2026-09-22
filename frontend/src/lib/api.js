/**
 * URL de base de l'API.
 *
 * En développement, le backend tourne sur http://localhost:8000.
 * En production, le front et l'API partagent le même domaine : `VITE_API_URL`
 * vaut `/api` et nginx relaie vers uvicorn.
 */
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
