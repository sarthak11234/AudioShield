'use client';

import { GlassPanel, Button } from '@/components/ui';
import { Bell, Shield, Trash2, Moon } from 'lucide-react';

export default function SettingsPage() {
    return (
        <div className="max-w-2xl space-y-8">
            <div>
                <h1 className="text-3xl font-bold">Settings</h1>
                <p className="text-white/60 mt-1">Manage your preferences</p>
            </div>

            <GlassPanel>
                <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
                    <Shield className="w-5 h-5 text-[#6C5CE7]" />
                    Protection Settings
                </h2>
                <div className="space-y-4">
                    <div className="flex items-center justify-between py-3 border-b border-white/10">
                        <div>
                            <p className="font-medium">Protection Level</p>
                            <p className="text-sm text-white/40">Higher = more protection, slightly more noise</p>
                        </div>
                        <select className="bg-white/10 border border-white/20 rounded-lg px-4 py-2 text-white">
                            <option>Standard (ε=0.02)</option>
                            <option>High (ε=0.03)</option>
                            <option>Maximum (ε=0.05)</option>
                        </select>
                    </div>
                    <div className="flex items-center justify-between py-3 border-b border-white/10">
                        <div>
                            <p className="font-medium">Auto-delete after</p>
                            <p className="text-sm text-white/40">Automatically remove files after processing</p>
                        </div>
                        <select className="bg-white/10 border border-white/20 rounded-lg px-4 py-2 text-white">
                            <option>1 hour</option>
                            <option>24 hours</option>
                            <option>7 days</option>
                        </select>
                    </div>
                </div>
            </GlassPanel>

            <GlassPanel>
                <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
                    <Bell className="w-5 h-5 text-[#00CEC9]" />
                    Notifications
                </h2>
                <div className="space-y-4">
                    <div className="flex items-center justify-between py-3">
                        <div>
                            <p className="font-medium">Email when done</p>
                            <p className="text-sm text-white/40">Get notified when processing completes</p>
                        </div>
                        <input type="checkbox" className="w-5 h-5 accent-[#6C5CE7]" />
                    </div>
                </div>
            </GlassPanel>

            <GlassPanel>
                <h2 className="text-lg font-semibold mb-6 flex items-center gap-2 text-[#FF7675]">
                    <Trash2 className="w-5 h-5" />
                    Danger Zone
                </h2>
                <div className="flex items-center justify-between">
                    <div>
                        <p className="font-medium">Delete all data</p>
                        <p className="text-sm text-white/40">Remove all protected files and history</p>
                    </div>
                    <Button variant="secondary" className="border-[#FF7675] text-[#FF7675]">
                        Delete All
                    </Button>
                </div>
            </GlassPanel>
        </div>
    );
}
