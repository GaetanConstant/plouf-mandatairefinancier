import React from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { ShieldCheck, ShieldAlert, AlertTriangle, Info, CheckCircle2 } from 'lucide-react';
import { cn } from '../lib/utils';

const API_URL = 'http://localhost:8000';

const NIVEAUX = {
    bloquant: { label: 'Bloquant', icon: ShieldAlert, cls: 'text-red-600', badge: 'bg-red-500/10 text-red-600 border-red-500/20' },
    avertissement: { label: 'Avertissement', icon: AlertTriangle, cls: 'text-orange-600', badge: 'bg-orange-500/10 text-orange-600 border-orange-500/20' },
    info: { label: 'À compléter', icon: Info, cls: 'text-blue-600', badge: 'bg-blue-500/10 text-blue-600 border-blue-500/20' },
};

export function ConformitePage() {
    const { data, isLoading } = useQuery({
        queryKey: ['conformite'],
        queryFn: async () => (await axios.get(`${API_URL}/conformite`)).data,
        refetchInterval: 8000,
    });

    if (isLoading) return <div>Analyse de conformité en cours...</div>;

    const { alertes = [], compteurs = {}, pret_a_deposer } = data || {};

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <header>
                <h1 className="text-3xl font-bold tracking-tight">Conformité du compte</h1>
                <p className="text-muted-foreground">Contrôles automatiques pour prévenir un rejet du compte de campagne.</p>
            </header>

            {/* Bandeau prêt à déposer */}
            <div className={cn(
                "rounded-2xl border p-6 flex items-center gap-4",
                pret_a_deposer ? "border-green-200 bg-green-50/10" : "border-red-200 bg-red-50/10"
            )}>
                {pret_a_deposer
                    ? <ShieldCheck className="w-10 h-10 text-green-600" />
                    : <ShieldAlert className="w-10 h-10 text-red-600" />}
                <div>
                    <h2 className="text-xl font-bold">
                        {pret_a_deposer ? "Aucun motif de rejet détecté" : "Motifs de rejet à corriger"}
                    </h2>
                    <p className="text-sm text-muted-foreground">
                        {pret_a_deposer
                            ? "Les avertissements et points à compléter ci-dessous restent à traiter avant le dépôt."
                            : "Au moins un point bloquant empêche un dépôt conforme."}
                    </p>
                </div>
            </div>

            {/* Compteurs */}
            <div className="grid gap-4 grid-cols-3">
                {['bloquant', 'avertissement', 'info'].map((niv) => {
                    const N = NIVEAUX[niv];
                    return (
                        <div key={niv} className="bg-card rounded-xl border border-border p-5 flex items-center gap-4">
                            <N.icon className={cn("w-7 h-7", N.cls)} />
                            <div>
                                <div className="text-2xl font-bold">{compteurs[niv] || 0}</div>
                                <div className="text-xs uppercase tracking-wider text-muted-foreground">{N.label}</div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Liste des alertes */}
            <div className="rounded-md border border-border bg-card divide-y divide-border">
                {alertes.length === 0 && (
                    <div className="py-16 text-center">
                        <CheckCircle2 className="w-14 h-14 text-green-500 mx-auto mb-3 opacity-30" />
                        <p className="text-muted-foreground italic">Aucune alerte. Le compte est conforme.</p>
                    </div>
                )}
                {alertes.map((a, i) => {
                    const N = NIVEAUX[a.niveau] || NIVEAUX.info;
                    return (
                        <div key={i} className="flex items-center gap-3 px-5 py-3 hover:bg-muted/40">
                            <N.icon className={cn("w-4 h-4 shrink-0", N.cls)} />
                            <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase shrink-0", N.badge)}>
                                {N.label}
                            </span>
                            <span className="text-sm flex-1">{a.message}</span>
                            <span className="text-[10px] text-muted-foreground font-mono shrink-0">{a.code}</span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
