import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ShieldAlert, Send, Clock, CheckCircle, Database, ListChecks, FileText, X, Activity, Download } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

function App() {
  const [records, setRecords] = useState([]);
  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const [modal, setModal] = useState({ isOpen: false, type: null, data: null, title: '' });

  const fetchRecords = async () => {
    try {
      const response = await axios.get('http://localhost:8080/api/records');
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
      await axios.post('http://localhost:8080/api/records', { rawInput: inputText });
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
      const response = await axios.get(`http://localhost:8080/api/records/${id}/recommendations`);
      setModal({ isOpen: true, type: 'recommendations', data: response.data, title: `Action Plan: Record #${id}` });
    } catch (error) {
      alert("Error fetching recommendations.");
    }
    setActionLoading(null);
  };

  const handleGenerateReport = async (id) => {
    setActionLoading(`${id}-rep`);
    try {
      const response = await axios.get(`http://localhost:8080/api/records/${id}/report`);
      setModal({ isOpen: true, type: 'report', data: response.data, title: `Official Audit Report: Record #${id}` });
    } catch (error) {
      alert("Error generating report.");
    }
    setActionLoading(null);
  };

  const closeModal = () => setModal({ isOpen: false, type: null, data: null, title: '' });

  // --- ANALYTICS DATA CALCULATION ---
  const totalRecords = records.length;
  const processingRecords = records.filter(r => r.status === 'PROCESSING').length;
  const completedRecords = records.filter(r => r.status === 'COMPLETED').length;

  const chartData = [
    { name: 'PROCESSING', count: processingRecords, fill: '#f59e0b' }, // Amber
    { name: 'COMPLETED', count: completedRecords, fill: '#10b981' }  // Green
  ];

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '20px', fontFamily: 'sans-serif' }}>
      
      {/* Header */}
      <div className="header-container" style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '30px', borderBottom: '2px solid #eee', paddingBottom: '20px' }}>
        <ShieldAlert size={40} color="#2563eb" />
        <div>
          <h1 style={{ margin: 0, color: '#1e293b' }}>DPDP Act Compliance Centre</h1>
          <p style={{ margin: 0, color: '#64748b' }}>AI-Powered Data Protection Auditing</p>
        </div>
      </div>

      {/* --- NEW: ANALYTICS DASHBOARD --- */}
      <div style={{ marginBottom: '40px' }}>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#0f172a' }}><Activity size={24}/> Compliance Overview</h2>
        
        {/* KPI Cards */}
        <div style={{ display: 'flex', gap: '15px', marginBottom: '20px', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '200px', padding: '20px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', textAlign: 'center' }}>
            <h3 style={{ margin: 0, color: '#64748b', fontSize: '14px', textTransform: 'uppercase' }}>Total Incidents</h3>
            <p style={{ margin: '10px 0 0 0', fontSize: '32px', fontWeight: 'bold', color: '#0f172a' }}>{totalRecords}</p>
          </div>
          <div style={{ flex: 1, minWidth: '200px', padding: '20px', backgroundColor: '#fffbeb', borderRadius: '8px', border: '1px solid #fef3c7', textAlign: 'center' }}>
            <h3 style={{ margin: 0, color: '#d97706', fontSize: '14px', textTransform: 'uppercase' }}>AI Processing</h3>
            <p style={{ margin: '10px 0 0 0', fontSize: '32px', fontWeight: 'bold', color: '#b45309' }}>{processingRecords}</p>
          </div>
          <div style={{ flex: 1, minWidth: '200px', padding: '20px', backgroundColor: '#f0fdf4', borderRadius: '8px', border: '1px solid #dcfce3', textAlign: 'center' }}>
            <h3 style={{ margin: 0, color: '#16a34a', fontSize: '14px', textTransform: 'uppercase' }}>Fully Audited</h3>
            <p style={{ margin: '10px 0 0 0', fontSize: '32px', fontWeight: 'bold', color: '#15803d' }}>{completedRecords}</p>
          </div>
        </div>

        {/* Charts Container */}
        <div className="action-buttons" style={{ display: 'flex', gap: '20px', height: '250px' }}>
          {/* Bar Chart */}
          <div style={{ flex: 1, minWidth: '300px', backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <h4 style={{ marginTop: 0, textAlign: 'center', color: '#475569' }}>Status Distribution</h4>
            <ResponsiveContainer width="100%" height="80%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{fontSize: 12}} />
                <YAxis allowDecimals={false} tick={{fontSize: 12}} />
                <Tooltip cursor={{fill: '#f1f5f9'}} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Pie Chart */}
          <div style={{ flex: 1, minWidth: '300px', backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <h4 style={{ marginTop: 0, textAlign: 'center', color: '#475569' }}>Compliance Ratio</h4>
            <ResponsiveContainer width="100%" height="80%">
              <PieChart>
                <Pie data={chartData} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="count">
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Input Form */}
      <div style={{ backgroundColor: '#f8fafc', padding: '20px', borderRadius: '8px', marginBottom: '30px', border: '1px solid #e2e8f0' }}>
        <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Database size={20}/> Log New Data Activity or Incident
        </h3>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <textarea 
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Describe the data processing activity, new software, or security incident..."
            style={{ width: '100%', height: '100px', padding: '10px', borderRadius: '4px', border: '1px solid #cbd5e1', resize: 'vertical' }}
            disabled={loading}
          />
          <button 
            type="submit" 
            disabled={loading || !inputText.trim()}
            style={{ alignSelf: 'flex-end', padding: '10px 20px', backgroundColor: '#2563eb', color: 'white', border: 'none', borderRadius: '4px', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 'bold' }}
          >
            {loading ? 'Sending...' : 'Analyze Compliance'}
          </button>
        </form>
      </div>

      {/* Audit Log Header with CSV Export */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
        <h2 style={{ margin: 0 }}>Audit Log</h2>
        <button 
          onClick={() => window.open('http://localhost:8080/api/records/export')}
          style={{ padding: '8px 15px', backgroundColor: '#10b981', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 'bold' }}
        >
          <Download size={16} /> Export to CSV
        </button>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        {records.length === 0 ? <p>No records found.</p> : records.map(record => (
            <div key={record.id} style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '15px', backgroundColor: 'white' }}>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '10px', marginBottom: '10px' }}>
                <span style={{ fontWeight: 'bold', color: '#475569' }}>Record #{record.id}</span>
                {record.status === 'PROCESSING' ? (
                  <span style={{ color: '#d97706', backgroundColor: '#fef3c7', padding: '4px 8px', borderRadius: '12px', fontSize: '12px', fontWeight: 'bold' }}>PROCESSING AI...</span>
                ) : (
                  <span style={{ color: '#16a34a', backgroundColor: '#dcfce3', padding: '4px 8px', borderRadius: '12px', fontSize: '12px', fontWeight: 'bold' }}>AI REVIEWED</span>
                )}
              </div>

              <div style={{ marginBottom: '15px' }}>
                <strong style={{ display: 'block', fontSize: '12px', color: '#64748b' }}>RAW INPUT</strong>
                <p style={{ margin: '5px 0 0 0', color: '#334155' }}>{record.rawInput}</p>
              </div>

              {record.professionalDescription && (
                <div style={{ backgroundColor: '#f0fdf4', padding: '10px', borderRadius: '4px', borderLeft: '4px solid #16a34a' }}>
                  <strong style={{ display: 'block', fontSize: '12px', color: '#166534' }}>DPO COMPLIANCE SUMMARY</strong>
                  <p style={{ margin: '5px 0 0 0', color: '#166534' }}>{record.professionalDescription}</p>
                  
                  <div className="action-buttons" style={{ display: 'flex', gap: '10px', marginTop: '15px' }}>
                    <button 
                      onClick={() => handleGetRecommendations(record.id)}
                      disabled={actionLoading !== null}
                      style={{ padding: '8px 12px', backgroundColor: 'white', color: '#0f172a', border: '1px solid #cbd5e1', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px', fontSize: '13px', fontWeight: 'bold' }}
                    >
                      <ListChecks size={16} color="#d97706" /> 
                      {actionLoading === `${record.id}-rec` ? 'Thinking...' : 'Get Recommendations'}
                    </button>
                    
                    <button 
                      onClick={() => handleGenerateReport(record.id)}
                      disabled={actionLoading !== null}
                      style={{ padding: '8px 12px', backgroundColor: '#0f172a', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px', fontSize: '13px', fontWeight: 'bold' }}
                    >
                      <FileText size={16} color="#38bdf8" /> 
                      {actionLoading === `${record.id}-rep` ? 'Generating...' : 'Full Audit Report'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
      </div>

      {/* --- MODAL POPUP UI --- */}
      {modal.isOpen && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000, padding: '20px', boxSizing: 'border-box' }}>
          <div className="modal-content" style={{ backgroundColor: 'white', borderRadius: '8px', padding: '25px', width: '100%', maxWidth: '700px', maxHeight: '85vh', overflowY: 'auto', position: 'relative' }}>
            <button onClick={closeModal} style={{ position: 'absolute', top: '15px', right: '15px', background: 'none', border: 'none', cursor: 'pointer' }}><X size={24} color="#64748b" /></button>
            <h2 style={{ marginTop: 0, color: '#0f172a', borderBottom: '2px solid #f1f5f9', paddingBottom: '10px' }}>{modal.title}</h2>
            
            {modal.type === 'recommendations' && modal.data && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                {modal.data.map((rec, index) => (
                  <div key={index} style={{ borderLeft: `4px solid ${rec.priority === 'High' ? '#ef4444' : rec.priority === 'Medium' ? '#f59e0b' : '#3b82f6'}`, paddingLeft: '15px' }}>
                    <span style={{ fontSize: '12px', fontWeight: 'bold', color: '#64748b', textTransform: 'uppercase' }}>{rec.action_type} • PRIORITY: {rec.priority}</span>
                    <p style={{ margin: '5px 0 0 0', color: '#334155' }}>{rec.description}</p>
                  </div>
                ))}
              </div>
            )}

            {modal.type === 'report' && modal.data && (
              <div>
                <h3 style={{ color: '#1e293b' }}>{modal.data.title}</h3>
                <p style={{ fontStyle: 'italic', color: '#475569', backgroundColor: '#f8fafc', padding: '10px', borderRadius: '4px' }}>{modal.data.executive_summary}</p>
                <h4 style={{ color: '#334155', borderBottom: '1px solid #e2e8f0', paddingBottom: '5px' }}>Overview</h4>
                <p style={{ color: '#475569' }}>{modal.data.overview}</p>
                <h4 style={{ color: '#334155', borderBottom: '1px solid #e2e8f0', paddingBottom: '5px' }}>Key Findings (Top Items)</h4>
                <ul style={{ color: '#475569' }}>
                  {modal.data.top_items.map((item, i) => <li key={i} style={{ marginBottom: '5px' }}>{item}</li>)}
                </ul>
                <h4 style={{ color: '#334155', borderBottom: '1px solid #e2e8f0', paddingBottom: '5px' }}>Required Actions</h4>
                <ol style={{ color: '#475569' }}>
                  {modal.data.recommendations.map((rec, i) => <li key={i} style={{ marginBottom: '5px' }}>{rec}</li>)}
                </ol>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;