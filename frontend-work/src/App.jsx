import React, { useState } from 'react';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import Upload from './components/Upload';

function App() {
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [dashboardAdjustments, setDashboardAdjustments] = useState({
    reportsProcessed: 0,
    autoMatched: 0,
    needsReview: 0,
    unmatched: 0,
  });
  const [newActivity, setNewActivity] = useState([]);

  const handleAnalysisComplete = (result) => {
    if (result.status === 'error') return;

    // Derive the activity-log status the same way the table displays it:
    // no_match -> unmatched; matched + High confidence -> matched;
    // matched + anything else (Medium-Low, Low) -> needs-review.
    const activityStatus =
      result.status === 'no_match'
        ? 'unmatched'
        : result.confidence === 'High'
        ? 'matched'
        : 'needs-review';

    setDashboardAdjustments((current) => ({
      ...current,
      reportsProcessed: current.reportsProcessed + 1,
      autoMatched: current.autoMatched + (activityStatus === 'matched' ? 1 : 0),
      needsReview: current.needsReview + (activityStatus === 'needs-review' ? 1 : 0),
      unmatched: current.unmatched + (activityStatus === 'unmatched' ? 1 : 0),
    }));

    const newEntry = {
      id: `ACT-NEW-${Date.now()}`,
      report: result.input_report,
      status: activityStatus,
      date: new Date().toISOString().slice(0, 10),
      confidence: result.confidence,
    };
    setNewActivity((current) => [newEntry, ...current]);
  };

  return (
    <Layout activeTab={activeTab} setActiveTab={setActiveTab}>
      {activeTab === 'Dashboard' ? (
        <Dashboard adjustments={dashboardAdjustments} newActivity={newActivity} />
      ) : (
        <Upload onAnalysisComplete={handleAnalysisComplete} />
      )}
    </Layout>
  );
}

export default App;
