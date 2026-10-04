import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Check, Download, FileText, HandCoins, Plus, Trash2, Upload } from 'lucide-react';
import { Button, Modal } from './ui/Components';
import { ExpenseForm } from './ExpenseForm';
import { API_URL, messageErreur } from '../lib/api';

const eur = (v) => (v ?? 0).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });

/**
 * Notes de frais : les avances d'une personne, regroupées en un document.
 *
 * L'état n'est pas saisi — une note est remboursée quand toutes ses dépenses
 * sont rapprochées au relevé. Une case cochée en plus du compte finirait par
 * le contredire.
 */
export function NotesFraisPage() {
    const queryClient = useQueryClient();
    const [erreur, setErreur] = useState('');
    // Saisie d'une dépense avancée sans quitter l'écran : c'est ici qu'on
    // traite la pile de reçus qu'une personne vient de remettre.
    const [saisie, setSaisie] = useState(null);

    const rafraichir = () => ['notes-frais', 'avances', 'depenses', 'completude']
        .forEach(k => queryClient.invalidateQueries([k]));

    const { data: notes, isLoading } = useQuery({
        queryKey: ['notes-frais'],
        queryFn: async () => (await axios.get(`${API_URL}/notes-frais`)).data,
    });
    const { data: avances } = useQuery({
        queryKey: ['avances'],
        queryFn: async () => (await axios.get(`${API_URL}/avances`)).data,
    });

    const creer = useMutation({
        mutationFn: async (personne) => axios.post(`${API_URL}/notes-frais`, { personne }),
        onSuccess: () => { rafraichir(); setErreur(''); },
        onError: (err) => setErreur(messageErreur(err)),
    });
    const supprimer = useMutation({
        mutationFn: async (id) => axios.delete(`${API_URL}/notes-frais/${id}`),
        onSuccess: rafraichir,
        onError: (err) => setErreur(messageErreur(err)),
    });

    if (isLoading) return <div>Chargement des notes de frais...</div>;

    // Personnes ayant des avances pas encore regroupées : celles déjà dans une
    // note sont suivies par la note, les reproposer ferait doublon.
    const aRegrouper = (avances || [])
        .map(a => ({ ...a, lignes: a.lignes.filter(l => !l.note_frais_id) }))
        .filter(a => a.lignes.length)
        .map(a => ({ ...a, total: Math.round(a.lignes.reduce((t, l) => t + (l.montant || 0), 0) * 100) / 100 }));

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <header className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Notes de frais</h1>
                    <p className="text-muted-foreground">
                        Les sommes avancées par une personne, regroupées en un document à signer.
                    </p>
                </div>
                <Button className="gap-2" onClick={() => setSaisie({ avance_par: '' })}>
                    <Plus className="h-4 w-4" /> Dépense avancée
                </Button>
            </header>

            {erreur && <p className="text-sm text-destructive">{erreur}</p>}

            {Boolean(aRegrouper.length) && (
                <div className="rounded-xl border border-amber-300 bg-amber-50/50 p-4">
                    <div className="mb-3 flex items-center gap-2">
                        <HandCoins className="h-4 w-4 text-amber-600" />
                        <h2 className="text-sm font-bold text-amber-800">Avances sans note</h2>
                    </div>
                    <ul className="space-y-2">
                        {aRegrouper.map(a => (
                            <li key={a.personne} className="flex items-center justify-between gap-3 text-sm">
                                <span>
                                    {a.personne}
                                    <span className="ml-2 text-xs text-muted-foreground">
                                        {a.lignes.length} dépense{a.lignes.length > 1 ? 's' : ''} · {eur(a.total)}
                                    </span>
                                </span>
                                <div className="flex shrink-0 items-center gap-3">
                                    <button type="button"
                                        onClick={() => setSaisie({ avance_par: a.personne })}
                                        className="inline-flex items-center gap-1 text-xs text-primary hover:underline">
                                        <Plus className="h-3 w-3" /> dépense
                                    </button>
                                    <Button variant="outline" isLoading={creer.isPending}
                                        onClick={() => creer.mutate(a.personne)}>
                                        Établir la note
                                    </Button>
                                </div>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {!notes?.length ? (
                <div className="rounded-2xl border border-dashed border-border px-6 py-14 text-center">
                    <FileText className="mx-auto mb-3 h-12 w-12 text-muted-foreground opacity-20" />
                    <p className="font-medium text-muted-foreground">Aucune note de frais.</p>
                    <p className="mx-auto mt-2 max-w-lg text-sm text-muted-foreground/80">
                        Une note regroupe les dépenses dont quelqu'un a avancé le montant —
                        l'essence d'un colleur, les menues dépenses du candidat. Saisissez la
                        dépense en indiquant qui l'a avancée : elle apparaîtra ici, prête à
                        être regroupée.
                    </p>
                    <Button className="mt-5 gap-2" onClick={() => setSaisie({ avance_par: '' })}>
                        <Plus className="h-4 w-4" /> Saisir une dépense avancée
                    </Button>
                </div>
            ) : notes.map(note => (
                <div key={note.id} className="rounded-xl border border-border bg-card">
                    <div className="flex flex-wrap items-center gap-3 border-b border-border px-5 py-3">
                        <h3 className="font-semibold">{note.personne}</h3>
                        <span className="text-xs text-muted-foreground">
                            {note.date_creation} · {note.nb_lignes} ligne(s)
                        </span>
                        <span className="font-bold tabular-nums">{eur(note.total)}</span>
                        {note.remboursee ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-700">
                                <Check className="h-3 w-3" /> remboursée
                            </span>
                        ) : (
                            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-700">
                                à rembourser
                            </span>
                        )}
                        <a href={`${API_URL}/notes-frais/${note.id}/pdf`} target="_blank"
                            rel="noopener noreferrer"
                            className="ml-auto inline-flex items-center gap-1 text-xs text-primary hover:underline">
                            <Download className="h-3.5 w-3.5" /> Note à signer (PDF)
                        </a>
                        <PieceNote note={note} onFait={rafraichir} />
                        <button onClick={() => window.confirm(
                            `Supprimer la note de ${note.personne} ? Les dépenses sont conservées.`)
                            && supprimer.mutate(note.id)}
                            title="Supprimer la note"
                            className="text-muted-foreground transition-colors hover:text-destructive">
                            <Trash2 className="h-4 w-4" />
                        </button>
                    </div>
                    <div>
                        {note.lignes.map(l => (
                            <div key={l.id} className="flex flex-wrap items-center gap-3 border-b border-border/60 px-5 py-2 text-sm last:border-0">
                                <span className="w-16 shrink-0 font-mono text-xs text-muted-foreground">{l.num_piece}</span>
                                <span className="w-24 shrink-0 text-xs text-muted-foreground">{l.date}</span>
                                <span className="flex-1">{l.libelle}
                                    {l.fournisseur && <span className="text-muted-foreground"> · {l.fournisseur}</span>}
                                </span>
                                {l.rapprochee && <Check className="h-3.5 w-3.5 text-emerald-600" />}
                                <span className="tabular-nums">{eur(l.montant)}</span>
                            </div>
                        ))}
                    </div>
                    {!note.remboursee && (
                        <p className="px-5 py-2 text-[11px] text-muted-foreground">
                            La note passera à « remboursée » quand toutes ses lignes seront
                            rapprochées au relevé — un seul virement peut toutes les régler.
                        </p>
                    )}
                </div>
            ))}
            <Modal isOpen={Boolean(saisie)} onClose={() => setSaisie(null)}
                title={saisie?.avance_par
                    ? `Dépense avancée par ${saisie.avance_par}`
                    : 'Dépense avancée'}>
                {saisie && (
                    <ExpenseForm prefilledData={saisie} onClose={() => setSaisie(null)} />
                )}
            </Modal>
        </div>
    );
}

/** Preuve du remboursement : virement, reçu signé. */
function PieceNote({ note, onFait }) {
    const [erreur, setErreur] = useState('');

    const deposer = useMutation({
        mutationFn: async (fichier) => {
            const body = new FormData();
            body.append('file', fichier);
            const { data } = await axios.post(`${API_URL}/upload`, body, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            await axios.post(`${API_URL}/notes-frais/${note.id}/piece`, { fichier: data.path });
        },
        onSuccess: onFait,
        onError: (err) => setErreur(messageErreur(err)),
    });

    if (note.justificatif) {
        return (
            <a href={`${API_URL}/docs/${note.justificatif}`} target="_blank" rel="noopener noreferrer"
                title="Justificatif du remboursement"
                className="inline-flex items-center gap-1 text-xs text-primary hover:underline">
                <FileText className="h-3.5 w-3.5" /> justificatif
            </a>
        );
    }

    return (
        <label title={erreur || "Déposer la preuve du remboursement"}
            className="inline-flex cursor-pointer items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-primary">
            <Upload className="h-3.5 w-3.5" />
            {deposer.isPending ? 'Envoi...' : 'justificatif'}
            <input type="file" className="hidden" disabled={deposer.isPending}
                onChange={e => e.target.files[0] && deposer.mutate(e.target.files[0])} />
        </label>
    );
}
