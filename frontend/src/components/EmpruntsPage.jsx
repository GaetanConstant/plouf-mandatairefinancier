import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Landmark, Plus, Trash2 } from 'lucide-react';
import { Modal, Button, Input, Select } from './ui/Components';
import { API_URL } from '../lib/api';

const eur = (v) => (v || 0).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });

const TYPES = [
    { value: 'banque', label: 'Emprunt bancaire (annexe 3.2)' },
    { value: 'parti', label: 'Emprunt parti politique (annexe 3.3)' },
    { value: 'personne_physique', label: 'Emprunt personne physique (annexe 3.4)' },
];
const TYPE_LABEL = { banque: 'Banque', parti: 'Parti', personne_physique: 'Personne physique' };

export function EmpruntsPage() {
    const qc = useQueryClient();
    const [open, setOpen] = useState(false);
    const [f, setF] = useState({ type: 'banque', preteur_nom: '', preteur_civilite: '', preteur_prenom: '', preteur_pays: 'France', date_contrat: '', duree_mois: '', date_fin: '', taux: '', montant: '' });

    const { data: emprunts, isLoading } = useQuery({ queryKey: ['emprunts'], queryFn: async () => (await axios.get(`${API_URL}/emprunts`)).data });
    const add = useMutation({
        mutationFn: (p) => axios.post(`${API_URL}/emprunts`, p),
        onSuccess: () => { qc.invalidateQueries(['emprunts']); setOpen(false); setF({ type: 'banque', preteur_nom: '', preteur_civilite: '', preteur_prenom: '', preteur_pays: 'France', date_contrat: '', duree_mois: '', date_fin: '', taux: '', montant: '' }); },
    });
    const del = useMutation({ mutationFn: (id) => axios.delete(`${API_URL}/emprunts/${id}`), onSuccess: () => qc.invalidateQueries(['emprunts']) });

    if (isLoading) return <div>Chargement...</div>;
    const isPP = f.type === 'personne_physique';

    const submit = () => add.mutate({
        ...f,
        duree_mois: f.duree_mois === '' ? null : Number(f.duree_mois),
        taux: f.taux === '' ? null : Number(f.taux),
        montant: Number(f.montant || 0),
        date_contrat: f.date_contrat || null,
        date_fin: f.date_fin || null,
    });

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <header className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Emprunts</h1>
                    <p className="text-muted-foreground">Contrats de prêt (banque / parti / personne physique) — détail exigé par la CNCCFP.</p>
                </div>
                <Button onClick={() => setOpen(true)} className="gap-2"><Plus className="w-4 h-4" /> Nouvel emprunt</Button>
            </header>

            <div className="rounded-md border border-border bg-card overflow-auto">
                <table className="w-full text-sm">
                    <thead className="[&_tr]:border-b"><tr className="text-left text-muted-foreground">
                        <th className="h-11 px-3 font-medium">Type</th><th className="h-11 px-3 font-medium">Prêteur</th><th className="h-11 px-3 font-medium">Pays</th>
                        <th className="h-11 px-3 font-medium">Date contrat</th><th className="h-11 px-3 font-medium">Durée</th><th className="h-11 px-3 font-medium">Taux</th>
                        <th className="h-11 px-3 font-medium text-right">Montant</th><th></th>
                    </tr></thead>
                    <tbody className="[&_tr:last-child]:border-0">
                        {emprunts?.map(e => (
                            <tr key={e.id} className="border-b hover:bg-muted/40">
                                <td className="px-3 py-2"><span className="text-xs bg-muted rounded-full px-2 py-0.5">{TYPE_LABEL[e.type]}</span></td>
                                <td className="px-3 py-2 font-medium">{[e.preteur_civilite, e.preteur_prenom, e.preteur_nom].filter(Boolean).join(' ')}</td>
                                <td className="px-3 py-2">{e.preteur_pays || '—'}</td>
                                <td className="px-3 py-2">{e.date_contrat || '—'}</td>
                                <td className="px-3 py-2">{e.duree_mois ? `${e.duree_mois} mois` : '—'}</td>
                                <td className="px-3 py-2">{e.taux != null ? `${e.taux} %` : '—'}</td>
                                <td className="px-3 py-2 text-right font-medium">{eur(e.montant)}</td>
                                <td className="px-3 py-2 text-right"><button onClick={() => del.mutate(e.id)} className="text-muted-foreground hover:text-red-600"><Trash2 className="w-4 h-4" /></button></td>
                            </tr>
                        ))}
                        {!emprunts?.length && <tr><td colSpan={8} className="p-8 text-center text-muted-foreground italic">Aucun emprunt.</td></tr>}
                    </tbody>
                </table>
            </div>

            <Modal isOpen={open} onClose={() => setOpen(false)} title="Nouvel emprunt">
                <div className="space-y-4">
                    <Select label="Type d'emprunt" options={TYPES} value={f.type} onChange={e => setF({ ...f, type: e.target.value })} />
                    {isPP ? (
                        <div className="grid grid-cols-3 gap-3">
                            <Input label="Civ." value={f.preteur_civilite} onChange={e => setF({ ...f, preteur_civilite: e.target.value })} />
                            <Input label="Prénom" value={f.preteur_prenom} onChange={e => setF({ ...f, preteur_prenom: e.target.value })} />
                            <Input label="Nom" value={f.preteur_nom} onChange={e => setF({ ...f, preteur_nom: e.target.value })} />
                        </div>
                    ) : (
                        <Input label={f.type === 'banque' ? "Établissement prêteur" : "Parti / groupement prêteur"} value={f.preteur_nom} onChange={e => setF({ ...f, preteur_nom: e.target.value })} />
                    )}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <Input label="Pays" value={f.preteur_pays} onChange={e => setF({ ...f, preteur_pays: e.target.value })} />
                        <Input label="Montant (€)" type="number" value={f.montant} onChange={e => setF({ ...f, montant: e.target.value })} />
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <Input label="Date du contrat" type="date" value={f.date_contrat} onChange={e => setF({ ...f, date_contrat: e.target.value })} />
                        <Input label="Date de fin" type="date" value={f.date_fin} onChange={e => setF({ ...f, date_fin: e.target.value })} />
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <Input label="Durée (mois)" type="number" value={f.duree_mois} onChange={e => setF({ ...f, duree_mois: e.target.value })} />
                        <Input label="Taux d'intérêt (%)" type="number" value={f.taux} onChange={e => setF({ ...f, taux: e.target.value })} />
                    </div>
                    <div className="flex justify-end gap-2 pt-2">
                        <Button variant="outline" onClick={() => setOpen(false)}>Annuler</Button>
                        <Button onClick={submit} isLoading={add.isPending}>Créer</Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}
