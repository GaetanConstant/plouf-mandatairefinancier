import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Gift, Plus, Trash2 } from 'lucide-react';
import { Button, Input, Modal, Select } from './ui/Components';
import { CATEGORIES_CNCCFP, ORIGINES_CONCOURS } from '../lib/constants';
import { API_URL } from '../lib/api';

const eur = (v) => (v ?? 0).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });

export function ConcoursNaturePage() {
    const queryClient = useQueryClient();
    const [ouvert, setOuvert] = useState(false);

    const { data: concours, isLoading } = useQuery({
        queryKey: ['concours-nature'],
        queryFn: async () => (await axios.get(`${API_URL}/concours-nature`)).data,
    });
    const { data: synthese } = useQuery({
        queryKey: ['concours-synthese'],
        queryFn: async () => (await axios.get(`${API_URL}/concours-nature/synthese`)).data,
    });

    const supprimer = useMutation({
        mutationFn: async (id) => axios.delete(`${API_URL}/concours-nature/${id}`),
        onSuccess: () => ['concours-nature', 'concours-synthese', 'stats', 'completude']
            .forEach(k => queryClient.invalidateQueries([k])),
    });

    if (isLoading) return <div>Chargement des concours en nature...</div>;

    return (
        <div className="space-y-5 animate-in fade-in duration-500">
            <header className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight">Concours en nature</h2>
                    <p className="text-sm text-muted-foreground">
                        Biens et services fournis gratuitement à la campagne. Ils consomment
                        le plafond légal sans passer par la trésorerie, et forment l'annexe 4 du compte.
                    </p>
                </div>
                <Button className="gap-2" onClick={() => setOuvert(true)}>
                    <Plus className="h-4 w-4" /> Déclarer un concours
                </Button>
            </header>

            {synthese && synthese.nombre > 0 && (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    {Object.entries(synthese.par_origine).map(([cle, bloc]) => (
                        <div key={cle} className="rounded-md border border-border bg-card p-4">
                            <div className="text-xs uppercase tracking-wide text-muted-foreground">{bloc.libelle}</div>
                            <div className="mt-1 text-xl font-bold">{eur(bloc.montant)}</div>
                        </div>
                    ))}
                    <div className="rounded-md border border-primary/30 bg-primary/5 p-4">
                        <div className="text-xs uppercase tracking-wide text-primary">Total — annexe 4</div>
                        <div className="mt-1 text-xl font-bold text-primary">{eur(synthese.total)}</div>
                    </div>
                </div>
            )}

            {!concours?.length ? (
                <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-12 text-center">
                    <Gift className="mb-3 h-12 w-12 text-muted-foreground opacity-20" />
                    <p className="font-medium text-muted-foreground">Aucun concours en nature déclaré.</p>
                    <p className="mt-1 text-xs text-muted-foreground/70">
                        Local prêté, véhicule mis à disposition, prestation bénévole valorisée…
                    </p>
                </div>
            ) : (
                <div className="w-full overflow-x-auto rounded-md border border-border bg-card">
                    <table className="w-full caption-bottom text-sm">
                        <thead className="[&_tr]:border-b">
                            <tr className="border-b">
                                <th className="h-11 px-3 text-left font-medium text-muted-foreground">Origine</th>
                                <th className="h-11 px-3 text-left font-medium text-muted-foreground">Nature</th>
                                <th className="h-11 px-3 text-left font-medium text-muted-foreground">Méthode d'évaluation</th>
                                <th className="h-11 px-3 text-left font-medium text-muted-foreground">Rubrique</th>
                                <th className="h-11 px-3 text-right font-medium text-muted-foreground">Valeur estimée</th>
                                <th className="h-11 px-3 text-center font-medium text-muted-foreground"></th>
                            </tr>
                        </thead>
                        <tbody>
                            {concours.map(c => (
                                <tr key={c.id} className="border-b transition-colors last:border-0 hover:bg-muted/40">
                                    <td className="p-3 whitespace-nowrap">{c.origine_label}</td>
                                    <td className="p-3 font-medium">{c.nature}</td>
                                    <td className="p-3 text-xs text-muted-foreground">{c.methode_evaluation || '—'}</td>
                                    <td className="p-3">{c.rubrique_imputation || '—'}</td>
                                    <td className="p-3 text-right font-semibold">{eur(c.valeur_estimee)}</td>
                                    <td className="p-3 text-center">
                                        <button onClick={() => supprimer.mutate(c.id)} title="Supprimer"
                                            className="text-muted-foreground transition-colors hover:text-destructive">
                                            <Trash2 className="h-4 w-4" />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            <Modal isOpen={ouvert} onClose={() => setOuvert(false)} title="Déclarer un concours en nature">
                <FormulaireConcours onClose={() => setOuvert(false)} />
            </Modal>
        </div>
    );
}


function FormulaireConcours({ onClose }) {
    const queryClient = useQueryClient();
    const [f, setF] = useState({
        origine: ORIGINES_CONCOURS[0].value, nature: '', valeur_estimee: '',
        methode_evaluation: '', rubrique_imputation: CATEGORIES_CNCCFP[0].code,
    });
    const [erreur, setErreur] = useState('');

    const creer = useMutation({
        mutationFn: async () => axios.post(`${API_URL}/concours-nature`, {
            ...f, valeur_estimee: Number(f.valeur_estimee),
        }),
        onSuccess: () => {
            ['concours-nature', 'concours-synthese', 'stats', 'completude']
                .forEach(k => queryClient.invalidateQueries([k]));
            onClose();
        },
        onError: (err) => setErreur(err.response?.data?.detail || 'Enregistrement impossible.'),
    });

    return (
        <div className="space-y-4">
            <Select label="Origine du concours" options={ORIGINES_CONCOURS}
                value={f.origine} onChange={e => setF({ ...f, origine: e.target.value })} />

            <Input label="Nature du concours" placeholder="Ex : mise à disposition d'une salle"
                value={f.nature} onChange={e => setF({ ...f, nature: e.target.value })} />

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Input label="Valeur estimée (€)" type="number" step="0.01"
                    value={f.valeur_estimee} onChange={e => setF({ ...f, valeur_estimee: e.target.value })} />
                <Select label="Rubrique CNCCFP"
                    options={CATEGORIES_CNCCFP.map(c => ({ value: c.code, label: `${c.code} — ${c.label}` }))}
                    value={f.rubrique_imputation}
                    onChange={e => setF({ ...f, rubrique_imputation: e.target.value })} />
            </div>

            <Input label="Méthode d'évaluation"
                placeholder="Ex : loyer de marché constaté pour un local équivalent"
                value={f.methode_evaluation}
                onChange={e => setF({ ...f, methode_evaluation: e.target.value })} />
            <p className="text-xs text-muted-foreground">
                La commission demande sur quelle base la valeur a été estimée : sans méthode,
                le concours est contestable.
            </p>

            {erreur && <p className="text-sm text-destructive">{erreur}</p>}

            <div className="flex justify-end gap-2 pt-2">
                <Button variant="outline" onClick={onClose}>Annuler</Button>
                <Button isLoading={creer.isPending}
                    onClick={() => f.nature.trim() && Number(f.valeur_estimee) > 0 && creer.mutate()}>
                    Déclarer
                </Button>
            </div>
        </div>
    );
}
