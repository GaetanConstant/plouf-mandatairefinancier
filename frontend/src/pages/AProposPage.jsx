import React from 'react';
import { Info } from 'lucide-react';
import VERSIONS from '../data/versions.json';

// L'historique n'est pas écrit ici : la source de vérité est CHANGELOG.md à la
// racine du dépôt, converti en JSON par `uv run scripts/changelog_to_json.py`.
// Cette page ne fait que le rendu.

const VERSION_COURANTE = VERSIONS[0]?.version ?? '';
const ANNEE_COURANTE = VERSIONS[0]?.date?.slice(0, 4) ?? '';

export function AProposPage() {
    return (
        <div className="space-y-4 animate-in fade-in duration-500">
            <div>
                <h2 className="text-2xl font-bold tracking-tight">À propos</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                    Mandataire financier <span className="font-semibold text-foreground">{VERSION_COURANTE}</span> —
                    historique des versions, de la plus récente à la plus ancienne.
                </p>
            </div>

            <div className="flex flex-col gap-3 max-w-3xl">
                {VERSIONS.map(({ version, dateAffichee, titre, details, majeur }) => (
                    <div
                        key={version}
                        className={`rounded-md border border-border bg-card p-5 ${majeur ? 'border-l-4 border-l-primary' : ''}`}
                    >
                        <div className="mb-3 flex flex-wrap items-baseline gap-3">
                            <span
                                className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-black uppercase tracking-wider ${
                                    majeur ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground'
                                }`}
                            >
                                {version}
                            </span>
                            <h3 className="m-0 text-sm font-black">{titre}</h3>
                            {version === VERSION_COURANTE && (
                                <span className="rounded-full border border-border px-1.5 py-0.5 text-[10px] font-black uppercase tracking-wider text-muted-foreground">
                                    version actuelle
                                </span>
                            )}
                            <span className="ml-auto text-xs font-bold text-muted-foreground">{dateAffichee}</span>
                        </div>
                        <ul className="m-0 list-disc pl-5 text-[13px] leading-relaxed text-muted-foreground">
                            {details.map((d, i) => <li key={i}>{d}</li>)}
                        </ul>
                    </div>
                ))}
            </div>

            <p className="flex items-center gap-2 pt-2 text-xs text-muted-foreground">
                <Info size={14} /> © {ANNEE_COURANTE} SCOPA
            </p>
        </div>
    );
}
