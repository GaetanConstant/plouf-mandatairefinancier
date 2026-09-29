import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { CheckCircle2, ChevronRight, ListChecks, Upload } from 'lucide-react';
import { Button } from './ui/Components';
import { API_URL } from '../lib/api';

// Où déposer le fichier, selon la nature de ce qui manque. Le reste des
// manques ne se règle pas par une pièce : on renvoie vers l'écran de saisie.
const DEPOTS = {
    depense: (a, chemin) =>
        axios.post(`${API_URL}/depenses/${a.id}/piece`, { fichier: chemin, type_piece: 'facture' }),
    recette: (a, chemin) =>
        axios.post(`${API_URL}/recettes/${a.id}/piece`, { fichier: chemin, type_piece: 'recu' }),
    piece_declarative: (a, chemin) =>
        axios.put(`${API_URL}/identite/pieces-declaratives/${a.cle}`, { fichier: chemin }),
};

const eur = (v) => (v ?? 0).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });

/**
 * Ce qui reste à réunir avant de pouvoir déposer le compte.
 *
 * Les manques étaient jusqu'ici énoncés sans pouvoir être traités : il fallait
 * lire la liste, retenir la ligne, puis la retrouver dans un autre écran. Ici,
 * ce qui se règle par un fichier se règle sur place ; le reste renvoie d'un
 * clic à l'endroit de la saisie.
 */
export function ResteAFairePage({ onNavigate }) {
    const { data: completude, isLoading } = useQuery({
        queryKey: ['completude'],
        queryFn: async () => (await axios.get(`${API_URL}/identite/completude`)).data,
    });

    if (isLoading) return <div>Chargement du reste à faire...</div>;
    if (!completude) return null;

    const aTraiter = completude.sections.filter(s => !s.complet);

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <header>
                <h1 className="text-3xl font-bold tracking-tight">Reste à faire</h1>
                <p className="text-muted-foreground">
                    Ce qu'il manque pour que le dossier puisse être déposé, traitable d'ici.
                </p>
            </header>

            <Bandeau etat={completude} />

            {!aTraiter.length && (
                <div className="rounded-2xl border border-emerald-300 bg-emerald-50/50 p-8 text-center">
                    <CheckCircle2 className="mx-auto mb-3 h-12 w-12 text-emerald-600" />
                    <p className="font-bold text-emerald-700">Plus rien à réunir.</p>
                    <p className="text-sm text-emerald-700/80">
                        Le dossier est complet — l'export est ouvert depuis l'écran Dépôt.
                    </p>
                </div>
            )}

            {aTraiter.map(section => (
                <Section key={section.cle} section={section} onNavigate={onNavigate} />
            ))}
        </div>
    );
}

function Bandeau({ etat }) {
    const reste = etat.manquants.length;
    return (
        <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
            <div className="mb-3 flex items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                    <ListChecks className="h-5 w-5 text-primary" />
                    <h2 className="font-bold">
                        {reste} élément{reste > 1 ? 's' : ''} à traiter
                    </h2>
                </div>
                <span className="text-2xl font-black text-primary">{etat.pct}%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
                <div className="h-full bg-primary transition-all duration-700"
                    style={{ width: `${etat.pct}%` }} />
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
                {etat.remplis} sur {etat.requis} éléments exigés pour le dépôt.
            </p>
        </div>
    );
}

function Section({ section, onNavigate }) {
    const fichiers = section.actions.filter(a => DEPOTS[a.type]);
    const ecrans = section.actions.filter(a => a.type === 'ecran');

    return (
        <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
            <div className="mb-3 flex items-center justify-between gap-3">
                <h2 className="font-bold">{section.titre}</h2>
                <span className="text-sm font-medium text-muted-foreground">
                    {section.remplis}/{section.requis}
                </span>
            </div>

            {fichiers.map(action => (
                <LigneFichier key={`${action.type}-${action.id ?? action.cle}`} action={action} />
            ))}

            {/* Manques qui ne se règlent pas par un fichier : champs de saisie,
                rangs de la liste, relevé à importer. */}
            {!fichiers.length && (
                <ul className="mb-3 ml-5 list-disc space-y-0.5 text-sm text-muted-foreground">
                    {section.manquants.map((m, i) => <li key={i}>{m}</li>)}
                </ul>
            )}

            {ecrans.map(action => (
                <Button key={action.onglet} variant="outline" className="gap-1"
                    onClick={() => onNavigate(action.onglet, action.cible ? { entite: action.cible } : null)}>
                    {action.libelle} <ChevronRight className="h-4 w-4" />
                </Button>
            ))}
        </div>
    );
}

function LigneFichier({ action }) {
    const queryClient = useQueryClient();
    const [erreur, setErreur] = useState('');

    const deposer = useMutation({
        mutationFn: async (fichier) => {
            const body = new FormData();
            body.append('file', fichier);
            const { data } = await axios.post(`${API_URL}/upload`, body, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            await DEPOTS[action.type](action, data.path);
        },
        onSuccess: () => ['completude', 'depenses', 'recettes', 'pieces-declaratives', 'documents']
            .forEach(k => queryClient.invalidateQueries([k])),
        onError: (err) => setErreur(err.response?.data?.detail || 'Le dépôt a échoué.'),
    });

    const detail = [action.tiers, action.montant != null ? eur(action.montant) : null]
        .filter(Boolean).join(' · ');

    return (
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 py-3 last:border-0">
            <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">
                    {action.num_piece && (
                        <span className="mr-2 font-mono text-xs text-muted-foreground">{action.num_piece}</span>
                    )}
                    {action.libelle}
                </p>
                {detail && <p className="text-xs text-muted-foreground">{detail}</p>}
                {erreur && <p className="text-xs text-destructive">{erreur}</p>}
            </div>

            <label className="inline-flex shrink-0 cursor-pointer items-center gap-1.5 rounded-md border border-input px-3 py-1.5 text-xs font-medium transition-colors hover:border-primary hover:text-primary">
                <Upload className="h-3.5 w-3.5" />
                {deposer.isPending ? 'Envoi...' : 'Déposer la pièce'}
                <input type="file" className="hidden" disabled={deposer.isPending}
                    onChange={e => { setErreur(''); if (e.target.files[0]) deposer.mutate(e.target.files[0]); }} />
            </label>
        </div>
    );
}
