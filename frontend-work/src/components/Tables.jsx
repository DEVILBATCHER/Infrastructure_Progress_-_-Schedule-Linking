import React from 'react';
import { CheckIcon, XIcon } from './Icons';

export const ActivityTable = ({ activity }) => {
  return (
    <div className="overflow-hidden rounded-site border-hairline border-site-grey bg-white">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="bg-gray-50 border-b border-site-grey">
            <th className="px-6 py-3 text-xs font-mono text-site-grey uppercase tracking-wider">ID</th>
            <th className="px-6 py-3 text-xs font-mono text-site-grey uppercase tracking-wider">Report</th>
            <th className="px-6 py-3 text-xs font-mono text-site-grey uppercase tracking-wider">Status</th>
            <th className="px-6 py-3 text-xs font-mono text-site-grey uppercase tracking-wider">Confidence</th>
            <th className="px-6 py-3 text-xs font-mono text-site-grey uppercase tracking-wider">Date</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-site-grey">
          {activity.map((item) => (
            <tr key={item.id} className="hover:bg-gray-50 transition-colors">
              <td className="px-6 py-4 text-sm font-mono">{item.id}</td>
              <td className="px-6 py-4 text-sm font-medium">{item.report}</td>
              <td className="px-6 py-4 text-sm">
                <span className={`px-2 py-1 rounded text-[10px] font-mono uppercase ${
                  item.status === 'matched' ? 'bg-green-100 text-site-accent-active' :
                  item.status === 'needs-review' ? 'bg-orange-100 text-site-accent-delayed' :
                  'bg-gray-100 text-gray-500'
                }`}>
                  {item.status.replace('-', ' ')}
                </span>
              </td>
              <td className="px-6 py-4 text-sm font-mono">{item.confidence}</td>
              <td className="px-6 py-4 text-sm text-site-grey font-mono">{item.date}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
