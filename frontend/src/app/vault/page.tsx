'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Download, Trash2, Clock, Search, Filter } from 'lucide-react';
import { GlassPanel, Badge } from '@/components/ui';
import { api, Task } from '@/lib/api';

export default function VaultPage() {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [filterStatus, setFilterStatus] = useState<string>('all');

    useEffect(() => {
        const fetchTasks = async () => {
            try {
                const data = await api.getTasks();
                setTasks(data);
            } catch (err) {
                console.error('Failed to load tasks', err);
            } finally {
                setLoading(false);
            }
        };
        fetchTasks();
    }, []);

    const handleDownload = (taskId: string) => {
        const url = api.getDownloadUrl(taskId);
        window.open(url, '_blank');
    };

    const handleDelete = async (taskId: string) => {
        try {
            await api.deleteTask(taskId);
            setTasks(tasks.filter(t => t.id !== taskId));
        } catch (err) {
            console.error('Failed to delete task', err);
        }
    };

    const filteredTasks = tasks.filter(task => {
        const matchesSearch = task.original_name.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesFilter = filterStatus === 'all' || task.status === filterStatus;
        return matchesSearch && matchesFilter;
    });

    if (loading) {
        return (
            <div className="flex h-[50vh] items-center justify-center">
                <Spinner />
            </div>
        );
    }

    return (
        <div className="space-y-8 max-w-6xl mx-auto">
            <motion.div 
                className="flex flex-col md:flex-row md:items-end justify-between gap-4"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
            >
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">My Vault</h1>
                    <p className="text-[var(--text-muted)] mt-1">Your protected audio library</p>
                </div>

                <div className="flex items-center gap-3 w-full md:w-auto">
                    <div className="relative flex-1 md:w-64">
                        <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                        <input
                            type="text"
                            placeholder="Search files..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="input-glass"
                        />
                    </div>
                    <div className="relative">
                        <Filter className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] pointer-events-none" />
                        <select
                            value={filterStatus}
                            onChange={(e) => setFilterStatus(e.target.value)}
                            className="appearance-none bg-[rgba(243,238,255,0.6)] border border-[var(--glass-border)] rounded-xl py-2.5 pl-10 pr-8 text-[var(--text-primary)] focus:outline-none focus:border-[var(--violet)] transition-all cursor-pointer text-sm"
                        >
                            <option value="all" className="bg-white">All Status</option>
                            <option value="completed" className="bg-white">Protected</option>
                            <option value="processing" className="bg-white">Processing</option>
                            <option value="queued" className="bg-white">Queued</option>
                            <option value="expired" className="bg-white">Expired</option>
                            <option value="failed" className="bg-white">Failed</option>
                        </select>
                    </div>
                </div>
            </motion.div>

            <motion.div
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
            >
                <GlassPanel>
                    <div className="grid gap-3">
                        <AnimatePresence mode="popLayout">
                            {filteredTasks.map((task) => (
                                <motion.div
                                    key={task.id}
                                    layout
                                    initial={{ opacity: 0, y: 10, scale: 0.98 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.95 }}
                                    transition={{ duration: 0.2 }}
                                    className="flex flex-col md:flex-row md:items-center justify-between p-4 bg-[rgba(124,58,237,0.03)] rounded-2xl hover:bg-[rgba(124,58,237,0.07)] transition-all duration-200 group gap-4"
                                >
                                    <div className="flex items-center gap-4 min-w-0">
                                        <div className={`w-12 h-12 flex-shrink-0 rounded-2xl flex items-center justify-center ${task.status === 'expired' ? 'bg-[rgba(30,16,51,0.06)]' : 'gradient-primary glow-lavender'}`}>
                                            {task.status === 'expired' ? <Clock className="w-6 h-6 text-[var(--text-muted)]" /> : <Shield className="w-6 h-6 text-white" />}
                                        </div>
                                        <div className="min-w-0">
                                            <p className="font-medium truncate text-sm">{task.original_name}</p>
                                            <div className="flex items-center gap-3 text-xs text-[var(--text-muted)] mt-1">
                                                <span>{new Date(task.created_at).toLocaleDateString()}</span>
                                                {task.processed_at && (
                                                    <>
                                                        <span className="w-1 h-1 rounded-full bg-[var(--text-muted)]" />
                                                        <span>{new Date(task.processed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                                                    </>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex items-center justify-between md:justify-end gap-6">
                                        {task.status === 'completed' && <Badge status="secure">PROTECTED</Badge>}
                                        {task.status === 'expired' && <Badge status="vulnerable">EXPIRED</Badge>}
                                        {task.status === 'failed' && <Badge status="vulnerable">FAILED</Badge>}
                                        {(task.status === 'queued' || task.status === 'processing') && <Badge status="processing">PROCESSING...</Badge>}
                                        
                                        <div className="flex gap-2 md:opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                                            {task.status === 'completed' && (
                                                <motion.button 
                                                    whileHover={{ scale: 1.05 }}
                                                    whileTap={{ scale: 0.95 }}
                                                    onClick={() => handleDownload(task.id)} 
                                                    className="p-2 bg-[rgba(124,58,237,0.08)] hover:bg-[rgba(124,58,237,0.15)] rounded-xl transition-colors text-[var(--violet)]"
                                                >
                                                    <Download className="w-4 h-4" />
                                                </motion.button>
                                            )}
                                            <motion.button 
                                                whileHover={{ scale: 1.05 }}
                                                whileTap={{ scale: 0.95 }}
                                                onClick={() => handleDelete(task.id)}
                                                className="p-2 bg-[rgba(244,63,94,0.05)] hover:bg-[rgba(244,63,94,0.12)] rounded-xl transition-colors text-[var(--rose)]"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </motion.button>
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>

                        {filteredTasks.length === 0 && (
                            <motion.div 
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="text-center py-16 text-[var(--text-muted)]"
                            >
                                <Shield className="w-16 h-16 mx-auto mb-4 opacity-15" />
                                <p className="text-lg">No audio files found</p>
                                {searchQuery && <p className="text-sm mt-2">Try adjusting your search or filters</p>}
                            </motion.div>
                        )}
                    </div>
                </GlassPanel>
            </motion.div>
        </div>
    );
}

function Spinner() {
    return <div className="w-8 h-8 border-2 border-[var(--violet)] border-t-transparent rounded-full animate-spin" />;
}
