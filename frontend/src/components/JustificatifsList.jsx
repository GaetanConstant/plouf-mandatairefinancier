
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import {
    File,
    FileText,
    Image as ImageIcon,
    Trash2,
    ExternalLink,
    Search,
    Download,
    FileQuestion,
    Loader2
} from 'lucide-react';
import { Button } from './ui/Components';
import { API_URL } from '../lib/api';


export function JustificatifsList() {
    const queryClient = useQueryClient();
    const [searchTerm, setSearchTerm] = useState('');

    const { data: files, isLoading, error } = useQuery({
        queryKey: ['justificatifs'],
        queryFn: async () => {
            const response = await axios.get(`${API_URL}/justificatifs`, { withCredentials: true });
            return response.data;
        }
    });

    const deleteMutation = useMutation({
        mutationFn: async (filename) => {
            await axios.delete(`${API_URL}/justificatifs/${filename}`, { withCredentials: true });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['justificatifs'] });
        }
    });

    const handleDelete = (e, filename) => {
        e.stopPropagation();
        if (window.confirm(`Êtes-vous sûr de vouloir supprimer le fichier ${filename} ?`)) {
            deleteMutation.mutate(filename);
        }
    };

    const getFileIcon = (filename) => {
        const ext = filename.split('.').pop().toLowerCase();
        if (ext === 'pdf') return <FileText className="w-8 h-8 text-red-500" />;
        if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) return <ImageIcon className="w-8 h-8 text-blue-500" />;
        if (['xlsx', 'xls', 'csv'].includes(ext)) return <File className="w-8 h-8 text-green-500" />;
        return <FileQuestion className="w-8 h-8 text-gray-500" />;
    };

    const formatSize = (bytes) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const filteredFiles = files?.filter(file =>
        file.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (isLoading) return (
        <div className="flex flex-col items-center justify-center h-64 gap-4">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
            <p className="text-muted-foreground">Chargement des justificatifs...</p>
        </div>
    );

    if (error) return (
        <div className="p-8 text-center text-red-500 bg-red-50 rounded-xl border border-red-100">
            Une erreur est survenue lors de la récupération des fichiers.
        </div>
    );

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight">Explorateur de Justificatifs</h2>
                    <p className="text-muted-foreground">Gérez et visualisez vos pièces justificatives téléchargées.</p>
                </div>

                <div className="relative w-full md:w-72">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                        type="search"
                        placeholder="Rechercher un fichier..."
                        className="w-full pl-10 pr-4 py-2 bg-card border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            </header>

            {!files?.length ? (
                <div className="flex flex-col items-center justify-center h-64 bg-card rounded-xl border border-dashed border-border p-8 text-center">
                    <FileQuestion className="w-12 h-12 text-muted-foreground mb-4 opacity-20" />
                    <p className="font-medium text-muted-foreground">Aucun justificatif trouvé</p>
                    <p className="text-xs text-muted-foreground/60 mt-1">Les fichiers téléchargés lors de la création de dépenses apparaîtront ici.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {filteredFiles?.map((file) => (
                        <div
                            key={file.name}
                            className="bg-card group border border-border rounded-xl p-4 hover:shadow-md hover:border-primary/20 transition-all duration-300 relative flex flex-col"
                        >
                            <div className="flex items-start justify-between mb-3">
                                <div className="p-3 bg-muted rounded-lg group-hover:bg-primary/5 transition-colors">
                                    {getFileIcon(file.name)}
                                </div>
                                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                                    <a
                                        href={`${API_URL}${file.url}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="p-1.5 hover:bg-muted rounded-md text-muted-foreground hover:text-primary transition-colors"
                                        title="Voir le fichier"
                                        onClick={(e) => e.stopPropagation()}
                                    >
                                        <ExternalLink className="w-4 h-4" />
                                    </a>
                                    <button
                                        onClick={(e) => handleDelete(e, file.name)}
                                        className="p-1.5 hover:bg-destructive/10 rounded-md text-muted-foreground hover:text-destructive transition-colors"
                                        title="Supprimer"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>

                            <div className="mt-auto">
                                <h3 className="font-semibold text-sm truncate mb-1" title={file.name}>
                                    {file.name}
                                </h3>
                                <div className="flex items-center justify-between text-[11px] text-muted-foreground/70">
                                    <span>{formatSize(file.size)}</span>
                                    <span>{new Date(file.mtime).toLocaleDateString('fr-FR')}</span>
                                </div>
                            </div>

                            <a
                                href={`${API_URL}${file.url}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="absolute inset-x-0 inset-y-0 z-0 cursor-pointer pointer-events-none sm:pointer-events-auto"
                                aria-label={`Voir ${file.name}`}
                            ></a>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
