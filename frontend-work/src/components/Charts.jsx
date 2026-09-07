import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export const ScheduleChart = ({ data }) => {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#1C2B45" stopOpacity={0.1}/>
              <stop offset="95%" stopColor="#1C2B45" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#D1D5DB" />
          <XAxis
            dataKey="name"
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#AAB2B9', fontSize: 12, fontFamily: 'JetBrains Mono' }}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#AAB2B9', fontSize: 12, fontFamily: 'JetBrains Mono' }}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#fff', border: '1px solid #AAB2B9', borderRadius: '8px', fontSize: '12px', fontFamily: 'JetBrains Mono' }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#1C2B45"
            fillOpacity={1}
            fill="url(#colorValue)"
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
