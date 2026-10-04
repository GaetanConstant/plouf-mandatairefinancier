import React, { useEffect, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { surErreurServeur } from '../lib/api';

const DUREE = 8000;

/**
 * Dernière erreur d'écriture, affichée en bas d'écran.
 *
 * Filet de sécurité, pas remplacement : les formulaires qui affichent déjà un
 * message contextuel le gardent. Celle-ci couvre tout le reste — sans elle, un
 * enregistrement refusé ne produisait aucun signe visible.
 */
export function BanniereErreur() {
    const [message, setMessage] = useState(null);

    useEffect(() => {
        surErreurServeur((texte) => setMessage({ texte, cle: Date.now() }));
        return () => surErreurServeur(null);
    }, []);

    useEffect(() => {
        if (!message) return undefined;
        const t = setTimeout(() => setMessage(null), DUREE);
        return () => clearTimeout(t);
    }, [message]);

    if (!message) return null;

    return (
        <div role="alert"
            className="fixed bottom-5 left-1/2 z-50 flex max-w-[min(560px,92vw)] -translate-x-1/2 items-start gap-3 rounded-xl border border-destructive/30 bg-destructive/95 px-4 py-3 text-sm text-white shadow-lg animate-in fade-in slide-in-from-bottom-4">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span className="flex-1">{message.texte}</span>
            <button onClick={() => setMessage(null)} title="Fermer"
                className="shrink-0 opacity-80 transition-opacity hover:opacity-100">
                <X className="h-4 w-4" />
            </button>
        </div>
    );
}
