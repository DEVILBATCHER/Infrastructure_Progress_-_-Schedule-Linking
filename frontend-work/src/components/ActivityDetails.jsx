import React from 'react';
import { motion } from 'framer-motion';
import { CheckIcon, DimensionArrows } from './Icons';

const ActivityDetails = ({ result, onReset }) => {
  return (
    <div className="max-w-3xl mx-auto py-12">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="site-card p-12 text-center relative overflow-hidden"
      >
        <div className="absolute top-0 left-0 w-full h-2 bg-site-accent-active" />

        <div className="flex justify-center mb-6">
          <div className="p-4 bg-green-50 text-site-accent-active rounded-full">
            <CheckIcon className="w-12 h-12" />
          </div>
        </div>

        <h2 className="text-3xl font-headline mb-2">Match Confirmed</h2>
        <p className="text-site-grey font-mono text-sm mb-8">Registry Entry Updated Successfully</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 text-left mb-12">
          <div className="p-6 bg-gray-50 rounded-site border border-site-grey">
            <p className="text-xs font-mono text-site-grey uppercase tracking-widest mb-2">Matched Asset</p>
            <p className="text-xl font-headline">{result.top_matches[0]?.description}</p>
            <p className="text-sm font-mono mt-1">ID: {result.top_matches[0]?.activity_id}</p>
          </div>

          <div className="p-6 bg-gray-50 rounded-site border border-site-grey">
            <p className="text-xs font-mono text-site-grey uppercase tracking-widest mb-2">Source Document</p>
            <p className="text-xl font-headline">{result.input_report}</p>
            <p className="text-sm font-mono mt-1">Confidence: {result.confidence}</p>
          </div>
        </div>

        <button
          onClick={onReset}
          className="px-8 py-3 rounded-site border border-site-grey text-site-ink font-medium hover:bg-gray-50 transition-all"
        >
          Process New Report
        </button>
      </motion.div>
    </div>
  );
};

export default ActivityDetails;
