'use client';

import { motion } from 'framer-motion';
import { Shield, Download, Trash2 } from 'lucide-react';
import { GlassPanel, Badge } from '@/components/ui';

const vaultItems = [
    { id: 1, name: 'Midnight_Freestyle_v3.wav', date: 'Jan 23, 2026', status: 'secure', size: '24.5 MB' },
    { id: 2, name: 'Summer_Vibes_Final.wav', date: 'Jan 22, 2026', status: 'secure', size: '18.2 MB' },
    { id: 3, name: 'Acoustic_Session_01.flac', date: 'Jan 20, 2026', status: 'secure', size: '45.1 MB' },
    { id: 4, name: 'Beat_Demo_Raw.mp3', date: 'Jan 18, 2026', status: 'secure', size: '8.7 MB' },
];

export default function VaultPage() {
    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-3xl font-bold">My Vault</h1>
                <p className="text-white/60 mt-1">Your protected audio library</p>
            </div>

            <GlassPanel>
                <div className="grid gap-4">
                    {vaultItems.map((item, i) => (
                        <motion.div
                            key={item.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.05 }}
                            className="flex items-center justify-between p-4 bg-white/5 rounded-xl hover:bg-white/10 transition-colors group"
                        >
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 rounded-xl gradient-primary flex items-center justify-center">
                                    <Shield className="w-6 h-6" />
                                </div>
                                <div>
                                    <p className="font-medium">{item.name}</p>
                                    <p className="text-sm text-white/40">{item.date} • {item.size}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-4">
                                <Badge status="secure">PROTECTED</Badge>
                                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button className="p-2 hover:bg-white/10 rounded-lg transition-colors">
                                        <Download className="w-4 h-4" />
                                    </button>
                                    <button className="p-2 hover:bg-white/10 rounded-lg transition-colors text-[#FF7675]">
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </GlassPanel>

            {vaultItems.length === 0 && (
                <div className="text-center py-16 text-white/40">
                    <Shield className="w-16 h-16 mx-auto mb-4 opacity-20" />
                    <p>No protected files yet</p>
                </div>
            )}
        </div>
    );
}
