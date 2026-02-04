
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Droplets, ChevronRight, Loader2, Plus, Trash2 } from 'lucide-react';
import { Button, Modal, Input } from '../components/ui/Components';

const API_URL = 'http://localhost:8000';

export function CampaignPage({ onSelect, user }) {
    const queryClient = useQueryClient();
    const { data: campaigns, isLoading, error } = useQuery({
        queryKey: ['campaigns'],
        queryFn: async () => {
            const response = await axios.get(`${API_URL}/campaigns`, { withCredentials: true });
            return response.data;
        }
    });

    const [selecting, setSelecting] = useState(null);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [newCampaignName, setNewCampaignName] = useState('');
    const [isCreating, setIsCreating] = useState(false);
    const [campaignToDelete, setCampaignToDelete] = useState(null);
    const [isDeleting, setIsDeleting] = useState(false);

    const handleSelect = async (campaign) => {
        setSelecting(campaign.id);
        try {
            await axios.post(`${API_URL}/select-campaign/${campaign.id}`, {}, { withCredentials: true });
            onSelect(campaign);
        } catch (err) {
            console.error("Selection failed", err);
            alert("Erreur lors de la sélection de la campagne");
        } finally {
            setSelecting(null);
        }
    };

    const handleCreateCampaign = async (e) => {
        e.preventDefault();
        if (!newCampaignName.trim()) return;

        setIsCreating(true);
        try {
            const response = await axios.post(`${API_URL}/campaigns`, { name: newCampaignName }, { withCredentials: true });
            queryClient.invalidateQueries(['campaigns']);
            setIsCreateModalOpen(false);
            setNewCampaignName('');
            // Automatically select the new campaign
            handleSelect(response.data);
        } catch (err) {
            console.error("Creation failed", err);
            alert("Erreur lors de la création de la campagne");
        } finally {
            setIsCreating(false);
        }
    };

    const handleDeleteCampaign = async () => {
        if (!campaignToDelete) return;
        setIsDeleting(true);
        try {
            await axios.delete(`${API_URL}/campaigns/${campaignToDelete.id}`, { withCredentials: true });
            queryClient.invalidateQueries(['campaigns']);
            setCampaignToDelete(null);
        } catch (err) {
            console.error("Deletion failed", err);
            alert(err.response?.data?.detail || "Erreur lors de la suppression de la campagne");
        } finally {
            setIsDeleting(false);
        }
    };

    if (isLoading) {
        return (
            <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
                <Loader2 className="w-12 h-12 text-primary animate-spin" />
                <p className="mt-4 text-muted-foreground">Chargement de vos campagnes...</p>
            </div>
        );
    }

    const isAdmin = user?.role === 'admin';

    return (
        <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
            <Modal
                isOpen={isCreateModalOpen}
                onClose={() => setIsCreateModalOpen(false)}
                title="Nouvelle Campagne"
            >
                <form onSubmit={handleCreateCampaign} className="space-y-4">
                    <Input
                        label="Nom de la campagne"
                        placeholder="Ex: Municipales Lyon 2026"
                        value={newCampaignName}
                        onChange={(e) => setNewCampaignName(e.target.value)}
                        required
                        autoFocus
                    />
                    <div className="flex justify-end gap-3 mt-6">
                        <Button type="button" variant="ghost" onClick={() => setIsCreateModalOpen(false)}>
                            Annuler
                        </Button>
                        <Button type="submit" isLoading={isCreating}>
                            Créer la campagne
                        </Button>
                    </div>
                </form>
            </Modal>

            <Modal
                isOpen={!!campaignToDelete}
                onClose={() => setCampaignToDelete(null)}
                title="Supprimer la campagne"
            >
                <div className="space-y-4">
                    <p className="text-muted-foreground">
                        Êtes-vous sûr de vouloir supprimer la campagne <span className="font-bold text-foreground">"{campaignToDelete?.name}"</span> ?
                    </p>
                    <p className="text-sm text-destructive bg-destructive/10 p-3 rounded-lg border border-destructive/20 font-medium">
                        Attention : Cette action est irréversible et supprimera définitivement toutes les données de cette campagne (recettes, dépenses, justificatifs).
                    </p>
                    <div className="flex justify-end gap-3 mt-6">
                        <Button type="button" variant="ghost" onClick={() => setCampaignToDelete(null)}>
                            Annuler
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={handleDeleteCampaign}
                            isLoading={isDeleting}
                        >
                            Supprimer définitivement
                        </Button>
                    </div>
                </div>
            </Modal>

            <div className="w-full max-w-2xl">
                <div className="flex flex-col items-center mb-12">
                    <div className="p-4 bg-primary/10 rounded-full mb-4">
                        <Droplets className="w-12 h-12 text-primary" />
                    </div>
                    <h1 className="text-3xl font-bold tracking-tight">Vos campagnes</h1>
                    <p className="text-muted-foreground mt-2">
                        Sélectionnez une campagne ou créez-en une nouvelle.
                    </p>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                    {campaigns?.map((campaign) => (
                        <div key={campaign.id} className="relative group/card">
                            <button
                                disabled={selecting !== null}
                                onClick={() => handleSelect(campaign)}
                                className="w-full h-full flex flex-col items-start p-6 bg-card border border-border rounded-xl shadow-sm hover:shadow-md hover:border-primary/50 transition-all text-left overflow-hidden disabled:opacity-50"
                            >
                                <div className="flex justify-between items-start w-full mb-4">
                                    <div className="p-2 bg-primary/5 rounded-lg group-hover:bg-primary/10 transition-colors">
                                        <Droplets className="w-6 h-6 text-primary" />
                                    </div>
                                    <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-primary transform group-hover:translate-x-1 transition-all" />
                                </div>
                                <h3 className="text-xl font-bold mb-1">{campaign.name}</h3>
                                <p className="text-sm text-muted-foreground">Mandat en cours • 2026</p>

                                {selecting === campaign.id && (
                                    <div className="absolute inset-0 bg-background/50 flex items-center justify-center z-10">
                                        <Loader2 className="w-6 h-6 text-primary animate-spin" />
                                    </div>
                                )}
                            </button>

                            {isAdmin && (
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setCampaignToDelete(campaign);
                                    }}
                                    className="absolute top-4 right-10 p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-all opacity-0 group-hover/card:opacity-100 z-20"
                                    title="Supprimer la campagne"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            )}
                        </div>
                    ))}

                    <button
                        onClick={() => setIsCreateModalOpen(true)}
                        className="flex flex-col items-center justify-center p-6 bg-muted/20 border-2 border-dashed border-border rounded-xl hover:bg-muted/30 hover:border-primary/50 transition-all text-center group min-h-[160px]"
                    >
                        <div className="p-3 bg-primary/5 rounded-full mb-3 group-hover:bg-primary/10 transition-colors">
                            <Plus className="w-6 h-6 text-primary" />
                        </div>
                        <span className="font-bold text-lg">Nouvelle campagne</span>
                        <p className="text-xs text-muted-foreground mt-1">Démarrer un nouveau mandat</p>
                    </button>
                </div>

                {campaigns?.length === 0 && !isCreateModalOpen && (
                    <div className="text-center mt-8 p-8 bg-muted/30 rounded-xl border border-dashed border-border animate-in fade-in duration-500">
                        <p className="text-muted-foreground">Vous n'avez pas encore de campagne active.</p>
                        <button
                            onClick={() => setIsCreateModalOpen(true)}
                            className="text-primary font-medium hover:underline mt-2"
                        >
                            Créer ma première campagne
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
