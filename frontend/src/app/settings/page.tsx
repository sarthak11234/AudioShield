'use client';

import { GlassPanel, Button } from '@/components/ui';
import { Bell, Shield, Trash2 } from 'lucide-react';

export default function SettingsPage() {
    return (
        <div className="max-w-2xl space-y-8">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
                <p className="text-[var(--text-muted)] mt-1">Manage your preferences</p>
            </div>

            <GlassPanel>
                <h2 className="text-lg font-semibold mb-6 flex items-center gap-2 tracking-tight">
                    <Shield className="w-5 h-5 text-[var(--violet)]" />
                    Protection Settings
                </h2>
                <div className="space-y-4">
                    <div className="flex items-center justify-between py-3 border-b border-[var(--glass-border)]">
                        <div>
                            <p className="font-medium text-sm">Protection Level</p>
                            <p className="text-xs text-[var(--text-muted)] mt-0.5">Higher = more protection, slightly more noise</p>
                        </div>
                        <select className="bg-[rgba(243,238,255,0.6)] border border-[var(--glass-border)] rounded-xl px-4 py-2 text-[var(--text-primary)] text-sm focus:outline-none focus:border-[var(--violet)] transition-all cursor-pointer">
                            <option className="bg-white">Standard (ε=0.02)</option>
                            <option className="bg-white">High (ε=0.03)</option>
                            <option className="bg-white">Maximum (ε=0.05)</option>
                        </select>
                    </div>
                    <div className="flex items-center justify-between py-3 border-b border-[var(--glass-border)]">
                        <div>
                            <p className="font-medium text-sm">Auto-delete after</p>
                            <p className="text-xs text-[var(--text-muted)] mt-0.5">Automatically remove files after processing</p>
                        </div>
                        <select className="bg-[rgba(243,238,255,0.6)] border border-[var(--glass-border)] rounded-xl px-4 py-2 text-[var(--text-primary)] text-sm focus:outline-none focus:border-[var(--violet)] transition-all cursor-pointer">
                            <option className="bg-white">1 hour</option>
                            <option className="bg-white">24 hours</option>
                            <option className="bg-white">7 days</option>
                        </select>
                    </div>
                </div>
            </GlassPanel>

            <GlassPanel>
                <h2 className="text-lg font-semibold mb-6 flex items-center gap-2 tracking-tight">
                    <Bell className="w-5 h-5 text-[var(--cyan-accent)]" />
                    Notifications
                </h2>
                <div className="space-y-4">
                    <div className="flex items-center justify-between py-3">
                        <div>
                            <p className="font-medium text-sm">Email when done</p>
                            <p className="text-xs text-[var(--text-muted)] mt-0.5">Get notified when processing completes</p>
                        </div>
                        <input type="checkbox" className="w-5 h-5 accent-[var(--violet)] cursor-pointer" />
                    </div>
                </div>
            </GlassPanel>

            <GlassPanel>
                <h2 className="text-lg font-semibold mb-6 flex items-center gap-2 text-[var(--rose)] tracking-tight">
                    <Trash2 className="w-5 h-5" />
                    Danger Zone
                </h2>
                <div className="flex items-center justify-between">
                    <div>
                        <p className="font-medium text-sm">Delete all data</p>
                        <p className="text-xs text-[var(--text-muted)] mt-0.5">Remove all protected files and history</p>
                    </div>
                    <Button variant="secondary" className="border-[var(--rose)] text-[var(--rose)] hover:bg-[rgba(244,63,94,0.06)]">
                        Delete All
                    </Button>
                </div>
            </GlassPanel>
        </div>
    );
}
