import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { BookOpen, Plus, Ban } from 'lucide-react';
import { Modal, Button, Input } from './ui/Components';
import { cn } from '../lib/utils';
import { API_URL } from '../lib/api';


const STATUT_BADGE = {
    delivre: 'bg-green-500/10 text-green-600 border-green-500/20',
    annule: 'bg-red-500/10 text-red-600 border-red-500/20',
    non_utilise: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20',
};

export function CarnetsPage() {
    const queryClient = useQueryClient();
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [form, setForm] = useState({ numero_carnet: '', numero_formule_debut: '', numero_formule_fin: '', date_retrait_prefecture: '' });
    const [error, setError] = useState(null);

    const { data: carnets, isLoading } = useQuery({
        queryKey: ['carnets'],
        queryFn: async () => (await axios.get(`${API_URL}/carnets`)).data,
    });

    const { data: recus } = useQuery({
        queryKey: ['recus'],
        queryFn: async () => (await axios.get(`${API_URL}/recus`)).data,
    });

    const createMutation = useMutation({
        mutationFn: async (payload) => axios.post(`${API_URL}/carnets`, payload),
        onSuccess: () => {
            queryClient.invalidateQueries(['carnets']);
            setIsModalOpen(false);
            setForm({ numero_carnet: '', numero_formule_debut: '', numero_formule_fin: '', date_retrait_prefecture: '' });
        },
        onError: (err) => setError(err.response?.data?.detail || 'Erreur'),
    });

    const annulerMutation = useMutation({
        mutationFn: async (id) => axios.post(`${API_URL}/recus/${id}/annuler`),
        onSuccess: () => {
            queryClient.invalidateQueries(['recus']);
            queryClient.invalidateQueries(['carnets']);
        },
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        setError(null);
        const debut = Number(form.numero_formule_debut);
        const fin = Number(form.numero_formule_fin);
        if (!form.numero_carnet) { setError('Le numéro de carnet est requis'); return; }
        if (!debut || !fin || fin < debut) { setError('Plage de numéros invalide'); return; }
        createMutation.mutate({
            numero_carnet: form.numero_carnet,
            numero_formule_debut: debut,
            numero_formule_fin: fin,
            date_retrait_prefecture: form.date_retrait_prefecture || null,
        });
    };

    if (isLoading) return <div>Chargement des carnets...</div>;

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <header className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Carnets de reçus-dons</h1>
                    <p className="text-muted-foreground">Suivi des formules retirées en préfecture, délivrées et à restituer.</p>
                </div>
                <Button onClick={() => setIsModalOpen(true)} className="gap-2">
                    <Plus className="w-4 h-4" /> Nouveau carnet
                </Button>
            </header>

            {/* Carnets */}
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {carnets?.map((c) => (
                    <div key={c.id} className="bg-card rounded-xl border border-border p-5 shadow-sm">
                        <div className="flex items-center gap-2 mb-3">
                            <BookOpen className="w-5 h-5 text-primary" />
                            <h3 className="font-bold text-lg">{c.numero_carnet}</h3>
                        </div>
                        <p className="text-xs text-muted-foreground mb-3">
                            Formules {c.numero_formule_debut} → {c.numero_formule_fin}
                            {c.date_retrait_prefecture && ` • retiré le ${c.date_retrait_prefecture}`}
                        </p>
                        <div className="grid grid-cols-4 gap-2 text-center text-sm">
                            <Stat label="Total" value={c.nb_total} />
                            <Stat label="Délivrés" value={c.nb_delivres} cls="text-green-600" />
                            <Stat label="Annulés" value={c.nb_annules} cls="text-red-600" />
                            <Stat label="Restants" value={c.nb_restants} cls="text-yellow-600" />
                        </div>
                    </div>
                ))}
                {!carnets?.length && (
                    <div className="col-span-full py-16 text-center bg-card rounded-2xl border border-dashed border-border">
                        <BookOpen className="w-14 h-14 text-muted-foreground mx-auto mb-3 opacity-20" />
                        <p className="text-muted-foreground italic">Aucun carnet. Créez-en un pour commencer à délivrer des reçus numérotés.</p>
                    </div>
                )}
            </div>

            {/* Reçus délivrés */}
            <div>
                <h2 className="text-xl font-bold tracking-tight mb-3">Reçus délivrés</h2>
                <div className="rounded-md border border-border bg-card">
                    <div className="w-full overflow-x-auto"><table className="w-full caption-bottom text-sm">
                        <thead className="[&_tr]:border-b">
                            <tr className="border-b">
                                <th className="h-12 px-4 text-left font-medium text-muted-foreground">N° formule</th>
                                <th className="h-12 px-4 text-left font-medium text-muted-foreground">Donateur</th>
                                <th className="h-12 px-4 text-left font-medium text-muted-foreground">Date</th>
                                <th className="h-12 px-4 text-left font-medium text-muted-foreground">Statut</th>
                                <th className="h-12 px-4 text-center font-medium text-muted-foreground">Avantage fiscal</th>
                                <th className="h-12 px-4 text-right font-medium text-muted-foreground">Montant</th>
                                <th className="h-12 px-4 text-center font-medium text-muted-foreground"></th>
                            </tr>
                        </thead>
                        <tbody className="[&_tr:last-child]:border-0">
                            {recus?.map((r) => (
                                <tr key={r.id} className="border-b hover:bg-muted/50">
                                    <td className="p-4 font-mono font-medium">{r.numero_formule}</td>
                                    <td className="p-4">{r.nom_donateur || '—'}</td>
                                    <td className="p-4">{r.date}</td>
                                    <td className="p-4">
                                        <span className={cn('inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold', STATUT_BADGE[r.statut])}>
                                            {r.statut}
                                        </span>
                                    </td>
                                    <td className="p-4 text-center">{r.avantage_fiscal_eligible ? '✓' : '—'}</td>
                                    <td className="p-4 text-right font-medium">{r.montant?.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}</td>
                                    <td className="p-4 text-center">
                                        {r.statut === 'delivre' && (
                                            <button
                                                onClick={() => annulerMutation.mutate(r.id)}
                                                className="text-muted-foreground hover:text-red-600 transition-colors"
                                                title="Annuler ce reçu"
                                            >
                                                <Ban className="w-4 h-4" />
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                            {!recus?.length && (
                                <tr><td colSpan={7} className="p-8 text-center text-muted-foreground italic">Aucun reçu délivré pour l'instant.</td></tr>
                            )}
                        </tbody>
                    </table></div>
                </div>
            </div>

            <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Nouveau carnet de reçus">
                <form onSubmit={handleSubmit} className="space-y-4">
                    {error && <div className="p-3 text-sm bg-destructive/10 text-destructive rounded-md border border-destructive/20">{error}</div>}
                    <Input label="Numéro de carnet" placeholder="Ex: CARN-001" value={form.numero_carnet}
                        onChange={e => setForm({ ...form, numero_carnet: e.target.value })} required />
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <Input label="Première formule" type="number" value={form.numero_formule_debut}
                            onChange={e => setForm({ ...form, numero_formule_debut: e.target.value })} required />
                        <Input label="Dernière formule" type="number" value={form.numero_formule_fin}
                            onChange={e => setForm({ ...form, numero_formule_fin: e.target.value })} required />
                    </div>
                    <Input label="Date de retrait en préfecture" type="date" value={form.date_retrait_prefecture}
                        onChange={e => setForm({ ...form, date_retrait_prefecture: e.target.value })} />
                    <div className="pt-4 flex justify-end gap-2">
                        <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>Annuler</Button>
                        <Button type="submit" isLoading={createMutation.isPending}>Créer le carnet</Button>
                    </div>
                </form>
            </Modal>
        </div>
    );
}

function Stat({ label, value, cls }) {
    return (
        <div>
            <div className={cn('font-bold text-lg', cls)}>{value}</div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
        </div>
    );
}
