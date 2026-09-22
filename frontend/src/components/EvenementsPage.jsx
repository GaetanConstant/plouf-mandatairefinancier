import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { CalendarDays, Plus, Trash2, Link2, X } from 'lucide-react';
import { Modal, Button, Input, Select } from './ui/Components';
import { API_URL } from '../lib/api';


const TYPES_EVT = ['reunion_publique', 'collecte', 'tractage', 'meeting', 'porte_a_porte', 'reception', 'autre']
    .map(v => ({ value: v, label: v.replace(/_/g, ' ') }));

const eur = (v) => (v || 0).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });

export function EvenementsPage() {
    const queryClient = useQueryClient();
    const [createOpen, setCreateOpen] = useState(false);
    const [detailId, setDetailId] = useState(null);
    const [form, setForm] = useState({ titre: '', type: 'meeting', date_debut: '', date_fin: '', lieu: '', description: '' });

    const { data: evenements, isLoading } = useQuery({
        queryKey: ['evenements'],
        queryFn: async () => (await axios.get(`${API_URL}/evenements`)).data,
    });

    const invalidate = () => {
        queryClient.invalidateQueries(['evenements']);
        queryClient.invalidateQueries(['frise']);
    };

    const createMutation = useMutation({
        mutationFn: async (p) => axios.post(`${API_URL}/evenements`, p),
        onSuccess: () => { invalidate(); setCreateOpen(false); setForm({ titre: '', type: 'meeting', date_debut: '', date_fin: '', lieu: '', description: '' }); },
    });
    const deleteMutation = useMutation({
        mutationFn: async (id) => axios.delete(`${API_URL}/evenements/${id}`),
        onSuccess: invalidate,
    });

    if (isLoading) return <div>Chargement des événements...</div>;

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Événements</h1>
                    <p className="text-muted-foreground">Regroupez vos dépenses par événement (coût calculé par quote-part).</p>
                </div>
                <Button onClick={() => setCreateOpen(true)} className="gap-2"><Plus className="w-4 h-4" /> Nouvel événement</Button>
            </header>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {evenements?.map((e) => (
                    <div key={e.id} className="bg-card rounded-xl border border-border p-5 shadow-sm cursor-pointer hover:border-primary/30 transition-colors"
                        onClick={() => setDetailId(e.id)}>
                        <div className="flex items-start justify-between">
                            <div className="flex items-center gap-2">
                                <CalendarDays className="w-5 h-5 text-primary" />
                                <h3 className="font-bold">{e.titre}</h3>
                            </div>
                            <button onClick={(ev) => { ev.stopPropagation(); deleteMutation.mutate(e.id); }} className="text-muted-foreground hover:text-red-600">
                                <Trash2 className="w-4 h-4" />
                            </button>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1 capitalize">{(e.type || '').replace(/_/g, ' ')} • {e.date_debut}{e.lieu ? ` • ${e.lieu}` : ''}</p>
                        <div className="mt-3 flex items-center justify-between">
                            <span className="text-sm text-muted-foreground">{e.nb_depenses} dépense(s)</span>
                            <span className="font-bold text-primary">{eur(e.cout)}</span>
                        </div>
                    </div>
                ))}
                {!evenements?.length && (
                    <div className="col-span-full py-16 text-center bg-card rounded-2xl border border-dashed border-border">
                        <CalendarDays className="w-14 h-14 text-muted-foreground mx-auto mb-3 opacity-20" />
                        <p className="text-muted-foreground italic">Aucun événement.</p>
                    </div>
                )}
            </div>

            <Modal isOpen={createOpen} onClose={() => setCreateOpen(false)} title="Nouvel événement">
                <div className="space-y-4">
                    <Input label="Titre" value={form.titre} onChange={e => setForm({ ...form, titre: e.target.value })} />
                    <div className="grid grid-cols-2 gap-4">
                        <Select label="Type" options={TYPES_EVT} value={form.type} onChange={e => setForm({ ...form, type: e.target.value })} />
                        <Input label="Lieu" value={form.lieu} onChange={e => setForm({ ...form, lieu: e.target.value })} />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <Input label="Date de début" type="date" value={form.date_debut} onChange={e => setForm({ ...form, date_debut: e.target.value })} />
                        <Input label="Date de fin" type="date" value={form.date_fin} onChange={e => setForm({ ...form, date_fin: e.target.value })} />
                    </div>
                    <Input label="Description" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
                    <div className="pt-2 flex justify-end gap-2">
                        <Button variant="outline" onClick={() => setCreateOpen(false)}>Annuler</Button>
                        <Button onClick={() => createMutation.mutate({ ...form, date_fin: form.date_fin || null })} isLoading={createMutation.isPending}>Créer</Button>
                    </div>
                </div>
            </Modal>

            {detailId && <EvenementDetail id={detailId} onClose={() => setDetailId(null)} onChange={invalidate} />}
        </div>
    );
}

