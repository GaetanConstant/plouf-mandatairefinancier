import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Users, Plus, Trash2, FileDown, FileSpreadsheet, X } from 'lucide-react';
import { Modal, Button, Input, Select } from './ui/Components';
import { cn } from '../lib/utils';
import { API_URL } from '../lib/api';

const eur = (v) => (v || 0).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });

export function MutualisationPage() {
    const queryClient = useQueryClient();
    const [partyOpen, setPartyOpen] = useState(false);
    const [mutOpen, setMutOpen] = useState(false);
    const [party, setParty] = useState({ nom: '', prenom_ou_liste: '', scrutin: '' });
    const [mut, setMut] = useState({ objet: '', montant_total_ttc: '', cle_justification: '' });
    const [reps, setReps] = useState([{ partie: 'notre_campagne', pourcentage: '' }]);

    const { data: parties } = useQuery({ queryKey: ['parties'], queryFn: async () => (await axios.get(`${API_URL}/parties-externes`)).data });
    const { data: muts, isLoading } = useQuery({ queryKey: ['mutualisations'], queryFn: async () => (await axios.get(`${API_URL}/mutualisations`)).data });

    const inval = () => { queryClient.invalidateQueries(['mutualisations']); queryClient.invalidateQueries(['parties']); };

    const createParty = useMutation({ mutationFn: (p) => axios.post(`${API_URL}/parties-externes`, p), onSuccess: () => { inval(); setPartyOpen(false); setParty({ nom: '', prenom_ou_liste: '', scrutin: '' }); } });
    const createMut = useMutation({
        mutationFn: (p) => axios.post(`${API_URL}/mutualisations`, p),
        onSuccess: () => { inval(); setMutOpen(false); setMut({ objet: '', montant_total_ttc: '', cle_justification: '' }); setReps([{ partie: 'notre_campagne', pourcentage: '' }]); },
        onError: (err) => alert(err.response?.data?.detail || 'Erreur'),
    });
    const delMut = useMutation({ mutationFn: (id) => axios.delete(`${API_URL}/mutualisations/${id}`), onSuccess: inval });

    const sumPct = reps.reduce((a, r) => a + Number(r.pourcentage || 0), 0);

    const submitMut = () => {
        const repartitions = reps.map(r => {
            const isExt = r.partie.startsWith('ext:');
            return { partie: isExt ? 'partie_externe' : 'notre_campagne', partie_id: isExt ? Number(r.partie.slice(4)) : null, pourcentage: Number(r.pourcentage || 0) };
        });
        createMut.mutate({ objet: mut.objet, montant_total_ttc: Number(mut.montant_total_ttc || 0), cle_justification: mut.cle_justification, porteur: 'notre_campagne', repartitions });
    };

    if (isLoading) return <div>Chargement...</div>;

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <header className="flex items-center justify-between flex-wrap gap-3">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Dépenses mutualisées</h1>
                    <p className="text-muted-foreground">Conventions de partage avec d'autres candidats — seule votre quote-part compte dans votre compte.</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={() => setPartyOpen(true)} className="gap-2"><Users className="w-4 h-4" /> Partie externe</Button>
                    <a href={`${API_URL}/mutualisations/export`} target="_blank" rel="noopener noreferrer">
                        <Button variant="outline" className="gap-2"><FileSpreadsheet className="w-4 h-4" /> État (Excel)</Button>
                    </a>
                    <Button onClick={() => setMutOpen(true)} className="gap-2"><Plus className="w-4 h-4" /> Nouvelle mutualisation</Button>
                </div>
            </header>

            <div className="space-y-4">
                {muts?.map((m) => (
                    <div key={m.id} className="bg-card rounded-xl border border-border p-5 shadow-sm">
                        <div className="flex items-start justify-between">
                            <div>
                                <h3 className="font-bold">{m.objet}</h3>
                                <p className="text-xs text-muted-foreground">Total {eur(m.montant_total_ttc)} • Notre quote-part : <span className="font-semibold text-primary">{eur(m.notre_quote_part)}</span></p>
                            </div>
                            <div className="flex items-center gap-2">
                                <a href={`${API_URL}/mutualisations/${m.id}/convention`} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary" title="Convention PDF"><FileDown className="w-4 h-4" /></a>
                                <button onClick={() => delMut.mutate(m.id)} className="text-muted-foreground hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                            </div>
                        </div>
                        {m.cle_justification && <p className="text-xs text-muted-foreground italic mt-2">Clé : {m.cle_justification}</p>}
                        <div className="mt-3 flex flex-wrap gap-2">
                            {m.repartitions.map((r) => (
                                <span key={r.id} className="text-xs bg-muted/50 rounded-full px-3 py-1 border border-border">
                                    {r.nom} : {r.pourcentage}% → {eur(r.montant)} <span className="text-muted-foreground">({r.statut_reglement})</span>
                                </span>
                            ))}
                        </div>
                    </div>
                ))}
                {!muts?.length && (
                    <div className="py-16 text-center bg-card rounded-2xl border border-dashed border-border">
                        <Users className="w-14 h-14 text-muted-foreground mx-auto mb-3 opacity-20" />
                        <p className="text-muted-foreground italic">Aucune dépense mutualisée.</p>
                    </div>
                )}
            </div>

            {/* Modal partie externe */}
            <Modal isOpen={partyOpen} onClose={() => setPartyOpen(false)} title="Nouvelle partie externe">
                <div className="space-y-4">
                    <Input label="Nom" value={party.nom} onChange={e => setParty({ ...party, nom: e.target.value })} />
                    <Input label="Prénom / Liste" value={party.prenom_ou_liste} onChange={e => setParty({ ...party, prenom_ou_liste: e.target.value })} />
                    <Input label="Scrutin" value={party.scrutin} onChange={e => setParty({ ...party, scrutin: e.target.value })} />
                    <div className="flex justify-end gap-2 pt-2">
                        <Button variant="outline" onClick={() => setPartyOpen(false)}>Annuler</Button>
                        <Button onClick={() => party.nom && createParty.mutate(party)} isLoading={createParty.isPending}>Créer</Button>
                    </div>
                </div>
            </Modal>

            {/* Modal mutualisation */}
            <Modal isOpen={mutOpen} onClose={() => setMutOpen(false)} title="Nouvelle dépense mutualisée">
                <div className="space-y-4">
                    <Input label="Objet" value={mut.objet} onChange={e => setMut({ ...mut, objet: e.target.value })} />
                    <Input label="Montant total TTC (€)" type="number" value={mut.montant_total_ttc} onChange={e => setMut({ ...mut, montant_total_ttc: e.target.value })} />
                    <Input label="Clé de répartition (justification)" value={mut.cle_justification} onChange={e => setMut({ ...mut, cle_justification: e.target.value })} />

                    <div className="space-y-2">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <label className="text-sm font-semibold">Répartition</label>
                            <span className={cn("text-xs font-mono", Math.abs(sumPct - 100) < 0.01 ? "text-green-600" : "text-orange-600")}>Σ = {sumPct}%</span>
                        </div>
                        {reps.map((r, i) => (
                            <div key={i} className="flex gap-2 items-center">
                                <select className="flex-1 bg-card border border-border rounded-md px-2 py-2 text-sm"
                                    value={r.partie} onChange={e => setReps(reps.map((x, j) => j === i ? { ...x, partie: e.target.value } : x))}>
                                    <option value="notre_campagne">Notre campagne</option>
                                    {parties?.map(p => <option key={p.id} value={`ext:${p.id}`}>{p.nom} {p.prenom_ou_liste || ''}</option>)}
                                </select>
                                <input type="number" placeholder="%" className="w-20 bg-card border border-border rounded-md px-2 py-2 text-sm"
                                    value={r.pourcentage} onChange={e => setReps(reps.map((x, j) => j === i ? { ...x, pourcentage: e.target.value } : x))} />
                                {reps.length > 1 && <button onClick={() => setReps(reps.filter((_, j) => j !== i))} className="text-muted-foreground hover:text-red-600"><X className="w-4 h-4" /></button>}
                            </div>
                        ))}
                        <button onClick={() => setReps([...reps, { partie: 'notre_campagne', pourcentage: '' }])} className="text-xs text-primary font-medium">+ Ajouter une partie</button>
                    </div>

                    <div className="flex justify-end gap-2 pt-2">
                        <Button variant="outline" onClick={() => setMutOpen(false)}>Annuler</Button>
                        <Button onClick={submitMut} isLoading={createMut.isPending} disabled={Math.abs(sumPct - 100) > 0.01}>Créer</Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}
