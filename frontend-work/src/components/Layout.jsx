import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CompassRose, FolderIcon } from './Icons';

const Layout = ({ children, activeTab, setActiveTab }) => {
  return (
    <div className="min-h-screen bg-site-bg text-site-ink font-body">
      <nav className="border-b border-site-grey px-8 py-6 flex justify-between items-center bg-white">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-site-ink text-white rounded-site">
            <CompassRose className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-headline tracking-tight leading-none">INFRA<span className="font-light">TRACK</span></h1>
            <p className="text-[10px] font-mono text-site-grey uppercase tracking-widest">Site Print System v1.0</p>
          </div>
        </div>

        <div className="flex gap-1">
          {['Dashboard', 'Upload'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium transition-all duration-200 rounded-site ${
                activeTab === tab
                  ? 'bg-site-ink text-white shadow-sm'
                  : 'text-site-ink hover:bg-gray-100'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </nav>

      <main className="p-8 max-w-7xl mx-auto">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
          >
            {children}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
};

export default Layout;
