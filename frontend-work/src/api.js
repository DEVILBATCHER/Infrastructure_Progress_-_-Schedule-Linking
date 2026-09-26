const USE_MOCK = true;

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const simulateNetwork = async () => {
  const delay = Math.floor(Math.random() * (900 - 500 + 1)) + 500;
  await sleep(delay);

  if (Math.random() < 0.1) {
    throw new Error("Simulated network error occurred while fetching data.");
  }
};

const MOCK_DATA = {
  dashboard: {
    reportsProcessed: 1248,
    autoMatched: 1102,
    needsReview: 84,
    unmatched: 62,
    matchingAccuracy: 88.4,
    recentActivity: [
      // Renamed from the demo-file names on purpose - these must NOT match
      // DEMO_FILE_MAP keys below, so a live upload during a presentation
      // clearly reads as a new row, not a pre-existing duplicate.
      { id: 'ACT-001', report: 'Northgate_Substation_Report.pdf', status: 'matched', date: '2026-09-07', confidence: 'High' },
      { id: 'ACT-002', report: 'Turbine_Bay_Inspection.csv', status: 'needs-review', date: '2026-09-07', confidence: 'Medium' },
      { id: 'ACT-003', report: 'Corridor_Survey_Draft.json', status: 'unmatched', date: '2026-09-06', confidence: 'Low' },
      { id: 'ACT-004', report: 'External_Audit_Final.pdf', status: 'matched', date: '2026-09-06', confidence: 'High' },
      { id: 'ACT-005', report: 'Inventory_Log_Sep.xlsx', status: 'matched', date: '2026-09-05', confidence: 'High' },
    ],
    scheduleProgress: [
      { name: 'Mon', value: 45 },
      { name: 'Tue', value: 52 },
      { name: 'Wed', value: 38 },
      { name: 'Thu', value: 65 },
      { name: 'Fri', value: 48 },
      { name: 'Sat', value: 20 },
      { name: 'Sun', value: 10 },
    ]
  },
  matchResults: [
    {
      id: 'res-1',
      status: 'matched',
      input_report: 'Q3_Infrastructure_Audit.pdf',
      top_matches: [{ activity_id: 'P101', description: 'Primary Power Distribution Unit - North Sector', score: 0.94 }],
      confidence: 'High',
      extracted_note: 'Detected consistent naming convention with P101 asset registry.'
    },
    {
      id: 'res-2',
      status: 'matched',
      input_report: 'Facility_Scan_B2.csv',
      top_matches: [
        { activity_id: 'P202', description: 'Secondary Ventilation Shaft B2', score: 0.62 },
        { activity_id: 'P205', description: 'Ventilation Shaft B1', score: 0.58 }
      ],
      confidence: 'Medium-Low',
      extracted_note: 'Partial match found; description contains ambiguous terminology.'
    },
    {
      id: 'res-3',
      status: 'no_match',
      input_report: 'Site_Print_Mapping_V1.json',
      top_matches: [],
      confidence: 'Low',
      extracted_note: 'No corresponding activity IDs found in the master registry.'
    },
    {
      id: 'res-4',
      status: 'error',
      input_report: 'Corrupt_File.pdf',
      top_matches: [],
      confidence: 'N/A',
      extracted_note: 'Unable to parse document structure.'
    },
    {
      id: 'res-5',
      status: 'matched',
      input_report: 'Detailed_Technical_Specification_Long_Text_Case.pdf',
      top_matches: [{ activity_id: 'P505', description: 'Ultra-High Capacity Thermal Management System with Integrated Redundancy and Multi-Phase Cooling Loops', score: 0.88 }],
      confidence: 'High',
      extracted_note: 'Extracted an unusually long description but matched perfectly with asset P505 registry details.'
    },
    {
      id: 'res-6',
      status: 'matched',
      input_report: 'Empty_Matches_Test.pdf',
      top_matches: [],
      confidence: 'Low',
      extracted_note: 'Parsing succeeded but result set is empty despite matched status.'
    }
  ]
};

// Filenames listed here always return the same fixed result, with the
// realistic delay but WITHOUT the random 10% network-error roll -
// use these during a live presentation to guarantee specific outcomes.
// Rename real files on disk to match these names exactly (case-sensitive)
// before demoing. Any other filename still gets full random behavior.
const DEMO_FILE_MAP = {
  "Q3_Infrastructure_Audit.pdf": 'res-1',   // guaranteed High confidence
  "Facility_Scan_B2.csv": 'res-2',           // guaranteed Medium-Low, shows alternatives
  "Site_Print_Mapping_V1.json": 'res-3',     // guaranteed no_match
  "Corrupt_File.pdf": 'res-4',               // guaranteed error state (returned gracefully, not thrown)
};

export const fetchDashboardStats = async () => {
  if (USE_MOCK) {
    await simulateNetwork();
    return MOCK_DATA.dashboard;
  }
  // Real API call would go here
  throw new Error("Real API not implemented");
};

export const uploadReport = async (file) => {
  if (USE_MOCK) {
    const demoResultId = DEMO_FILE_MAP[file.name];

    if (demoResultId) {
      // Demo files: realistic delay only, no random error - guaranteed outcome
      const delay = Math.floor(Math.random() * (900 - 500 + 1)) + 500;
      await sleep(delay);
      return MOCK_DATA.matchResults.find(r => r.id === demoResultId);
    }

    // Any other filename: full random behavior, including the ~10% error
    // chance, so uploading something else still shows realistic variation.
    await simulateNetwork();
    const randomIndex = Math.floor(Math.random() * MOCK_DATA.matchResults.length);
    return MOCK_DATA.matchResults[randomIndex];
  }
  throw new Error("Real API not implemented");
};

export const approveMatch = async (resultId, activityId) => {
  if (USE_MOCK) {
    await simulateNetwork();
    return { success: true };
  }
  throw new Error("Real API not implemented");
};

export const rejectMatch = async (resultId) => {
  if (USE_MOCK) {
    await simulateNetwork();
    return { success: true };
  }
  throw new Error("Real API not implemented");
};