'use client';

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, Shield, FileAudio, Check, Download } from 'lucide-react';
import { GlassPanel, Button } from '@/components/ui';

type Status = 'idle' | 'uploading' | 'processing' | 'completed' | 'error';

const statusMessages = [
    'Analyzing Frequency...',
    'Generating Noise Mask...',
    'Injecting Protection...',
    'Finalizing...'
];

export default function ProtectPage() {
    const [status, setStatus] = useState<Status>('idle');
    const [file, setFile] = useState<File | null>(null);
    const [progress, setProgress] = useState(0);
    const [statusMessage, setStatusMessage] = useState('');

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile && (droppedFile.name.endsWith('.wav') || droppedFile.name.endsWith('.flac') || droppedFile.name.endsWith('.mp3'))) {
            setFile(droppedFile);
            simulateProcessing();
        }
    }, []);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (selectedFile) {
            setFile(selectedFile);
            simulateProcessing();
        }
    };

    const simulateProcessing = () => {
        setStatus('uploading');
        setProgress(0);

        // Simulate upload
        setTimeout(() => {
            setStatus('processing');
            let step = 0;
            const interval = setInterval(() => {
                if (step < statusMessages.length) {
                    setStatusMessage(statusMessages[step]);
                    setProgress((step + 1) * 25);
                    step++;
                } else {
                    clearInterval(interval);
                    setStatus('completed');
                    setProgress(100);
                }
            }, 1500);
        }, 1000);
    };

    const reset = () => {
        setStatus('idle');
        setFile(null);
        setProgress(0);
        setStatusMessage('');
    };

    return (
        <div className="max-w-3xl mx-auto space-y-8">
            <div>
                <h1 className="text-3xl font-bold">The Forge</h1>
                <p className="text-white/60 mt-1">Protect your audio from AI voice cloning</p>
            </div>

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
                            <div className="border-2 border-dashed border-white/20 rounded-2xl p-16 text-center hover:border-[#6C5CE7] transition-colors animate-pulse-border">
                                <div className="w-20 h-20 mx-auto mb-6 rounded-2xl gradient-primary flex items-center justify-center glow-indigo">
                                    <Shield className="w-10 h-10" />
                                </div>
                                <h2 className="text-xl font-semibold mb-2">Drop Master File Here</h2>
                                <p className="text-white/60 mb-4">.WAV / .FLAC / .MP3 (Max 50MB)</p>
                                <p className="text-xs text-white/40">We do not train on your data. Files deleted after 1 hour.</p>
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
                        <GlassPanel className="text-center py-16">
                            <div className="w-24 h-24 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-[#6C5CE7] to-[#00CEC9] flex items-center justify-center relative overflow-hidden">
                                <FileAudio className="w-12 h-12 relative z-10" />
                                <motion.div
                                    className="absolute inset-0 bg-white/20"
                                    initial={{ x: '-100%' }}
                                    animate={{ x: '100%' }}
                                    transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
                                />
                            </div>
                            <h2 className="text-xl font-semibold mb-2">{file?.name}</h2>
                            <p className="text-[#00CEC9] font-medium mb-6">{statusMessage || 'Uploading...'}</p>

                            {/* Progress bar */}
                            <div className="max-w-md mx-auto">
                                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                                    <motion.div
                                        className="h-full gradient-primary"
                                        initial={{ width: 0 }}
                                        animate={{ width: `${progress}%` }}
                                        transition={{ duration: 0.5 }}
                                    />
                                </div>
                                <p className="text-sm text-white/40 mt-2">{progress}%</p>
                            </div>
                        </GlassPanel>
                    </motion.div>
                )}

                {status === 'completed' && (
                    <motion.div
                        key="completed"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                    >
                        <GlassPanel className="text-center py-12">
                            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-[#00B894] flex items-center justify-center">
                                <Check className="w-10 h-10" />
                            </div>
                            <h2 className="text-2xl font-bold mb-2">Protection Complete!</h2>
                            <p className="text-white/60 mb-8">{file?.name?.replace(/\.\w+$/, '_protected.wav')}</p>

                            <div className="grid grid-cols-3 gap-4 max-w-md mx-auto mb-8 text-sm">
                                <div className="bg-white/5 rounded-xl p-4">
                                    <p className="text-white/40">Protection</p>
                                    <p className="font-semibold">Anti-RVC v2</p>
                                </div>
                                <div className="bg-white/5 rounded-xl p-4">
                                    <p className="text-white/40">Quality</p>
                                    <p className="font-semibold">MOS 4.8</p>
                                </div>
                                <div className="bg-white/5 rounded-xl p-4">
                                    <p className="text-white/40">Noise</p>
                                    <p className="font-semibold">0.02%</p>
                                </div>
                            </div>

                            <div className="flex gap-4 justify-center">
                                <Button>
                                    <Download className="w-4 h-4 mr-2 inline" />
                                    Download Protected
                                </Button>
                                <Button variant="secondary" onClick={reset}>
                                    Protect Another
                                </Button>
                            </div>
                        </GlassPanel>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
