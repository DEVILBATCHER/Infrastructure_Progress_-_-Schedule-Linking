import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { fetchDashboardStats } from '../api';
import { ScheduleChart } from './Charts';
import { ActivityTable } from './Tables';
import { SectionCut } from './Icons';

const StatCard = ({ label, value, subtext, colorClass = "text-site-ink" }) => (
  <div className="site-card p-6 flex flex-col justify-between h-full">
    <p className="text-xs font-mono text-site-grey uppercase tracking-wider mb-2">{label}</p>
    <div className="flex items-baseline gap-2">
      <span className={`text-3xl font-headline ${colorClass}`}>{value}</span>
      {subtext && <span className="text-xs font-mono text-site-grey">{subtext}</span>}
    </div>
  </div>
);

const Dashboard = ({ adjustments, newActivity = [] }) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardStats().then(data => {
      setStats(data);
      setLoading(false);
    }).catch(err => {
      console.error(err);
      setLoading(false);
    });
  }, []);

  const displayedStats = stats && {
    ...stats,
    reportsProcessed: stats.reportsProcessed + adjustments.reportsProcessed,
    autoMatched: stats.autoMatched + adjustments.autoMatched,
    needsReview: stats.needsReview + adjustments.needsReview,
    unmatched: stats.unmatched + adjustments.unmatched,
  };

  // Newly uploaded entries appear first, then the original mock history,
  // capped to the last 5 so the table doesn't grow unbounded during a demo.
  const combinedActivity = stats
    ? [...newActivity, ...stats.recentActivity].slice(0, 5)
    : [];

  if (loading) return <div className="flex items-center justify-center h-64 text-site-grey font-mono">Loading Blueprint...</div>;
  if (!stats) return <div className="text-center p-12 text-red-500">Failed to load dashboard data.</div>;

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="relative p-12 rounded-site bg-white border-hairline border-site-grey overflow-hidden">
        <div className="absolute inset-0 blueprint-grid opacity-100" />

        <div className="relative z-10 flex flex-col md:flex-row justify-between items-center gap-8">
          <div className="max-w-md">
            <div className="flex items-center gap-2 mb-4">
              <SectionCut className="w-5 h-5 text-site-accent-delayed" />
              <span className="text-xs font-mono text-site-grey uppercase tracking-widest">System Accuracy Index</span>
            </div>
            <h2 className="text-5xl font-headline mb-4 leading-tight">Matching Accuracy<br/>Verification</h2>
            <p className="text-site-grey leading-relaxed">
              Comparing extracted report data against master infrastructure registry.
              The current index reflects the percentage of auto-matched assets with high confidence.
            </p>
          </div>

          <div className="relative flex flex-col items-center">
            <div className="text-center mb-6">
              <motion.div
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.8, ease: "easeOut" }}
                className="text-8xl font-headline text-site-ink tracking-tighter"
              >
                {Math.round(stats.matchingAccuracy)}%
              </motion.div>
              <div className="font-mono text-xs text-site-grey uppercase tracking-widest">Confidence Score</div>
            </div>

            {/* Hero Progress Element */}
            <div className="w-64 h-3 bg-gray-100 rounded-full overflow-hidden border border-site-grey">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${stats.matchingAccuracy}%` }}
                transition={{ duration: 1.5, ease: "easeInOut", delay: 0.5 }}
                className="h-full rounded-full bg-gradient-to-r from-site-accent-delayed to-[#E88C5E]"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Grid Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard label="Reports Processed" value={displayedStats.reportsProcessed} />
        <StatCard label="Auto Matched" value={displayedStats.autoMatched} colorClass="text-site-accent-active" />
        <StatCard label="Needs Review" value={displayedStats.needsReview} colorClass="text-site-accent-delayed" />
        <StatCard label="Unmatched" value={displayedStats.unmatched} />
      </div>

      {/* Bottom Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
        <div className="lg:col-span-2 space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-xl font-headline">Recent Activity Log</h3>
            <span className="text-xs font-mono text-site-grey">Last 5 entries</span>
          </div>
          <ActivityTable activity={combinedActivity} />
        </div>

        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-xl font-headline">Schedule Progress</h3>
            <span className="text-xs font-mono text-site-grey">Weekly trend</span>
          </div>
          <div className="site-card p-6">
            <ScheduleChart data={stats.scheduleProgress} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
