'use client';

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, FileAudio, Check, Download, Sparkles } from 'lucide-react';
import { GlassPanel, Button } from '@/components/ui';
import { api, Task } from '@/lib/api';

type Status = 'idle' | 'uploading' | 'processing' | 'completed' | 'error';

export default function ProtectPage() {
    const [status, setStatus] = useState<Status>('idle');
    const [file, setFile] = useState<File | null>(null);
    const [progress, setProgress] = useState(0);
    const [statusMessage, setStatusMessage] = useState('');
    const [task, setTask] = useState<Task | null>(null);
    const [error, setError] = useState<string | null>(null);

    const processFile = async (selectedFile: File) => {
        setFile(selectedFile);
        setStatus('uploading');
        setProgress(0);
        setError(null);

        try {
            // Upload file
            const uploadedTask = await api.uploadFile(selectedFile, (p) => {
                setProgress(Math.min(p, 30));
            });

            setTask(uploadedTask);
            setStatus('processing');
            setStatusMessage('Queued for processing...');
            setProgress(30);

            // Poll for status
            await api.pollTaskStatus(
                uploadedTask.id,
                (taskStatus) => {
                    const progressMap: Record<string, number> = {
                        'queued': 35,
                        'processing': 50,
                    };
                    setProgress(progressMap[taskStatus.status] || 50);

                    if (taskStatus.progress) {
                        setStatusMessage(taskStatus.progress);
                        if (taskStatus.progress.includes('chunk')) {
                            setProgress(60 + Math.random() * 30);
                        }
                    } else {
                        setStatusMessage(taskStatus.status === 'processing' ? 'Applying protection...' : 'Queued...');
                    }
                },
                2000
            );

            setStatus('completed');
            setProgress(100);
            setStatusMessage('Protection complete!');

        } catch (err) {
            setStatus('error');
            setError(err instanceof Error ? err.message : 'An error occurred');
        }
    };

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile && /\.(wav|flac|mp3)$/i.test(droppedFile.name)) {
            processFile(droppedFile);
        }
    }, []);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (selectedFile) {
            processFile(selectedFile);
        }
    };

    const handleDownload = () => {
        if (task) {
            window.open(api.getDownloadUrl(task.id), '_blank');
        }
    };

    const reset = () => {
        setStatus('idle');
        setFile(null);
        setProgress(0);
        setStatusMessage('');
        setTask(null);
        setError(null);
    };

    return (
        <div className="max-w-3xl mx-auto space-y-8">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
            >
                <h1 className="text-3xl font-bold tracking-tight">The Forge</h1>
                <p className="text-[var(--text-muted)] mt-1">Protect your audio from AI voice cloning</p>
            </motion.div>

            <AnimatePresence mode="wait">
                {status === 'idle' && (
                    <motion.div
                        key="dropzone"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                    >
                        <label
                            onDrop={handleDrop}
                            onDragOver={(e) => e.preventDefault()}
                            className="block cursor-pointer"
                        >
                            <div className="relative border-2 border-dashed border-[rgba(124,58,237,0.2)] rounded-3xl p-16 text-center hover:border-[var(--violet)] transition-all duration-300 animate-pulse-border group overflow-hidden bg-white/50">
                                {/* Ambient glow */}
                                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-[rgba(124,58,237,0.04)] rounded-full blur-[80px] group-hover:bg-[rgba(124,58,237,0.08)] transition-all duration-500" />
                                
                                <div className="relative z-10">
                                    <motion.div 
                                        className="w-20 h-20 mx-auto mb-6 rounded-3xl gradient-primary flex items-center justify-center glow-violet"
                                        animate={{ y: [0, -6, 0] }}
                                        transition={{ repeat: Infinity, duration: 3, ease: 'easeInOut' }}
                                    >
                                        <Shield className="w-10 h-10 text-white" />
                                    </motion.div>
                                    <h2 className="text-xl font-semibold mb-2 tracking-tight">Drop Master File Here</h2>
                                    <p className="text-[var(--text-secondary)] mb-4">.WAV / .FLAC / .MP3 (Max 50MB)</p>
                                    <div className="flex items-center justify-center gap-2 text-xs text-[var(--text-muted)]">
                                        <Sparkles className="w-3 h-3" />
                                        <span>We do not train on your data. Files deleted after 1 hour.</span>
                                    </div>
                                </div>
                            </div>
                            <input
                                type="file"
                                accept=".wav,.flac,.mp3"
                                onChange={handleFileSelect}
                                className="hidden"
                            />
                        </label>
                    </motion.div>
                )}

                {(status === 'uploading' || status === 'processing') && (
                    <motion.div
                        key="processing"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                    >
                        <GlassPanel className="text-center py-16 relative overflow-hidden">
                            {/* Background glow */}
                            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-80 h-80 bg-[rgba(124,58,237,0.05)] rounded-full blur-[100px]" />
                            
                            <div className="relative z-10">
                                <div className="w-24 h-24 mx-auto mb-6 rounded-3xl gradient-primary flex items-center justify-center relative overflow-hidden glow-violet">
                                    <FileAudio className="w-12 h-12 relative z-10 text-white" />
                                    <motion.div
                                        className="absolute inset-0 bg-white/20"
                                        initial={{ x: '-100%' }}
                                        animate={{ x: '100%' }}
                                        transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
                                    />
                                </div>
                                <h2 className="text-xl font-semibold mb-2 tracking-tight">{file?.name}</h2>
                                <p className="text-[var(--violet)] font-medium mb-6">{statusMessage}</p>

                                <div className="max-w-md mx-auto">
                                    <div className="h-2 bg-[rgba(124,58,237,0.08)] rounded-full overflow-hidden">
                                        <motion.div
                                            className="h-full gradient-primary"
                                            initial={{ width: 0 }}
                                            animate={{ width: `${progress}%` }}
                                            transition={{ duration: 0.5 }}
                                        />
                                    </div>
                                    <p className="text-sm text-[var(--text-muted)] mt-2">{Math.round(progress)}%</p>
                                </div>
                            </div>
                        </GlassPanel>
                    </motion.div>
                )}

                {status === 'completed' && task && (
                    <motion.div
                        key="completed"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                    >
                        <GlassPanel className="text-center py-12 relative overflow-hidden">
                            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-80 h-40 bg-[rgba(16,185,129,0.06)] rounded-full blur-[80px]" />
                            
                            <div className="relative z-10">
                                <motion.div 
                                    className="w-20 h-20 mx-auto mb-6 rounded-full bg-[rgba(16,185,129,0.1)] border border-[rgba(16,185,129,0.25)] flex items-center justify-center"
                                    initial={{ scale: 0 }}
                                    animate={{ scale: 1 }}
                                    transition={{ type: 'spring', stiffness: 400, damping: 15 }}
                                >
                                    <Check className="w-10 h-10 text-[var(--emerald)]" />
                                </motion.div>
                                <h2 className="text-2xl font-bold mb-2 tracking-tight">Protection Complete!</h2>
                                <p className="text-[var(--text-secondary)] mb-8">{task.original_name.replace(/\.\w+$/, '_protected.wav')}</p>

                                <div className="grid grid-cols-3 gap-4 max-w-md mx-auto mb-8 text-sm">
                                    <div className="bg-[rgba(124,58,237,0.04)] rounded-2xl p-4 border border-[var(--glass-border)]">
                                        <p className="text-[var(--text-muted)] text-xs">Protection</p>
                                        <p className="font-semibold mt-1">Anti-RVC v2</p>
                                    </div>
                                    <div className="bg-[rgba(124,58,237,0.04)] rounded-2xl p-4 border border-[var(--glass-border)]">
                                        <p className="text-[var(--text-muted)] text-xs">Quality</p>
                                        <p className="font-semibold mt-1">MOS 4.8</p>
                                    </div>
                                    <div className="bg-[rgba(124,58,237,0.04)] rounded-2xl p-4 border border-[var(--glass-border)]">
                                        <p className="text-[var(--text-muted)] text-xs">Noise</p>
                                        <p className="font-semibold mt-1">0.02%</p>
                                    </div>
                                </div>

                                <div className="flex gap-4 justify-center">
                                    <Button onClick={handleDownload}>
                                        <Download className="w-4 h-4 mr-2 inline" />
                                        Download Protected
                                    </Button>
                                    <Button variant="secondary" onClick={reset}>
                                        Protect Another
                                    </Button>
                                </div>
                            </div>
                        </GlassPanel>
                    </motion.div>
                )}

                {status === 'error' && (
                    <motion.div
                        key="error"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                    >
                        <GlassPanel className="text-center py-12 relative overflow-hidden">
                            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-60 h-40 bg-[rgba(244,63,94,0.04)] rounded-full blur-[80px]" />
                            
                            <div className="relative z-10">
                                <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-[rgba(244,63,94,0.08)] border border-[rgba(244,63,94,0.2)] flex items-center justify-center">
                                    <span className="text-3xl text-[var(--rose)]">!</span>
                                </div>
                                <h2 className="text-2xl font-bold mb-2 tracking-tight">Processing Failed</h2>
                                <p className="text-[var(--text-secondary)] mb-8">{error}</p>
                                <Button onClick={reset}>Try Again</Button>
                            </div>
                        </GlassPanel>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
