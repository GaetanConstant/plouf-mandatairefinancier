import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { CalendarDays, TrendingUp, Receipt, Flag } from 'lucide-react';
import { cn } from '../lib/utils';
import { API_URL } from '../lib/api';


const TYPE_CONF = {
    evenement: { label: 'Événements', icon: CalendarDays, dot: 'bg-primary', text: 'text-primary' },
    recette: { label: 'Recettes', icon: TrendingUp, dot: 'bg-green-500', text: 'text-green-600' },
    depense: { label: 'Dépenses', icon: Receipt, dot: 'bg-orange-500', text: 'text-orange-600' },
    echeance: { label: 'Échéances', icon: Flag, dot: 'bg-blue-500', text: 'text-blue-600' },
};

const eur = (v) => v == null ? '' : (v || 0).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });

export function FrisePage() {
    const [filters, setFilters] = useState({ evenement: true, recette: true, depense: true, echeance: true });

    const { data: items, isLoading } = useQuery({
        queryKey: ['frise'],
        queryFn: async () => (await axios.get(`${API_URL}/frise`)).data,
    });

    if (isLoading) return <div>Chargement de la frise...</div>;

    const visible = (items || []).filter(i => filters[i.type]);

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <header>
                <h1 className="text-3xl font-bold tracking-tight">Frise chronologique</h1>
                <p className="text-muted-foreground">Journal de bord visuel : événements, recettes, dépenses et échéances sur un même axe.</p>
            </header>

            <div className="flex flex-wrap gap-2">
                {Object.entries(TYPE_CONF).map(([key, conf]) => (
                    <button key={key} onClick={() => setFilters({ ...filters, [key]: !filters[key] })}
                        className={cn("flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-medium transition-colors",
                            filters[key] ? "border-border bg-card" : "border-dashed border-border bg-transparent opacity-50")}>
                        <span className={cn("w-2.5 h-2.5 rounded-full", conf.dot)} />
                        {conf.label}
                    </button>
                ))}
            </div>

            <div className="relative pl-6 border-l-2 border-border space-y-4">
                {visible.map((it, i) => {
                    const conf = TYPE_CONF[it.type];
                    const Icon = conf.icon;
                    return (
                        <div key={i} className="relative">
                            <span className={cn("absolute -left-[1.95rem] top-1.5 w-3.5 h-3.5 rounded-full ring-4 ring-background", conf.dot)} />
                            <div className="bg-card rounded-lg border border-border p-3 flex items-center gap-3">
                                <Icon className={cn("w-4 h-4 shrink-0", conf.text)} />
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-muted-foreground font-mono">{it.date || '—'}</span>
                                        <span className="font-medium truncate">{it.titre}</span>
                                    </div>
                                    {it.sous_titre && <p className="text-xs text-muted-foreground truncate">{it.sous_titre}</p>}
                                </div>
                                {it.montant != null && <span className={cn("font-semibold text-sm shrink-0", conf.text)}>{eur(it.montant)}</span>}
                            </div>
                        </div>
                    );
                })}
                {!visible.length && <p className="text-muted-foreground italic">Aucun élément à afficher.</p>}
            </div>
        </div>
    );
}
