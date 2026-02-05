import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import {
    FileCheck,
    Download,
    TrendingUp,
    Search,
    ShieldCheck,
    CheckCircle2,
    Clock,
    Send
} from 'lucide-react';
import { Modal, Button, Input } from './ui/Components';
import { cn } from '../lib/utils';
import { Edit2 } from 'lucide-react';

const API_URL = 'http://localhost:8000';

export function AttestationsPage({ campaignId }) {
    const queryClient = useQueryClient();
    const [searchTerm, setSearchTerm] = useState('');
    const [editingItem, setEditingItem] = useState(null);
    const [editFormData, setEditFormData] = useState({ nom_donateur: '', rue: '', cp: '69100', ville: 'Villeurbanne' });

    const { data: recettes, isLoading } = useQuery({
        queryKey: ['recettes', campaignId],
        queryFn: async () => {
            const response = await axios.get(`${API_URL}/recettes`);
            return response.data;
        }
    });

    const updateRecetteMutation = useMutation({
        mutationFn: async ({ id, data }) => {
            const original = recettes.find(r => r.id === id);
            await axios.put(`${API_URL}/recettes/${id}`, { ...original, ...data }, { withCredentials: true });
        },
        onSuccess: () => {
            queryClient.invalidateQueries(['recettes', campaignId]);
            setEditingItem(null);
        }
    });

    const markSentMutation = useMutation({
        mutationFn: async (id) => {
            await axios.post(`${API_URL}/attestations/recette/${id}/sent`, {}, { withCredentials: true });
        },
        onSuccess: () => {
            queryClient.invalidateQueries(['recettes', campaignId]);
        }
    });

    const handleDownload = (id) => {
        // Use window.location.href to ensure cookies are sent if opening in same tab, 
        // or _blank relies on browser cookie policy. 
        // Usually plain window.open works for cookie auth on same domain/localhost.
        // We'll append a timestamp to prevent caching issues.
        window.open(`${API_URL}/attestations/recette/${id}?t=${Date.now()}`, '_blank');
    };

    const startEditing = (item) => {
        setEditingItem(item);

        let rue = '';
        let cp = '69100';
        let ville = 'Villeurbanne';

        // Tentative de parsing si l'adresse existe déjà et n'est pas l'import par défaut
        if (item.adresse && item.adresse !== 'Import Excel') {
            const match = item.adresse.match(/^(.*),\s*(\d{5})\s+(.*)$/);
            if (match) {
                rue = match[1];
                cp = match[2];
                ville = match[3];
            } else {
                rue = item.adresse;
            }
        }

        setEditFormData({
            nom_donateur: item.nom_donateur,
            rue,
            cp,
            ville
        });
    };

    const handleSaveEdit = (e) => {
        e.preventDefault();
        updateRecetteMutation.mutate({
            id: editingItem.id,
            data: {
                nom_donateur: editFormData.nom_donateur,
                adresse: `${editFormData.rue}, ${editFormData.cp} ${editFormData.ville}`
            }
        });
    };

    const filteredItems = (recettes || [])
        .filter(item => item.type === 'Don' || item.type === 'Dons')
        .filter(item => item.nom_donateur.toLowerCase().includes(searchTerm.toLowerCase()))
        .sort((a, b) => new Date(b.date) - new Date(a.date));

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Reçus des Donateurs</h1>
                    <p className="text-muted-foreground underline decoration-primary/30 decoration-2 underline-offset-4">Complétez les informations légales puis générez les reçus fiscaux.</p>
                </div>

                <div className="flex items-center gap-3">
                    <div className="relative w-72">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                        <input
                            type="search"
                            placeholder="Rechercher un donateur..."
                            className="w-full pl-10 pr-4 py-2.5 bg-card border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all font-medium"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                </div>
            </header>

            <div className="grid gap-4">
                {isLoading ? (
                    <div className="py-20 text-center">Chargement...</div>
                ) : filteredItems.map((item) => (
                    <div
                        key={item.id}
                        className={cn(
                            "bg-card p-5 rounded-2xl border transition-all flex flex-col md:flex-row md:items-center justify-between gap-4",
                            item.date_envoi ? "border-green-200 bg-green-50/10" :
                                (!item.adresse || item.adresse === 'Import Excel' ? "border-orange-200 bg-orange-50/5" : "border-border hover:border-primary/30")
                        )}
                    >
                        <div className="flex items-center gap-4 flex-1">
                            <div className={cn(
                                "p-3 rounded-full",
                                item.date_envoi ? "bg-green-100 text-green-600" : "bg-primary/10 text-primary"
                            )}>
                                <TrendingUp className="w-5 h-5" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                    <h3 className="font-bold text-lg truncate">{item.nom_donateur}</h3>
                                    {item.date_envoi && (
                                        <span className="flex items-center gap-1 text-[10px] bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">
                                            <CheckCircle2 className="w-3 h-3" /> Envoyé
                                        </span>
                                    )}
                                </div>
                                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground mt-0.5">
                                    <span className="font-semibold text-foreground">{item.montant} €</span>
                                    <span>•</span>
                                    <span className={cn(
                                        "truncate max-w-[200px]",
                                        (!item.adresse || item.adresse === 'Import Excel') ? "text-orange-600 font-bold" : ""
                                    )}>
                                        {(!item.adresse || item.adresse === 'Import Excel') ? "Adresse à compléter" : item.adresse}
                                    </span>
                                    <span>•</span>
                                    <span>{item.date ? new Date(item.date).toLocaleDateString('fr-FR') : 'Date inconnue'}</span>
                                    {item.date_envoi && (
                                        <span className="flex items-center gap-1 text-green-600 font-medium italic">
                                            <Send className="w-3.5 h-3.5 ml-1" /> Envoyé le {item.date_envoi}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center gap-2 self-end md:self-center">
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => startEditing(item)}
                                className="h-12 w-12 p-0 rounded-xl hover:bg-orange-100/50 hover:text-orange-600"
                            >
                                <Edit2 className="w-5 h-5" />
                            </Button>

                            <div className="flex items-center gap-4 px-4 py-2 bg-muted/30 rounded-xl border border-border/50">
                                <label className="flex items-center gap-2 cursor-pointer group">
                                    <input
                                        type="checkbox"
                                        className="w-5 h-5 rounded-md border-gray-300 text-green-600 focus:ring-green-500 cursor-pointer transition-all"
                                        checked={!!item.date_envoi}
                                        onChange={() => markSentMutation.mutate(item.id)}
                                    />
                                    <span className={cn(
                                        "text-sm font-bold transition-colors hidden lg:inline",
                                        item.date_envoi ? "text-green-600" : "text-muted-foreground group-hover:text-foreground"
                                    )}>
                                        Accordé
                                    </span>
                                </label>
                            </div>

                            <Button
                                onClick={() => handleDownload(item.id)}
                                variant={item.date_envoi ? "outline" : "default"}
                                className={cn(
                                    "gap-2 px-5 py-6 rounded-xl transition-all h-12",
                                    !item.date_envoi && "shadow-lg shadow-primary/10 hover:shadow-primary/20"
                                )}
                                disabled={!item.adresse || item.adresse === 'Import Excel'}
                                title={(!item.adresse || item.adresse === 'Import Excel') ? "Veuillez remplir l'adresse avant de générer" : "Télécharger"}
                            >
                                <Download className="w-5 h-5" />
                                <span className="font-bold">PDF</span>
                            </Button>
                        </div>
                    </div>
                ))}

                {!isLoading && filteredItems.length === 0 && (
                    <div className="py-20 text-center bg-card rounded-2xl border border-dashed border-border shadow-inner">
                        <FileCheck className="w-16 h-16 text-muted-foreground mx-auto mb-4 opacity-20" />
                        <h3 className="text-xl font-bold text-muted-foreground">Aucun donateur trouvé</h3>
                        <p className="text-muted-foreground mt-2 px-4 max-w-md mx-auto italic">
                            Veuillez vérifier que vos recettes sont bien catégorisées en "Don" dans l'import Excel ou l'ajout manuel.
                        </p>
                    </div>
                )}
            </div>

            {/* Modal d'édition */}
            <Modal
                isOpen={!!editingItem}
                onClose={() => setEditingItem(null)}
                title="Informations Légales du Donateur"
            >
                <form onSubmit={handleSaveEdit} className="space-y-4">
                    <Input
                        label="Nom complet du donateur"
                        value={editFormData.nom_donateur}
                        onChange={e => setEditFormData({ ...editFormData, nom_donateur: e.target.value })}
                        required
                    />

                    <Input
                        label="Rue / N°"
                        placeholder="Ex: 123 Rue de la République"
                        value={editFormData.rue}
                        onChange={e => setEditFormData({ ...editFormData, rue: e.target.value })}
                        required
                    />

                    <div className="grid grid-cols-3 gap-3">
                        <Input
                            label="Code Postal"
                            placeholder="69100"
                            value={editFormData.cp}
                            onChange={e => setEditFormData({ ...editFormData, cp: e.target.value })}
                            required
                        />
                        <div className="col-span-2">
                            <Input
                                label="Ville"
                                placeholder="Villeurbanne"
                                value={editFormData.ville}
                                onChange={e => setEditFormData({ ...editFormData, ville: e.target.value })}
                                required
                            />
                        </div>
                    </div>

                    <div className="flex justify-end gap-3 pt-4">
                        <Button type="button" variant="ghost" onClick={() => setEditingItem(null)}>Annuler</Button>
                        <Button type="submit" isLoading={updateRecetteMutation.isPending}>
                            Enregistrer les informations
                        </Button>
                    </div>
                </form>
            </Modal>
        </div>
    );
}
