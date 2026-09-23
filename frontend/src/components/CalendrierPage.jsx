import React from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Download, CalendarRange } from 'lucide-react';
import { Button } from './ui/Components';
import { cn } from '../lib/utils';
import { API_URL } from '../lib/api';

const eur = (v) => (v || 0).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 });

export function CalendrierPage() {
    const { data, isLoading } = useQuery({
        queryKey: ['calendrier'],
        queryFn: async () => (await axios.get(`${API_URL}/calendrier`)).data,
    });

    if (isLoading) return <div>Chargement du calendrier...</div>;

    if (data?.vide) {
        return (
            <div className="space-y-4 animate-in fade-in duration-500">
                <h2 className="text-2xl font-bold tracking-tight">Calendrier de campagne</h2>
                <p className="text-muted-foreground">
                    Aucune date à représenter : renseigne la date du scrutin dans Identité, puis crée des événements.
                </p>
            </div>
        );
    }

    const colonnes = data.colonnes;
    const nbColonnes = colonnes.length;
    // Une case = une semaine. Les plages sans activité sont repliées en une
    // colonne étroite, pour que la campagne réelle occupe la largeur utile.
    const grille = {
        gridTemplateColumns: `14rem ${colonnes
            .map(c => (c.type === 'repli' ? '2.25rem' : 'minmax(0, 1fr)'))
            .join(' ')} 5rem`,
    };

    return (
        <div className="space-y-4 animate-in fade-in duration-500">
            <header className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight">Calendrier de campagne</h2>
                    <p className="text-sm text-muted-foreground">
                        {data.nb_semaines} semaines, de l'ouverture de la période de financement au jour du scrutin.
                        {' '}{data.nb_evenements} événement(s) · {eur(data.total_cout)}
                    </p>
                </div>
                <a href={`${API_URL}/calendrier/export-pdf`} target="_blank" rel="noopener noreferrer">
                    <Button className="gap-2"><Download className="w-4 h-4" /> Exporter (PDF)</Button>
                </a>
            </header>

            <div className="overflow-x-auto rounded-md border border-border bg-card p-3">
                <div className="min-w-[60rem]">
                    {/* Bandeau des mois */}
                    <div className="grid items-end gap-px" style={grille}>
                        <div />
                        {data.mois.map((m, i) => (
                            <div key={i}
                                style={{ gridColumn: `span ${m.largeur}` }}
                                className={cn('truncate border-b border-border pb-1 text-center text-[11px] font-bold uppercase tracking-wide',
                                    m.repli ? 'text-muted-foreground/50' : 'text-muted-foreground')}>
                                {m.libelle}
                            </div>
                        ))}
                        <div />
                    </div>

                    {/* Numéro de semaine : rend explicite qu'une case = une semaine. */}
                    <div className="grid gap-px pb-1" style={grille}>
                        <div />
                        {colonnes.map((c, i) => (
                            <div key={i} className={cn('text-center text-[9px]',
                                c.type === 'repli' ? 'text-muted-foreground/60' : 'text-muted-foreground/70')}>
                                {c.type === 'repli' ? '⋯' : `S${c.numero}`}
                            </div>
                        ))}
                        <div />
                    </div>

                    {data.groupes.map(groupe => (
                        <div key={groupe.titre}>
                            <div className="mt-3 mb-1 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                {groupe.titre}
                            </div>
                            {groupe.lignes.map((ligne, i) => (
                                <div key={i} className="grid items-center gap-px py-0.5 hover:bg-muted/40" style={grille}>
                                    <div className="pr-2 text-xs">
                                        <span className="font-medium">{ligne.libelle}</span>
                                        {ligne.detail && <span className="block text-[10px] text-muted-foreground">{ligne.detail}</span>}
                                    </div>
                                    {ligne.colonne > 0 && <div style={{ gridColumn: `span ${ligne.colonne}` }} />}
                                    <div
                                        style={{ gridColumn: `span ${ligne.largeur}` }}
                                        title={`${ligne.debut}${ligne.fin !== ligne.debut ? ` → ${ligne.fin}` : ''}`}
                                        className={cn('h-3 rounded-full', groupe.jalon ? 'bg-red-500' : 'bg-primary')}
                                    />
                                    {ligne.colonne + ligne.largeur < nbColonnes && (
                                        <div style={{ gridColumn: `span ${nbColonnes - ligne.colonne - ligne.largeur}` }} />
                                    )}
                                    <div className="pl-2 text-right text-[11px] text-muted-foreground">
                                        {ligne.cout ? eur(ligne.cout) : ''}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ))}
                </div>
            </div>

            {data.jalons_apres?.length > 0 && (
                <div className="rounded-md border border-border bg-muted/30 p-4">
                    <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold">
                        <CalendarRange className="w-4 h-4" /> Après le scrutin
                    </h3>
                    <ul className="space-y-0.5 text-sm text-muted-foreground">
                        {data.jalons_apres.map((j, i) => (
                            <li key={i}><span className="font-mono text-xs">{j.date}</span> — {j.libelle}</li>
                        ))}
                    </ul>
                </div>
            )}

            <p className="text-xs text-muted-foreground">
                Ce calendrier est joint au dossier en annexe (enveloppe B) : il est régénéré à chaque export,
                donc toujours conforme aux événements saisis.
            </p>
        </div>
    );
}
