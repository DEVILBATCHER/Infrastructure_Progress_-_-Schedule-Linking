import React, { useState } from 'react';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import Upload from './components/Upload';

function App() {
  const [activeTab, setActiveTab] = useState('Dashboard');

  return (
    <Layout activeTab={activeTab} setActiveTab={setActiveTab}>
      {activeTab === 'Dashboard' ? <Dashboard /> : <Upload />}
    </Layout>
  );
}

export default App;
