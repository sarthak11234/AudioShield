'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Shield, Mail, Lock, User, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { useAuth } from '@/lib/AuthContext';

export default function SignupPage() {
    const router = useRouter();
    const { signup } = useAuth();
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await signup(username, email, password);
            router.push('/');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Signup failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center px-4">
            {/* Mesh gradient background */}
            <div className="fixed inset-0 bg-[var(--bg-deepest)]" />
            <div className="fixed top-[20%] right-[20%] w-[500px] h-[500px] bg-[rgba(99,102,241,0.07)] rounded-full blur-[120px] animate-glow-pulse" />
            <div className="fixed bottom-[25%] left-[15%] w-[400px] h-[400px] bg-[rgba(124,58,237,0.06)] rounded-full blur-[100px] animate-glow-pulse" style={{ animationDelay: '1.5s' }} />
            <div className="fixed top-[50%] right-[50%] w-[250px] h-[250px] bg-[rgba(167,139,250,0.04)] rounded-full blur-[80px]" />

            <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="relative z-10 w-full max-w-md"
            >
                {/* Logo */}
                <div className="text-center mb-8">
                    <motion.div 
                        className="w-16 h-16 mx-auto mb-5 rounded-2xl gradient-primary flex items-center justify-center glow-violet"
                        animate={{ y: [0, -4, 0] }}
                        transition={{ repeat: Infinity, duration: 3, ease: 'easeInOut' }}
                    >
                        <Shield className="w-8 h-8 text-white" />
                    </motion.div>
                    <h1 className="text-3xl font-bold gradient-text tracking-tight">
                        Join AudioShield
                    </h1>
                    <p className="text-[var(--text-muted)] mt-1.5 text-sm">Start protecting your audio today</p>
                </div>

                {/* Form Card */}
                <div className="glass-panel p-8">
                    <h2 className="text-xl font-semibold mb-6 tracking-tight">Create your account</h2>

                    {error && (
                        <motion.div 
                            initial={{ opacity: 0, y: -5 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-[rgba(244,63,94,0.06)] border border-[rgba(244,63,94,0.15)] text-[var(--rose)] px-4 py-3 rounded-xl mb-4 text-sm"
                        >
                            {error}
                        </motion.div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label className="text-sm text-[var(--text-muted)] mb-1.5 block">Artist Name</label>
                            <div className="relative">
                                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                                <input
                                    type="text"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    placeholder="Your artist name"
                                    required
                                    className="input-glass"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="text-sm text-[var(--text-muted)] mb-1.5 block">Email</label>
                            <div className="relative">
                                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="you@artist.com"
                                    required
                                    className="input-glass"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="text-sm text-[var(--text-muted)] mb-1.5 block">Password</label>
                            <div className="relative">
                                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="••••••••"
                                    required
                                    minLength={6}
                                    className="input-glass"
                                />
                            </div>
                        </div>

                        <motion.button
                            type="submit"
                            disabled={loading}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.97 }}
                            className="w-full gradient-primary text-white font-semibold py-3 rounded-2xl flex items-center justify-center gap-2 glow-violet disabled:opacity-40 transition-all"
                        >
                            {loading ? 'Creating account...' : 'Create Account'}
                            {!loading && <ArrowRight className="w-4 h-4" />}
                        </motion.button>
                    </form>

                    <p className="text-center text-[var(--text-muted)] text-sm mt-6">
                        Already have an account?{' '}
                        <Link href="/login" className="text-[var(--violet)] hover:text-[var(--violet-deep)] transition-colors font-medium">
                            Sign in
                        </Link>
                    </p>
                </div>
            </motion.div>
        </div>
    );
}
