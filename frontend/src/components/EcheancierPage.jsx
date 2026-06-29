import React from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Flag, Download, CheckCircle2, Clock, AlertCircle } from 'lucide-react';
import { Button } from './ui/Components';
import { cn } from '../lib/utils';

const API_URL = 'http://localhost:8000';

const STATUT = {
    passe: { label: 'Passé', icon: CheckCircle2, cls: 'text-muted-foreground', badge: 'bg-muted text-muted-foreground' },
    aujourdhui: { label: "Aujourd'hui", icon: AlertCircle, cls: 'text-orange-600', badge: 'bg-orange-500/10 text-orange-600 border border-orange-500/20' },
    a_venir: { label: 'À venir', icon: Clock, cls: 'text-blue-600', badge: 'bg-blue-500/10 text-blue-600 border border-blue-500/20' },
    indetermine: { label: '—', icon: Clock, cls: 'text-muted-foreground', badge: 'bg-muted text-muted-foreground' },
};

export function EcheancierPage() {
    const { data: echeances, isLoading } = useQuery({
        queryKey: ['echeancier'],
        queryFn: async () => (await axios.get(`${API_URL}/echeancier`)).data,
    });

    if (isLoading) return <div>Chargement de l'échéancier...</div>;

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Échéancier & Rapport</h1>
                    <p className="text-muted-foreground">Échéances légales calculées depuis la date du 1er tour (renseignée dans l'Identité).</p>
                </div>
                <a href={`${API_URL}/rapport`} target="_blank" rel="noopener noreferrer">
                    <Button className="gap-2"><Download className="w-4 h-4" /> Rapport de campagne (PDF)</Button>
                </a>
            </header>

            {!echeances?.length ? (
                <div className="py-16 text-center bg-card rounded-2xl border border-dashed border-border">
                    <Flag className="w-14 h-14 text-muted-foreground mx-auto mb-3 opacity-20" />
                    <p className="text-muted-foreground italic">Renseignez la date du 1er tour dans la page « Identité » pour calculer les échéances.</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {echeances.map((e, i) => {
                        const S = STATUT[e.statut] || STATUT.indetermine;
                        const Icon = S.icon;
                        return (
                            <div key={i} className="bg-card rounded-xl border border-border p-4 flex items-center gap-4">
                                <Icon className={cn("w-6 h-6 shrink-0", S.cls)} />
                                <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                        <h3 className="font-semibold">{e.libelle}</h3>
                                        <span className={cn("text-[10px] font-bold uppercase rounded-full px-2 py-0.5", S.badge)}>{S.label}</span>
                                    </div>
                                    <p className="text-xs text-muted-foreground">{e.regle}</p>
                                </div>
                                <span className="font-mono text-sm">{e.date}</span>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
