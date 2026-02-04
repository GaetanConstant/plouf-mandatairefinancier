import React from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { FileText } from 'lucide-react';

const API_URL = 'http://localhost:8000';

export function DepensesList() {
    const { data: depenses, isLoading } = useQuery({
        queryKey: ['depenses'],
        queryFn: async () => {
            const response = await axios.get(`${API_URL}/depenses`);
            return response.data;
        }
    });

    if (isLoading) return <div>Chargement des dépenses...</div>;

    return (
        <div className="space-y-4 animate-in fade-in duration-500">
            <h2 className="text-2xl font-bold tracking-tight">Dépenses</h2>
            <div className="rounded-md border border-border bg-card">
                <div className="relative w-full overflow-auto">
                    <table className="w-full caption-bottom text-sm">
                        <thead className="[&_tr]:border-b">
                            <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Date</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Libellé</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Fournisseur</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Catégorie</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Statut</th>
                                <th className="h-12 px-4 text-right align-middle font-medium text-muted-foreground">Montant TTC</th>
                                <th className="h-12 px-4 text-center align-middle font-medium text-muted-foreground">Justificatif</th>
                            </tr>
                        </thead>
                        <tbody className="[&_tr:last-child]:border-0">
                            {depenses?.map((depense, i) => (
                                <tr key={i} className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                                    <td className="p-4 align-middle">{depense.date}</td>
                                    <td className="p-4 align-middle font-medium">
                                        {depense.libelle}
                                        {depense.is_nature && (
                                            <span className="ml-2 inline-flex items-center rounded-full bg-purple-100 px-2 py-0.5 text-[10px] font-bold text-purple-700 border border-purple-200">
                                                NATURE
                                            </span>
                                        )}
                                    </td>
                                    <td className="p-4 align-middle">{depense.fournisseur}</td>
                                    <td className="p-4 align-middle"><span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80">{depense.categorie_cnccfp}</span></td>
                                    <td className="p-4 align-middle">{depense.statut}</td>
                                    <td className="p-4 align-middle text-right">{depense.montant_ttc.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}</td>
                                    <td className="p-4 align-middle text-center">
                                        {depense.justificatif_path ? (
                                            <a
                                                href={`${API_URL}/docs/${depense.justificatif_path.split('/').pop()}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-primary hover:text-primary/80 flex justify-center transition-colors"
                                            >
                                                <FileText className="w-5 h-5" />
                                            </a>
                                        ) : (
                                            <span className="text-muted-foreground text-xs">-</span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
