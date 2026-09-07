import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { CheckIcon, XIcon } from './Icons';
import { approveMatch, rejectMatch } from '../api';
import ActivityDetails from './ActivityDetails';

const MatchResults = ({ result, onReset }) => {
  const [view, setView] = useState('results'); // 'results' | 'details'
  const [actionStatus, setActionStatus] = useState('idle'); // 'idle' | 'processing' | 'success'

  const handleApprove = async () => {
    setActionStatus('processing');
    try {
      await approveMatch(result.id, result.top_matches[0]?.activity_id);
      setActionStatus('success');
      setTimeout(() => setView('details'), 800);
    } catch (err) {
      alert("Approval failed: " + err.message);
      setActionStatus('idle');
    }
  };

  const handleReject = async () => {
    setActionStatus('processing');
    try {
      await rejectMatch(result.id);
      setActionStatus('success');
      setTimeout(() => onReset(), 800);
    } catch (err) {
      alert("Rejection failed: " + err.message);
      setActionStatus('idle');
    }
  };

  if (view === 'details') {
    return <ActivityDetails result={result} onReset={onReset} />;
  }

  const isError = result.status === 'error';
  const isNoMatch = result.status === 'no_match';

  return (
    <div className="max-w-3xl mx-auto py-12">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h2 className="text-3xl font-headline mb-2">AI Match Analysis</h2>
          <p className="text-site-grey font-mono text-sm">{result.input_report}</p>
        </div>
        <button onClick={onReset} className="text-xs font-mono text-site-grey hover:text-site-ink underline">
          Cancel Process
        </button>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {/* Extracted Note */}
        <div className="site-card p-6 border-l-4 border-l-site-accent-delayed">
          <p className="text-xs font-mono text-site-grey uppercase tracking-widest mb-2">Extracted Intelligence</p>
          <p className="text-site-ink leading-relaxed italic">"{result.extracted_note}"</p>
        </div>

        {/* Match Result */}
        <div className={`site-card p-8 ${isError || isNoMatch ? 'bg-gray-50' : ''}`}>
          <div className="flex justify-between items-start mb-8">
            <div>
              <p className="text-xs font-mono text-site-grey uppercase tracking-widest mb-1">Primary Match Candidate</p>
              {isError ? (
                <h3 className="text-2xl font-headline text-red-600">Analysis Error</h3>
              ) : isNoMatch ? (
                <h3 className="text-2xl font-headline text-site-grey">No Match Found</h3>
              ) : (
                <h3 className="text-2xl font-headline text-site-ink">
                  {result.top_matches[0]?.description || 'Unknown Asset'}
                </h3>
              )}
            </div>
            {!isError && !isNoMatch && (
              <div className="text-right">
                <p className="text-xs font-mono text-site-grey uppercase tracking-widest mb-1">Confidence</p>
                <span className={`text-xl font-mono font-bold ${
                  result.confidence === 'High' ? 'text-site-accent-active' :
                  result.confidence === 'Medium-Low' ? 'text-site-accent-delayed' : 'text-site-grey'
                }`}>
                  {result.confidence}
                </span>
              </div>
            )}
          </div>

          {!isError && !isNoMatch && result.top_matches.length > 1 && (
            <div className="mb-8">
              <p className="text-xs font-mono text-site-grey uppercase tracking-widest mb-3">Alternatives</p>
              <div className="space-y-2">
                {result.top_matches.slice(1).map((alt, i) => (
                  <div key={i} className="flex justify-between items-center p-3 rounded-site bg-gray-50 border border-site-grey text-sm">
                    <span className="font-medium">{alt.description}</span>
                    <span className="font-mono text-xs text-site-grey">Score: {alt.score}</span>
                  </div>
                ))}
              </div>
            </div>
            )}

          {/* Actions */}
          {!isError && !isNoMatch && (
            <div className="flex gap-4 pt-8 border-t border-site-grey">
              <button
                onClick={handleApprove}
                disabled={actionStatus !== 'idle'}
                className="flex-1 flex items-center justify-center gap-2 py-3 rounded-site bg-site-accent-active text-white font-medium hover:brightness-110 transition-all disabled:opacity-50"
              >
                {actionStatus === 'processing' ? 'Verifying...' : actionStatus === 'success' ? <CheckIcon /> : 'Approve Match'}
              </button>
              <button
                onClick={handleReject}
                disabled={actionStatus !== 'idle'}
                className="flex-1 flex items-center justify-center gap-2 py-3 rounded-site border border-site-grey text-site-ink font-medium hover:bg-gray-50 transition-all disabled:opacity-50"
              >
                {actionStatus === 'processing' ? 'Updating...' : actionStatus === 'success' ? <XIcon /> : 'Reject Match'}
              </button>
            </div>
          )}
          {(isError || isNoMatch) && (
            <button
              onClick={onReset}
              className="w-full py-3 rounded-site border border-site-grey text-site-ink font-medium hover:bg-gray-50 transition-all"
            >
              Return to Upload
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default MatchResults;
