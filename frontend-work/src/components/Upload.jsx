import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { FolderIcon, DimensionArrows } from './Icons';
import { uploadReport } from '../api';
import MatchResults from './MatchResults';

const Upload = () => {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle'); // 'idle' | 'processing' | 'result'
  const [result, setResult] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return;
    setStatus('processing');
    try {
      const res = await uploadReport(file);
      setResult(res);
      setStatus('result');
    } catch (err) {
      alert("Upload failed: " + err.message);
      setStatus('idle');
    }
  };

  if (status === 'result') {
    return <MatchResults result={result} onReset={() => { setStatus('idle'); setFile(null); }} />;
  }

  return (
    <div className="max-w-2xl mx-auto py-12">
      <div className="text-center mb-12">
        <div className="inline-block p-3 bg-site-bg rounded-site border border-site-grey mb-4">
          <FolderIcon className="w-8 h-8 text-site-ink" />
        </div>
        <h2 className="text-4xl font-headline mb-4">Report Ingestion</h2>
        <p className="text-site-grey leading-relaxed">
          Upload your infrastructure report to begin the AI matching process.<br/>
          Supported formats: .pdf, .csv, .json
        </p>
      </div>

      <div className={`relative group site-card p-12 text-center border-dashed border-2 transition-all duration-300 ${
        status === 'processing' ? 'bg-gray-50 pointer-events-none' : 'hover:border-site-ink'
      }`}>
        {status === 'idle' ? (
          <>
            <div className="flex flex-col items-center">
              <div className="mb-6 p-4 rounded-full bg-gray-50 text-site-grey group-hover:text-site-ink transition-colors">
                <DimensionArrows className="w-10 h-10" />
              </div>
              <input
                type="file"
                id="file-upload"
                className="hidden"
                onChange={handleFileChange}
              />
              <label
                htmlFor="file-upload"
                className="cursor-pointer px-6 py-3 rounded-site bg-site-ink text-white font-medium hover:bg-opacity-90 transition-all mb-4 inline-block"
              >
                {file ? 'Change File' : 'Select Report'}
              </label>
              {file && (
                <p className="text-sm font-mono text-site-ink">
                  {file.name} <span className="text-site-grey">({(file.size / 1024).toFixed(1)} KB)</span>
                </p>
              )}
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center py-8">
            <div className="w-12 h-12 border-4 border-site-grey border-t-site-accent-delayed rounded-full animate-spin mb-4" />
            <p className="font-mono text-sm animate-pulse">Processing blueprint data...</p>
            <p className="text-xs text-site-grey mt-2">Matching extracted entities with asset registry</p>
          </div>
        )}
      </div>

      {status === 'idle' && file && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-8 flex justify-center"
        >
          <button
            onClick={handleUpload}
            className="px-8 py-3 rounded-site bg-site-accent-delayed text-white font-medium hover:brightness-110 transition-all shadow-sm"
          >
            Begin Analysis
          </button>
        </motion.div>
      )}
    </div>
  );
};

export default Upload;
