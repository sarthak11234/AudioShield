'use client';

import { motion } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line, XAxis, YAxis } from 'recharts';
import { Shield, Upload, AlertTriangle, CheckCircle, TrendingUp, Zap } from 'lucide-react';
import { GlassPanel, Button, Badge } from '@/components/ui';

const securityData = [
  { name: 'Secured', value: 92, color: '#10B981' },
  { name: 'Vulnerable', value: 8, color: '#F43F5E' },
];

const threatData = [
  { name: 'Mon', attempts: 12 },
  { name: 'Tue', attempts: 19 },
  { name: 'Wed', attempts: 8 },
  { name: 'Thu', attempts: 25 },
  { name: 'Fri', attempts: 15 },
  { name: 'Sat', attempts: 32 },
  { name: 'Sun', attempts: 18 },
];

const recentTracks = [
  { name: 'Midnight_Freestyle_v3.wav', status: 'secure', time: '2m ago' },
  { name: 'Summer_Vibes_Final.wav', status: 'secure', time: '1h ago' },
  { name: 'Demo_Track_01.mp3', status: 'processing', time: 'Processing...' },
];

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5 },
};

export default function Dashboard() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div className="flex items-center justify-between" {...fadeUp}>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Command Center</h1>
          <p className="text-[var(--text-muted)] mt-1">Monitor your audio protection status</p>
        </div>
        <Button>
          <Upload className="w-4 h-4 mr-2 inline" />
          Protect New Track
        </Button>
      </motion.div>

      {/* Stats Row */}
      <motion.div 
        className="grid grid-cols-3 gap-4"
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        {[
          { label: 'Protected Tracks', value: '24', icon: Shield, color: 'var(--emerald)' },
          { label: 'Threats Blocked', value: '156', icon: Zap, color: 'var(--violet)' },
          { label: 'Success Rate', value: '99.2%', icon: TrendingUp, color: 'var(--cyan-accent)' },
        ].map((stat, i) => (
          <GlassPanel key={i} hover>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl flex items-center justify-center" style={{ background: `rgba(${stat.color === 'var(--emerald)' ? '16,185,129' : stat.color === 'var(--violet)' ? '124,58,237' : '14,165,233'}, 0.1)` }}>
                <stat.icon className="w-6 h-6" style={{ color: stat.color }} />
              </div>
              <div>
                <p className="text-2xl font-bold tracking-tight">{stat.value}</p>
                <p className="text-xs text-[var(--text-muted)]">{stat.label}</p>
              </div>
            </div>
          </GlassPanel>
        ))}
      </motion.div>

      {/* Main Grid */}
      <motion.div 
        className="grid grid-cols-3 gap-6"
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        {/* Security Health - Hero Widget */}
        <GlassPanel className="col-span-2 relative" hover>
          {/* Ambient glow */}
          <div className="glow-orb glow-orb-purple w-40 h-40 -top-10 -right-10 animate-glow-pulse" />
          <div className="flex items-center gap-8">
            <div className="relative w-48 h-48">
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={securityData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    dataKey="value"
                    strokeWidth={0}
                  >
                    {securityData.map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex items-center justify-center flex-col">
                <span className="text-4xl font-bold tracking-tight">92%</span>
                <span className="text-sm text-[var(--text-muted)]">Secured</span>
              </div>
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold mb-2 tracking-tight">Catalog Security</h2>
              <p className="text-[var(--text-secondary)] mb-5">Your audio library is well protected</p>
              <div className="flex gap-6">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-[var(--emerald)]" />
                  <span className="text-sm">12 Protected this week</span>
                </div>
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-[var(--rose)]" />
                  <span className="text-sm">3 Tracks vulnerable</span>
                </div>
              </div>
            </div>
          </div>
        </GlassPanel>

        {/* AI Threat Monitor */}
        <GlassPanel hover className="relative">
          <div className="glow-orb glow-orb-indigo w-32 h-32 -bottom-8 -left-8 animate-glow-pulse" />
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 tracking-tight">
            <Shield className="w-5 h-5 text-[var(--cyan-accent)]" />
            AI Landscape Monitor
          </h3>
          <div className="h-32">
            <ResponsiveContainer>
              <LineChart data={threatData}>
                <XAxis dataKey="name" stroke="rgba(30,16,51,0.15)" fontSize={10} />
                <YAxis stroke="rgba(30,16,51,0.15)" fontSize={10} />
                <Line
                  type="monotone"
                  dataKey="attempts"
                  stroke="#7C3AED"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-[var(--text-muted)] mt-2">Detected cloning attempts (simulated)</p>
        </GlassPanel>
      </motion.div>

      {/* Recent Activity */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
      >
        <GlassPanel>
          <h3 className="text-lg font-semibold mb-4 tracking-tight">Recent Activity</h3>
          <div className="space-y-3">
            {recentTracks.map((track, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 + i * 0.1 }}
                className="flex items-center justify-between p-4 bg-[rgba(124,58,237,0.04)] rounded-2xl hover:bg-[rgba(124,58,237,0.08)] transition-colors group"
              >
                <div className="flex items-center gap-4">
                  <div className="w-11 h-11 gradient-primary rounded-xl flex items-center justify-center glow-lavender">
                    <Shield className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <p className="font-medium text-sm">{track.name}</p>
                    <p className="text-xs text-[var(--text-muted)]">{track.time}</p>
                  </div>
                </div>
                <Badge status={track.status as 'secure' | 'processing'}>
                  {track.status.toUpperCase()}
                </Badge>
              </motion.div>
            ))}
          </div>
        </GlassPanel>
      </motion.div>
    </div>
  );
}