function EvenementDetail({ id, onClose, onChange }) {
    const queryClient = useQueryClient();
    const [depId, setDepId] = useState('');
    const [quotePart, setQuotePart] = useState('');

    const { data: detail } = useQuery({
        queryKey: ['evenement', id],
        queryFn: async () => (await axios.get(`${API_URL}/evenements/${id}`)).data,
    });
    const { data: depenses } = useQuery({
        queryKey: ['depenses'],
        queryFn: async () => (await axios.get(`${API_URL}/depenses`)).data,
    });

    const refresh = () => { queryClient.invalidateQueries(['evenement', id]); onChange(); };

    const linkMutation = useMutation({
        mutationFn: async () => axios.post(`${API_URL}/evenements/${id}/depenses`, { depense_id: Number(depId), quote_part: quotePart === '' ? null : Number(quotePart) }),
        onSuccess: () => { refresh(); setDepId(''); setQuotePart(''); },
        onError: (err) => alert(err.response?.data?.detail || 'Erreur'),
    });
    const unlinkMutation = useMutation({
        mutationFn: async (dId) => axios.delete(`${API_URL}/evenements/${id}/depenses/${dId}`),
        onSuccess: refresh,
    });

    return (
        <Modal isOpen={true} onClose={onClose} title={detail?.titre || 'Événement'}>
            <div className="space-y-4">
                <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{detail?.date_debut} {detail?.lieu && `• ${detail.lieu}`}</span>
                    <span className="font-bold text-primary">Coût : {eur(detail?.cout)}</span>
                </div>

                <div className="space-y-2">
                    <h4 className="text-sm font-semibold">Dépenses rattachées</h4>
                    {detail?.depenses?.length ? detail.depenses.map(d => (
                        <div key={d.depense_id} className="flex items-center justify-between bg-muted/40 rounded-md px-3 py-2 text-sm">
                            <span className="truncate flex-1">{d.libelle} <span className="text-muted-foreground">({d.fournisseur})</span></span>
                            <span className="mx-2 text-xs font-mono">{d.quote_part != null ? `${d.quote_part}%` : '100%'} → {eur(d.cout_affecte)}</span>
                            <button onClick={() => unlinkMutation.mutate(d.depense_id)} className="text-muted-foreground hover:text-red-600"><X className="w-4 h-4" /></button>
                        </div>
                    )) : <p className="text-sm text-muted-foreground italic">Aucune dépense rattachée.</p>}
                </div>

                <div className="border-t border-border pt-4 space-y-2">
                    <h4 className="text-sm font-semibold flex items-center gap-1"><Link2 className="w-4 h-4" /> Rattacher une dépense</h4>
                    <div className="flex gap-2 items-end">
                        <div className="flex-1">
                            <Select label="Dépense" value={depId} onChange={e => setDepId(e.target.value)}
                                options={[{ value: '', label: '— choisir —' }, ...(depenses || []).map(d => ({ value: String(d.id), label: `${d.libelle} (${eur(d.montant_ttc)})` }))]} />
                        </div>
                        <div className="w-28">
                            <Input label="Quote-part %" type="number" placeholder="100" value={quotePart} onChange={e => setQuotePart(e.target.value)} />
                        </div>
                        <Button onClick={() => depId && linkMutation.mutate()} isLoading={linkMutation.isPending}>Lier</Button>
                    </div>
                </div>
            </div>
        </Modal>
    );
}
