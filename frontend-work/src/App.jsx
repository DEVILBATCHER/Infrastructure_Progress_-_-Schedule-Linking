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

  const handleAnalysisComplete = (result) => {
    if (result.status === 'error') return;

    setDashboardAdjustments((current) => ({
      ...current,
      reportsProcessed: current.reportsProcessed + 1,
      autoMatched: current.autoMatched + (result.status === 'matched' ? 1 : 0),
      needsReview: current.needsReview + (result.status === 'needs-review' ? 1 : 0),
      unmatched: current.unmatched + (result.status === 'no_match' ? 1 : 0),
    }));
  };

  return (
    <Layout activeTab={activeTab} setActiveTab={setActiveTab}>
      {activeTab === 'Dashboard' ? (
        <Dashboard adjustments={dashboardAdjustments} />
      ) : (
        <Upload onAnalysisComplete={handleAnalysisComplete} />
      )}
    </Layout>
  );
}

export default App;
