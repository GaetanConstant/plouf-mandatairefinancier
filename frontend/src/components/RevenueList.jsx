import React from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

export function RevenueList() {
    const { data: recettes, isLoading } = useQuery({
        queryKey: ['recettes'],
        queryFn: async () => {
            const response = await axios.get(`${API_URL}/recettes`);
            return response.data;
        }
    });

    if (isLoading) return <div>Chargement des recettes...</div>;

    return (
        <div className="space-y-4 animate-in fade-in duration-500">
            <h2 className="text-2xl font-bold tracking-tight">Recettes & Dons</h2>
            <div className="rounded-md border border-border bg-card">
                <div className="relative w-full overflow-auto">
                    <table className="w-full caption-bottom text-sm">
                        <thead className="[&_tr]:border-b">
                            <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Date</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Donateur</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Type</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Recu fiscal</th>
                                <th className="h-12 px-4 text-right align-middle font-medium text-muted-foreground">Montant</th>
                            </tr>
                        </thead>
                        <tbody className="[&_tr:last-child]:border-0">
                            {recettes?.map((recette, i) => (
                                <tr key={i} className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                                    <td className="p-4 align-middle">{recette.date}</td>
                                    <td className="p-4 align-middle font-medium">{recette.nom_donateur}</td>
                                    <td className="p-4 align-middle">{recette.type}</td>
                                    <td className="p-4 align-middle">
                                        {recette.recu_genere ? (
                                            <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-green-500/10 text-green-500 hover:bg-green-500/20">Oui</span>
                                        ) : (
                                            <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-yellow-500/10 text-yellow-500 hover:bg-yellow-500/20">Non</span>
                                        )}
                                    </td>
                                    <td className="p-4 align-middle text-right text-green-600 font-medium">+ {recette.montant.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
