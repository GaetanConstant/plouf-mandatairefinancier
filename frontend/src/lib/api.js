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

// Filet global : toute requête qui échoue doit se voir. Les écrans qui
// affichent déjà un message contextuel continuent de le faire — mais sur les
// quelque soixante-dix appels de l'application, la moitié n'en avait aucun, et
// un échec passait alors totalement inaperçu. Deux bêta-testeurs ont conclu
// « je n'ai pas réussi » devant un formulaire qui ne disait rien.
let onErreurServeur = null;

export function surErreurServeur(callback) {
    onErreurServeur = callback;
}

/** Message lisible tiré d'une erreur axios. */
export function messageErreur(erreur) {
    const detail = erreur.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    // Erreur de validation FastAPI : une liste d'objets.
    if (Array.isArray(detail) && detail.length) {
        return detail.map(d => d.msg || '').filter(Boolean).join(' · ') || 'Données refusées.';
    }
    if (erreur.response?.status >= 500) return "Le serveur a rencontré une erreur.";
    if (!erreur.response) return "Le serveur est injoignable.";
    return `Erreur ${erreur.response.status}.`;
}

axios.interceptors.response.use(
    (reponse) => reponse,
    (erreur) => {
        const url = erreur.config?.url || '';
        // Un 401 sur /login, c'est un mot de passe refusé, pas une session perdue.
        if (erreur.response?.status === 401 && !url.endsWith('/login')) {
            onSessionExpiree?.();
            return Promise.reject(erreur);
        }
        // La connexion gère son propre message ; les lectures échouées sont
        // déjà signalées par les écrans. Seules les écritures remontent ici.
        const ecriture = ['post', 'put', 'patch', 'delete']
            .includes((erreur.config?.method || '').toLowerCase());
        if (ecriture && !url.endsWith('/login')) {
            onErreurServeur?.(messageErreur(erreur));
        }
        return Promise.reject(erreur);
    },
);
