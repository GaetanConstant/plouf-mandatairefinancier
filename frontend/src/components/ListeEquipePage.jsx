import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Users, UserPlus, Trash2, Plus } from 'lucide-react';
import { Button, Input } from './ui/Components';
import { API_URL } from '../lib/api';


export function ListeEquipePage() {
    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <header>
                <h1 className="text-3xl font-bold tracking-tight">Liste & équipe</h1>
                <p className="text-muted-foreground">Colistiers (liste alphabétique pour le dépôt) et équipe de campagne (annexe 7).</p>
            </header>
            <Colistiers />
            <Equipe />
        </div>
    );
}

function Colistiers() {
    const qc = useQueryClient();
    const [f, setF] = useState({ civilite: 'M.', prenom: '', nom: '', mandat_parlementaire: '', present_tour1: true, present_tour2: false });
    const { data } = useQuery({ queryKey: ['colistiers'], queryFn: async () => (await axios.get(`${API_URL}/colistiers`)).data });
    const add = useMutation({ mutationFn: (p) => axios.post(`${API_URL}/colistiers`, p), onSuccess: () => { qc.invalidateQueries(['colistiers']); setF({ ...f, prenom: '', nom: '', mandat_parlementaire: '' }); } });
    const del = useMutation({ mutationFn: (id) => axios.delete(`${API_URL}/colistiers/${id}`), onSuccess: () => qc.invalidateQueries(['colistiers']) });

    return (
        <section className="bg-card rounded-xl border border-border p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4"><Users className="w-5 h-5 text-primary" /><h2 className="font-bold text-lg">Colistiers</h2></div>
            <div className="w-full overflow-x-auto"><table className="w-full text-sm mb-4">
                <thead><tr className="border-b text-muted-foreground text-left">
                    <th className="py-2 px-2 font-medium">Civ.</th><th className="py-2 px-2 font-medium">Prénom</th><th className="py-2 px-2 font-medium">Nom</th>
                    <th className="py-2 px-2 font-medium">Mandat parl.</th><th className="py-2 px-2 font-medium text-center">T1</th><th className="py-2 px-2 font-medium text-center">T2</th><th></th>
                </tr></thead>
                <tbody>
                    {data?.map(c => (
                        <tr key={c.id} className="border-b hover:bg-muted/40">
                            <td className="py-2 px-2">{c.civilite}</td><td className="py-2 px-2">{c.prenom}</td><td className="py-2 px-2 font-medium">{c.nom}</td>
                            <td className="py-2 px-2 text-muted-foreground">{c.mandat_parlementaire || '—'}</td>
                            <td className="py-2 px-2 text-center">{c.present_tour1 ? '✓' : ''}</td><td className="py-2 px-2 text-center">{c.present_tour2 ? '✓' : ''}</td>
                            <td className="py-2 px-2 text-right"><button onClick={() => del.mutate(c.id)} className="text-muted-foreground hover:text-red-600"><Trash2 className="w-4 h-4" /></button></td>
                        </tr>
                    ))}
                    {!data?.length && <tr><td colSpan={7} className="py-4 text-center text-muted-foreground italic">Aucun colistier.</td></tr>}
                </tbody>
            </table></div>
            <div className="flex flex-wrap gap-2 items-end border-t border-border pt-4">
                <div className="w-20"><Input label="Civ." value={f.civilite} onChange={e => setF({ ...f, civilite: e.target.value })} /></div>
                <div className="flex-1 min-w-[120px]"><Input label="Prénom" value={f.prenom} onChange={e => setF({ ...f, prenom: e.target.value })} /></div>
                <div className="flex-1 min-w-[120px]"><Input label="Nom" value={f.nom} onChange={e => setF({ ...f, nom: e.target.value })} /></div>
                <div className="flex-1 min-w-[120px]"><Input label="Mandat parl." value={f.mandat_parlementaire} onChange={e => setF({ ...f, mandat_parlementaire: e.target.value })} /></div>
                <label className="flex items-center gap-1 text-sm pb-2"><input type="checkbox" checked={f.present_tour1} onChange={e => setF({ ...f, present_tour1: e.target.checked })} /> T1</label>
                <label className="flex items-center gap-1 text-sm pb-2"><input type="checkbox" checked={f.present_tour2} onChange={e => setF({ ...f, present_tour2: e.target.checked })} /> T2</label>
                <Button onClick={() => f.nom && add.mutate(f)} className="gap-1"><Plus className="w-4 h-4" /> Ajouter</Button>
            </div>
        </section>
    );
}

function Equipe() {
    const qc = useQueryClient();
    const [f, setF] = useState({ prenom: '', nom: '', fonction: '' });
    const { data } = useQuery({ queryKey: ['equipe'], queryFn: async () => (await axios.get(`${API_URL}/equipe`)).data });
    const add = useMutation({ mutationFn: (p) => axios.post(`${API_URL}/equipe`, p), onSuccess: () => { qc.invalidateQueries(['equipe']); setF({ prenom: '', nom: '', fonction: '' }); } });
    const del = useMutation({ mutationFn: (id) => axios.delete(`${API_URL}/equipe/${id}`), onSuccess: () => qc.invalidateQueries(['equipe']) });

    return (
        <section className="bg-card rounded-xl border border-border p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4"><UserPlus className="w-5 h-5 text-primary" /><h2 className="font-bold text-lg">Équipe de campagne (annexe 7)</h2></div>
            <div className="w-full overflow-x-auto"><table className="w-full text-sm mb-4">
                <thead><tr className="border-b text-muted-foreground text-left">
                    <th className="py-2 px-2 font-medium">Prénom</th><th className="py-2 px-2 font-medium">Nom</th><th className="py-2 px-2 font-medium">Fonction</th><th></th>
                </tr></thead>
                <tbody>
                    {data?.map(m => (
                        <tr key={m.id} className="border-b hover:bg-muted/40">
                            <td className="py-2 px-2">{m.prenom}</td><td className="py-2 px-2 font-medium">{m.nom}</td><td className="py-2 px-2">{m.fonction}</td>
                            <td className="py-2 px-2 text-right"><button onClick={() => del.mutate(m.id)} className="text-muted-foreground hover:text-red-600"><Trash2 className="w-4 h-4" /></button></td>
                        </tr>
                    ))}
                    {!data?.length && <tr><td colSpan={4} className="py-4 text-center text-muted-foreground italic">Aucun membre.</td></tr>}
                </tbody>
            </table></div>
            <div className="flex flex-wrap gap-2 items-end border-t border-border pt-4">
                <div className="flex-1 min-w-[120px]"><Input label="Prénom" value={f.prenom} onChange={e => setF({ ...f, prenom: e.target.value })} /></div>
                <div className="flex-1 min-w-[120px]"><Input label="Nom" value={f.nom} onChange={e => setF({ ...f, nom: e.target.value })} /></div>
                <div className="flex-[2] min-w-[160px]"><Input label="Fonction" value={f.fonction} onChange={e => setF({ ...f, fonction: e.target.value })} /></div>
                <Button onClick={() => f.nom && add.mutate(f)} className="gap-1"><Plus className="w-4 h-4" /> Ajouter</Button>
            </div>
        </section>
    );
}
