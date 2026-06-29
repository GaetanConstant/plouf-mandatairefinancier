import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Download, ShieldCheck, ShieldAlert, FileText } from 'lucide-react';
import { Button } from './ui/Components';
import { cn } from '../lib/utils';

const API_URL = 'http://localhost:8000';

const ENVELOPPES = [
    { value: '', label: 'Non classé' },
    { value: 'A', label: 'Enveloppe A' },
    { value: 'B', label: 'Enveloppe B' },
    { value: 'hors_depot', label: 'Hors dépôt' },
];

export function DepotPage() {
    const queryClient = useQueryClient();

    const { data: etat, isLoading } = useQuery({
        queryKey: ['depot'],
        queryFn: async () => (await axios.get(`${API_URL}/depot`)).data,
        refetchInterval: 8000,
    });
    const { data: documents } = useQuery({
        queryKey: ['documents'],
        queryFn: async () => (await axios.get(`${API_URL}/documents`)).data,
    });

    const updateMutation = useMutation({
        mutationFn: async ({ id, enveloppe }) => axios.put(`${API_URL}/documents/${id}`, { enveloppe: enveloppe || null }),
        onSuccess: () => {
            queryClient.invalidateQueries(['documents']);
            queryClient.invalidateQueries(['depot']);
        },
    });

    if (isLoading) return <div>Chargement du dossier de dépôt...</div>;

    const pret = etat?.pret_a_deposer;

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Dépôt du dossier</h1>
                    <p className="text-muted-foreground">Classement des pièces par enveloppe (A / B) et bordereau de dépôt.</p>
                </div>
                <a href={`${API_URL}/depot/export`} target="_blank" rel="noopener noreferrer">
                    <Button className="gap-2"><Download className="w-4 h-4" /> Bordereau de dépôt (PDF)</Button>
                </a>
            </header>

            <div className={cn("rounded-2xl border p-6 flex items-center gap-4",
                pret ? "border-green-200 bg-green-50/10" : "border-red-200 bg-red-50/10")}>
                {pret ? <ShieldCheck className="w-10 h-10 text-green-600" /> : <ShieldAlert className="w-10 h-10 text-red-600" />}
                <div>
                    <h2 className="text-xl font-bold">{pret ? "Prêt à déposer" : "Points bloquants à corriger"}</h2>
                    <p className="text-sm text-muted-foreground">
                        Enveloppe A : {etat?.pieces_A?.length || 0} pièces · Enveloppe B : {etat?.pieces_B?.length || 0} · Non classées : {etat?.pieces_non_classees?.length || 0}
                    </p>
                </div>
            </div>

            {etat?.alertes_bloquantes?.length > 0 && (
                <div className="rounded-md border border-red-200 bg-red-50/5 p-4 space-y-1">
                    <h3 className="font-semibold text-red-600 text-sm mb-2">Points bloquants</h3>
                    {etat.alertes_bloquantes.map((a, i) => (
                        <p key={i} className="text-sm text-foreground">• {a.message}</p>
                    ))}
                </div>
            )}

            <div className="rounded-md border border-border bg-card">
                <table className="w-full caption-bottom text-sm">
                    <thead className="[&_tr]:border-b">
                        <tr className="border-b">
                            <th className="h-11 px-4 text-left font-medium text-muted-foreground">Type</th>
                            <th className="h-11 px-4 text-left font-medium text-muted-foreground">Fichier</th>
                            <th className="h-11 px-4 text-left font-medium text-muted-foreground">Ajouté le</th>
                            <th className="h-11 px-4 text-left font-medium text-muted-foreground">Enveloppe</th>
                        </tr>
                    </thead>
                    <tbody className="[&_tr:last-child]:border-0">
                        {documents?.map((d) => (
                            <tr key={d.id} className="border-b hover:bg-muted/40">
                                <td className="p-4">{d.type_label}</td>
                                <td className="p-4 flex items-center gap-2"><FileText className="w-4 h-4 text-muted-foreground shrink-0" /><span className="truncate max-w-[360px]">{d.fichier}</span></td>
                                <td className="p-4 text-muted-foreground">{d.date_ajout}</td>
                                <td className="p-4">
                                    <select
                                        className="bg-card border border-border rounded-md px-2 py-1 text-sm"
                                        value={d.enveloppe || ''}
                                        onChange={(e) => updateMutation.mutate({ id: d.id, enveloppe: e.target.value })}
                                    >
                                        {ENVELOPPES.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                                    </select>
                                </td>
                            </tr>
                        ))}
                        {!documents?.length && (
                            <tr><td colSpan={4} className="p-8 text-center text-muted-foreground italic">Aucune pièce. Les justificatifs ajoutés aux dépenses apparaîtront ici.</td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
