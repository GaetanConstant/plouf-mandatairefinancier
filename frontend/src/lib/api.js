import axios from 'axios';

/**
 * URL de base de l'API.
 *
 * En développement, le backend tourne sur http://localhost:8000.
 * En production, le front et l'API partagent le même domaine : `VITE_API_URL`
 * vaut `/api` et nginx relaie vers uvicorn.
 */
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';


// Session expirée : sans cela chaque écran affiche sa propre erreur et
// l'application paraît cassée, alors qu'il suffit de se reconnecter.
// `onSessionExpiree` est posé par App au montage.
let onSessionExpiree = null;

export function surSessionExpiree(callback) {
    onSessionExpiree = callback;
}

axios.defaults.withCredentials = true;

axios.interceptors.response.use(
    (reponse) => reponse,
    (erreur) => {
        const url = erreur.config?.url || '';
        // Un 401 sur /login, c'est un mot de passe refusé, pas une session perdue.
        if (erreur.response?.status === 401 && !url.endsWith('/login')) {
            onSessionExpiree?.();
        }
        return Promise.reject(erreur);
    },
);
