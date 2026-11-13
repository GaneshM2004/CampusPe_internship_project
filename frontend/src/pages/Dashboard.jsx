import React, { useState, useEffect } from 'react';
import api, { API_BASE } from '../api';
import { useAuth } from '../AuthContext';
import {
  ShieldAlert, Database, ListChecks, FileText, X, Activity,
  Download, AlertCircle, CheckCircle2, Clock, LogOut, User, Crown
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';
import { jsPDF } from 'jspdf';
import { toPng } from 'html-to-image';

export default function Dashboard() {
  const [records, setRecords] = useState([]);
  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const [modal, setModal] = useState({ isOpen: false, type: null, data: null, title: '' });

  const { auth, logout, isAdmin } = useAuth();

  const fetchRecords = async () => {
    try {
      const response = await api.get('/api/records');
      const sortedData = response.data.sort((a, b) => b.id - a.id);
      setRecords(sortedData);
    } catch (error) {
      console.error("Error fetching records:", error);
    }
  };

  useEffect(() => {
    fetchRecords();
    const interval = setInterval(fetchRecords, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    setLoading(true);
    try {
      await api.post('/api/records', { rawInput: inputText });
      setInputText("");
      fetchRecords();
    } catch (error) {
      alert("Failed to connect to the Java backend!");
    }
    setLoading(false);
  };

  const handleGetRecommendations = async (id) => {
    setActionLoading(`${id}-rec`);
    try {
      const response = await api.get(`/api/records/${id}/recommendations`);
      setModal({ isOpen: true, type: 'recommendations', data: response.data, title: `Action Plan: Record #${id}` });
    } catch (error) {
      alert("Error fetching recommendations.");
    }
    setActionLoading(null);
  };

  const handleGenerateReport = async (id) => {
    setActionLoading(`${id}-rep`);
    try {
      const response = await api.get(`/api/records/${id}/report`);
      setModal({ isOpen: true, type: 'report', data: response.data, title: `Official Audit Report: Record #${id}` });
    } catch (error) {
      alert("Error generating report.");
    }
    setActionLoading(null);
  };

  const closeModal = () => setModal({ isOpen: false, type: null, data: null, title: '' });

  const handleDownloadPDF = async () => {
    const reportElement = document.getElementById('modal-pdf-content');
    if (!reportElement) return;

    // Extract record ID from modal title (e.g., "Official Audit Report: Record #32")
    const recordIdMatch = modal.title.match(/#(\d+)/);
    const recordId = recordIdMatch ? recordIdMatch[1] : 'Unknown';
    const fileName = `Audit_Report_Record_${recordId}.pdf`;

    try {
      const dataUrl = await toPng(reportElement, {
        backgroundColor: '#ffffff',
        pixelRatio: 2 // for higher resolution
      });

      const imgWidth = reportElement.scrollWidth;
      const imgHeight = reportElement.scrollHeight;

      const pdfWidth = 210; // A4 width in mm
      const pdfHeight = (imgHeight * pdfWidth) / imgWidth;

      // Create a single-page PDF with a dynamic height to match the content perfectly.
      // This prevents the messy horizontal slicing of text across A4 page boundaries.
      const pdf = new jsPDF({
        orientation: 'p',
        unit: 'mm',
        format: [pdfWidth, pdfHeight]
      });

      pdf.addImage(dataUrl, 'PNG', 0, 0, pdfWidth, pdfHeight);

      pdf.save(fileName);
    } catch (error) {
      console.error('Error generating PDF:', error);
      alert(`Failed to generate PDF: ${error.message || error}`);
    }
  };

  // Analytics Math
  const totalRecords = records.length;
  const processingRecords = records.filter(r => r.status === 'PROCESSING').length;
  const completedRecords = records.filter(r => r.status === 'COMPLETED').length;
  const chartData = [
    { name: 'PROCESSING', count: processingRecords, fill: '#f59e0b' },
    { name: 'COMPLETED', count: completedRecords, fill: '#10b981' }
  ];

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-800 pb-20">

      {/* Top Navigation Bar */}
      <nav className="bg-white border-b border-slate-200 shadow-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-blue-100 p-2 rounded-lg">
              <ShieldAlert className="text-blue-600" size={28} />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900 leading-tight">DPDP Act Compliance Centre</h1>
              <p className="text-sm text-slate-500 font-medium">AI-Powered Data Protection Auditing</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Role Badge */}
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold ${isAdmin
                ? 'bg-gradient-to-r from-amber-100 to-orange-100 text-amber-800 border border-amber-200'
                : 'bg-gradient-to-r from-blue-100 to-indigo-100 text-blue-800 border border-blue-200'
              }`}>
              {isAdmin ? <Crown size={13} /> : <User size={13} />}
              {isAdmin ? 'Admin' : 'User'}: {auth?.username}
            </div>
            <button
              id="logout-button"
              onClick={logout}
              className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
              title="Sign out"
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-6 mt-8 space-y-8">

        {/* Analytics Section */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <Activity className="text-slate-700" size={20} />
            <h2 className="text-lg font-semibold text-slate-800">
              {isAdmin ? 'Organization-wide Compliance Overview' : 'My Compliance Overview'}
            </h2>
          </div>

          {/* KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col justify-center items-center hover:shadow-md transition-shadow">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Total Incidents</span>
              <span className="text-4xl font-extrabold text-slate-800">{totalRecords}</span>
            </div>
            <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl shadow-sm border border-amber-100 p-6 flex flex-col justify-center items-center hover:shadow-md transition-shadow">
              <span className="text-xs font-bold text-amber-600 uppercase tracking-wider mb-1 flex items-center gap-1"><Clock size={14} /> AI Processing</span>
              <span className="text-4xl font-extrabold text-amber-600">{processingRecords}</span>
            </div>
            <div className="bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl shadow-sm border border-emerald-100 p-6 flex flex-col justify-center items-center hover:shadow-md transition-shadow">
              <span className="text-xs font-bold text-emerald-600 uppercase tracking-wider mb-1 flex items-center gap-1"><CheckCircle2 size={14} /> Fully Audited</span>
              <span className="text-4xl font-extrabold text-emerald-600">{completedRecords}</span>
            </div>
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-72">
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 flex flex-col">
              <h3 className="text-sm font-semibold text-slate-500 text-center mb-4 uppercase tracking-wider">Status Distribution</h3>
              <div className="flex-grow">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
                    <Tooltip cursor={{ fill: '#f8fafc' }} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={60}>
                      {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 flex flex-col">
              <h3 className="text-sm font-semibold text-slate-500 text-center mb-4 uppercase tracking-wider">Compliance Ratio</h3>
              <div className="flex-grow">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={chartData} cx="50%" cy="50%" innerRadius={70} outerRadius={90} paddingAngle={5} dataKey="count" stroke="none">
                      {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </section>

        {/* Input Form — Hidden for Admin */}
        {!isAdmin && (
          <section className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="bg-slate-50 px-6 py-4 border-b border-slate-200">
              <h2 className="text-md font-semibold text-slate-800 flex items-center gap-2">
                <Database size={18} className="text-blue-600" /> Log New Data Activity or Incident
              </h2>
            </div>
            <form onSubmit={handleSubmit} className="p-6" id="incident-form">
              <textarea
                id="incident-input"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Describe the data processing activity, new software implementation, or security incident..."
                className="w-full h-28 p-4 bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all resize-y text-slate-700"
                disabled={loading}
              />
              <div className="mt-4 flex justify-end">
                <button
                  id="submit-incident"
                  type="submit"
                  disabled={loading || !inputText.trim()}
                  className={`px-6 py-2.5 rounded-lg font-semibold text-sm transition-all flex items-center gap-2 ${loading || !inputText.trim()
                      ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                      : 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm hover:shadow'
                    }`}
                >
                  {loading ? 'Analyzing...' : 'Analyze Compliance'}
                </button>
              </div>
            </form>
          </section>
        )}

        {/* Admin info banner */}
        {isAdmin && (
          <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl px-6 py-4 flex items-center gap-3">
            <Crown size={20} className="text-amber-600 shrink-0" />
            <p className="text-sm text-amber-800 font-medium">
              <span className="font-bold">Admin Mode</span> — You are viewing all records across the organization. Use the Export CSV button to download the full audit trail.
            </p>
          </div>
        )}

        {/* Audit Log */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-slate-800">Audit Log</h2>
            {/* Export CSV — Admin Only */}
            {isAdmin && (
              <button
                id="export-csv"
                onClick={() => {
                  // We need to send the token for the authenticated request
                  const token = localStorage.getItem('token');
                  fetch(`${API_BASE}/api/records/export`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                  })
                    .then(res => res.blob())
                    .then(blob => {
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = 'dpdp_audit_log.csv';
                      a.click();
                      window.URL.revokeObjectURL(url);
                    });
                }}
                className="px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded-lg text-sm font-semibold hover:bg-slate-50 transition-colors flex items-center gap-2 shadow-sm"
              >
                <Download size={16} /> Export CSV
              </button>
            )}
          </div>

          <div className="space-y-4">
            {records.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-xl border border-slate-200 border-dashed">
                <p className="text-slate-500 font-medium">
                  {isAdmin
                    ? 'No records in the system yet.'
                    : 'No records found. Submit an incident above to begin.'
                  }
                </p>
              </div>
            ) : records.map(record => (
              <div key={record.id} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden hover:border-slate-300 transition-colors">

                {/* Log Header */}
                <div className="px-6 py-3 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs font-bold text-slate-500">REF-ID: {record.id.toString().padStart(4, '0')}</span>
                    {/* Submitted By badge — visible for Admin */}
                    {isAdmin && record.submittedBy && (
                      <span className="px-2.5 py-0.5 bg-indigo-50 text-indigo-700 text-[11px] font-bold rounded-full border border-indigo-100 flex items-center gap-1">
                        <User size={10} />
                        Submitted By: {record.submittedBy}
                      </span>
                    )}
                  </div>
                  {record.status === 'PROCESSING' ? (
                    <span className="px-3 py-1 bg-amber-100 text-amber-700 text-xs font-bold rounded-full animate-pulse flex items-center gap-1">
                      <Clock size={12} /> PROCESSING AI
                    </span>
                  ) : (
                    <span className="px-3 py-1 bg-emerald-100 text-emerald-700 text-xs font-bold rounded-full flex items-center gap-1">
                      <CheckCircle2 size={12} /> AI REVIEWED
                    </span>
                  )}
                </div>

                <div className="p-6">
                  {/* Raw Input */}
                  <div className="mb-6">
                    <span className="text-[10px] font-bold tracking-widest text-slate-400 uppercase mb-2 block">Raw Input</span>
                    <p className="text-slate-700 text-sm leading-relaxed">{record.rawInput}</p>
                  </div>

                  {/* AI Summary Block */}
                  {record.professionalDescription && (
                    <div className="bg-slate-50 rounded-lg p-5 border border-slate-200">
                      <div className="flex gap-3">
                        <div className="mt-0.5"><ShieldAlert size={18} className="text-blue-600" /></div>
                        <div>
                          <span className="text-xs font-bold tracking-wider text-blue-800 uppercase mb-1 block">DPO Compliance Summary</span>
                          <p className="text-[10px] text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1 mb-2">
                            ⚠️ <strong>Informational only.</strong> This is AI-generated content and does not constitute legal advice. Consult a qualified Data Protection Officer or legal professional before making compliance decisions.
                          </p>
                          <p className="text-slate-800 text-sm leading-relaxed font-medium mb-5">{record.professionalDescription}</p>

                          {/* Action Buttons */}
                          <div className="flex flex-wrap gap-3">
                            <button
                              onClick={() => handleGetRecommendations(record.id)}
                              disabled={actionLoading !== null}
                              className="px-4 py-2 bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 rounded-md text-xs font-bold transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
                            >
                              <ListChecks size={14} className="text-amber-600" />
                              {actionLoading === `${record.id}-rec` ? 'Thinking...' : 'Get Recommendations'}
                            </button>

                            <button
                              onClick={() => handleGenerateReport(record.id)}
                              disabled={actionLoading !== null}
                              className="px-4 py-2 bg-slate-900 text-white hover:bg-slate-800 rounded-md text-xs font-bold transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
                            >
                              <FileText size={14} className="text-blue-400" />
                              {actionLoading === `${record.id}-rep` ? 'Generating...' : 'Full Audit Report'}
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>

      {/* Modern Modal Overlay */}
      {modal.isOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex justify-center items-center z-50 p-4 transition-opacity">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden transform transition-all">

            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                {modal.type === 'report' ? <FileText className="text-blue-600" /> : <ListChecks className="text-amber-600" />}
                {modal.title}
              </h2>
              <div className="flex items-center gap-3">
                {modal.type === 'report' && (
                  <button
                    onClick={handleDownloadPDF}
                    className="flex items-center gap-2 px-3 py-1.5 text-sm font-semibold text-slate-600 border border-slate-300 rounded-lg hover:bg-slate-100 hover:text-slate-800 transition-colors shadow-sm"
                  >
                    <Download size={16} /> Download PDF
                  </button>
                )}
                <button onClick={closeModal} className="text-slate-400 hover:text-slate-600 transition-colors p-1 rounded-md hover:bg-slate-200">
                  <X size={20} />
                </button>
              </div>
            </div>

            {/* Modal Content - Scrollable */}
            <div className="p-6 overflow-y-auto">
              {modal.type === 'recommendations' && modal.data && (
                <div className="space-y-4">
                  {modal.data.map((rec, index) => (
                    <div key={index} className={`p-4 rounded-lg border-l-4 bg-slate-50 ${rec.priority === 'High' ? 'border-l-red-500' : rec.priority === 'Medium' ? 'border-l-amber-500' : 'border-l-blue-500'}`}>
                      <div className="flex items-center gap-2 mb-1">
                        <AlertCircle size={14} className={rec.priority === 'High' ? 'text-red-500' : rec.priority === 'Medium' ? 'text-amber-500' : 'text-blue-500'} />
                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{rec.action_type} • Priority: {rec.priority}</span>
                      </div>
                      <p className="text-slate-700 text-sm font-medium">{rec.description}</p>
                    </div>
                  ))}
                </div>
              )}

              {modal.type === 'report' && modal.data && (
                <div id="modal-pdf-content" className="p-8 space-y-6 text-sm text-slate-700 bg-white font-sans w-full">
                  <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-2 text-xs text-amber-800">
                    ⚠️ <strong>Informational only.</strong> This report is AI-generated and does not constitute legal advice or a formal compliance assessment. Verify all findings with a qualified legal professional.
                  </div>
                  <div className="flex justify-between items-start border-b border-slate-200 pb-4 mb-4">
                    <div className="flex-1 pr-4">
                      <h3 className="text-xl font-bold text-slate-900 mb-2">{modal.data.title}</h3>
                      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                        Official Compliance Audit Report
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-xs text-slate-400 mb-1">Generated: {new Date().toLocaleDateString()}</p>
                      <p className="text-xs font-semibold text-indigo-700 bg-indigo-50 px-2 py-1 rounded border border-indigo-100">
                        Submitter: {(() => {
                          const match = modal.title.match(/#(\d+)/);
                          const current = records.find(r => r.id === (match ? parseInt(match[1]) : null));
                          return current?.submittedBy || 'Unknown';
                        })()}
                      </p>
                    </div>
                  </div>

                  <div>
                    <div className="bg-blue-50 text-blue-900 p-4 rounded-lg border border-blue-100 font-medium leading-relaxed">
                      {modal.data.executive_summary}
                    </div>
                  </div>

                  <div>
                    <h4 className="font-bold text-slate-800 border-b border-slate-200 pb-2 mb-3 uppercase tracking-wider text-xs">Overview</h4>
                    <p className="leading-relaxed">{modal.data.overview}</p>
                  </div>

                  <div>
                    <h4 className="font-bold text-slate-800 border-b border-slate-200 pb-2 mb-3 uppercase tracking-wider text-xs">Key Findings</h4>
                    <ul className="list-disc pl-5 space-y-2 text-slate-600">
                      {modal.data.top_items.map((item, i) => <li key={i} className="pl-1">{item}</li>)}
                    </ul>
                  </div>

                  <div>
                    <h4 className="font-bold text-slate-800 border-b border-slate-200 pb-2 mb-3 uppercase tracking-wider text-xs">Required Actions</h4>
                    <ol className="list-decimal pl-5 space-y-2 font-medium text-slate-800 bg-slate-50 p-4 rounded-lg">
                      {modal.data.recommendations.map((rec, i) => <li key={i} className="pl-2">{rec}</li>)}
                    </ol>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
