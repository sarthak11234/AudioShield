'use client';

import { motion } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line, XAxis, YAxis } from 'recharts';
import { Shield, Upload, AlertTriangle, CheckCircle } from 'lucide-react';
import { GlassPanel, Button, Badge } from '@/components/ui';

const securityData = [
  { name: 'Secured', value: 92, color: '#00B894' },
  { name: 'Vulnerable', value: 8, color: '#FF7675' },
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

export default function Dashboard() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Command Center</h1>
          <p className="text-white/60 mt-1">Monitor your audio protection status</p>
        </div>
        <Button>
          <Upload className="w-4 h-4 mr-2 inline" />
          Protect New Track
        </Button>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Security Health - Hero Widget */}
        <GlassPanel className="col-span-2" hover>
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
                <span className="text-4xl font-bold">92%</span>
                <span className="text-sm text-white/60">Secured</span>
              </div>
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold mb-2">Catalog Security</h2>
              <p className="text-white/60 mb-4">Your audio library is well protected</p>
              <div className="flex gap-4">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-[#00B894]" />
                  <span>12 Protected this week</span>
                </div>
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-[#FF7675]" />
                  <span>3 Tracks vulnerable</span>
                </div>
              </div>
            </div>
          </div>
        </GlassPanel>

        {/* AI Threat Monitor */}
        <GlassPanel hover>
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-[#00CEC9]" />
            AI Landscape Monitor
          </h3>
          <div className="h-32">
            <ResponsiveContainer>
              <LineChart data={threatData}>
                <XAxis dataKey="name" stroke="#ffffff40" fontSize={10} />
                <YAxis stroke="#ffffff40" fontSize={10} />
                <Line
                  type="monotone"
                  dataKey="attempts"
                  stroke="#00CEC9"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-white/40 mt-2">Detected cloning attempts (simulated)</p>
        </GlassPanel>
      </div>

      {/* Recent Activity */}
      <GlassPanel>
        <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
        <div className="space-y-3">
          {recentTracks.map((track, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="flex items-center justify-between p-4 bg-white/5 rounded-xl"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 bg-gradient-to-br from-[#6C5CE7] to-[#00CEC9] rounded-lg flex items-center justify-center">
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <p className="font-medium">{track.name}</p>
                  <p className="text-sm text-white/40">{track.time}</p>
                </div>
              </div>
              <Badge status={track.status as 'secure' | 'processing'}>
                {track.status.toUpperCase()}
              </Badge>
            </motion.div>
          ))}
        </div>
      </GlassPanel>
    </div>
  );
}
