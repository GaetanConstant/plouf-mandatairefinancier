import React from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Download, BookText } from 'lucide-react';
import { Button } from './ui/Components';
import { cn } from '../lib/utils';
import { API_URL } from '../lib/api';


export function MainCourantePage() {
    const { data: lignes, isLoading } = useQuery({
        queryKey: ['main-courante'],
        queryFn: async () => (await axios.get(`${API_URL}/main-courante`)).data,
    });

    if (isLoading) return <div>Chargement de la main courante...</div>;

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <header className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Main courante</h1>
                    <p className="text-muted-foreground">Journal chronologique des recettes et dépenses (annexe 8).</p>
                </div>
                <div className="flex gap-2">
                    <a href={`${API_URL}/livre-comptes/export`} target="_blank" rel="noopener noreferrer">
                        <Button variant="outline" className="gap-2"><Download className="w-4 h-4" /> Livre de comptes (Excel)</Button>
                    </a>
                    <a href={`${API_URL}/main-courante/export`} target="_blank" rel="noopener noreferrer">
                        <Button className="gap-2"><Download className="w-4 h-4" /> Export annexe 8 (Excel)</Button>
                    </a>
                </div>
            </header>

            <div className="rounded-md border border-border bg-card overflow-auto">
                <table className="w-full caption-bottom text-sm">
                    <thead className="[&_tr]:border-b">
                        <tr className="border-b">
                            <th className="h-11 px-3 text-left font-medium text-muted-foreground">Sens</th>
                            <th className="h-11 px-3 text-left font-medium text-muted-foreground">Date facture</th>
                                <th className="h-11 px-3 text-left font-medium text-muted-foreground">Date paiement</th>
                            <th className="h-11 px-3 text-left font-medium text-muted-foreground">N° pièce</th>
                            <th className="h-11 px-3 text-left font-medium text-muted-foreground">Rubrique</th>
                            <th className="h-11 px-3 text-left font-medium text-muted-foreground">Nature</th>
                                <th className="h-11 px-3 text-left font-medium text-muted-foreground">Libellé relevé</th>
                            <th className="h-11 px-3 text-left font-medium text-muted-foreground">Tiers</th>
                            <th className="h-11 px-3 text-left font-medium text-muted-foreground">Mode</th>
                            <th className="h-11 px-3 text-left font-medium text-muted-foreground">N° relevé</th>
                            <th className="h-11 px-3 text-center font-medium text-muted-foreground">Rappr.</th>
                            <th className="h-11 px-3 text-right font-medium text-muted-foreground">Montant</th>
                            <th className="h-11 px-3 text-right font-medium text-muted-foreground">Solde</th>
                        </tr>
                    </thead>
                    <tbody className="[&_tr:last-child]:border-0">
                        {lignes?.map((l, i) => (
                            <tr key={i} className="border-b hover:bg-muted/40">
                                <td className="p-3">
                                    <span className={cn(
                                        "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase",
                                        l.sens === 'recette'
                                            ? "bg-green-500/10 text-green-600 border-green-500/20"
                                            : "bg-orange-500/10 text-orange-600 border-orange-500/20"
                                    )}>
                                        {l.sens === 'recette' ? 'Recette' : 'Dépense'}
                                    </span>
                                </td>
                                <td className="p-3 whitespace-nowrap">{l.date_facture || l.date}</td>
                                    {/* Vide tant que la dépense n'est pas rapprochée : on voit
                                        d'un coup d'œil ce qui reste à régler. */}
                                    <td className="p-3 whitespace-nowrap text-muted-foreground">{l.date_paiement || '—'}</td>
                                <td className="p-3 text-muted-foreground">{l.num_piece || '—'}</td>
                                <td className="p-3 font-mono text-xs">{l.rubrique || '—'}</td>
                                <td className="p-3 font-medium">{l.nature}</td>
                                    <td className="p-3 text-xs text-muted-foreground">{l.libelle_releve || '—'}</td>
                                <td className="p-3">{l.tiers || '—'}</td>
                                <td className="p-3 text-muted-foreground">{l.mode || '—'}</td>
                                <td className="p-3 text-muted-foreground">{l.num_releve || '—'}</td>
                                <td className="p-3 text-center">{l.rapprochement ? <span className="text-green-600">✓</span> : <span className="text-muted-foreground">—</span>}</td>
                                <td className={cn("p-3 text-right font-medium", l.sens === 'recette' ? "text-green-600" : "text-orange-600")}>
                                    {l.sens === 'recette' ? '+ ' : '- '}
                                    {l.montant?.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                                </td>
                                <td className={cn("p-3 text-right font-mono text-xs", l.solde < 0 ? "text-red-600" : "text-foreground")}>
                                    {l.solde?.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                                </td>
                            </tr>
                        ))}
                        {!lignes?.length && (
                            <tr><td colSpan={11} className="p-10 text-center text-muted-foreground italic">
                                <BookText className="w-12 h-12 mx-auto mb-2 opacity-20" />
                                Aucune écriture pour l'instant.
                            </td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
