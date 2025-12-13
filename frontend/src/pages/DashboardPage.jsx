import React, { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import api from '../lib/api';
import UploadComponent from '../components/UploadComponent';
import CountdownTimer from '../components/CountdownTimer';
import '../styles/dashboard.css';
import zipIcon from '../../icons/zip.png';
import loadingSpinner from '../../icons/loading-animation.gif';

function DashboardPage() {
  const { user, logout } = useAuth();
  const [tp, setTp] = useState(null);
  const [error, setError] = useState('');
  const [effectiveEndTime, setEffectiveEndTime] = useState(null);
  // Hardcoded TP ID for now.
  const TP_ID = 1;

  useEffect(() => {
    const fetchTpInfo = async () => {
      try {
        const response = await api.get(`/api/tp/${TP_ID}`);
        setTp(response.data);

        // Per-student session window.
        const sessionKey = `tp_session_${TP_ID}_${user.student_id}`;
        const existing = localStorage.getItem(sessionKey);
        if (existing) {
          try {
            const parsed = JSON.parse(existing);
            if (parsed.end) {
              setEffectiveEndTime(parsed.end);
              return;
            }
          } catch (_) {
            // Fall through and recreate session.
          }
        }

        const start = new Date();
        const end = new Date(start.getTime() + 4 * 60 * 60 * 1000); // 4 hours from first access
        const session = { start: start.toISOString(), end: end.toISOString() };
        localStorage.setItem(sessionKey, JSON.stringify(session));
        setEffectiveEndTime(session.end);

      } catch (err) {
        setError('Failed to load TP information.');
        console.error(err);
      }
    };

    fetchTpInfo();
  }, [user.student_id]);

  return (
    <div className="dashboard-root">
      <div className="dashboard-inner">
        <header className="dashboard-header">
          <h1 className="dashboard-title">Dashboard</h1>
          <div>
            <span className="dashboard-welcome">Welcome, {user.full_name}!</span>
            <button onClick={logout} className="dashboard-logout">
              Logout
            </button>
          </div>
        </header>

        {error && <p className="dashboard-error">{error}</p>}

        {user.drive_zip_id && (
          <div className="dataset-box">
            <p className="dataset-text">Your dataset is ready for download.</p>
            <div className="dataset-buttons">
              <a
                href={`https://drive.google.com/uc?export=download&id=${user.drive_zip_id}`}
                target="_blank"
                rel="noreferrer"
                className="dataset-zip-link"
              >
                <img src={zipIcon} alt="ZIP Icon" className="zip-icon" />
                {user.zip_name || 'dataset.zip'}
              </a>
              <a
                href="https://github.com/gitpizzanow/NLP-test/blob/main/README.md"
                target="_blank"
                rel="noopener noreferrer"
                className="dataset-guide-btn"
              >
                Display Guide
              </a>
            </div>
          </div>
        )}

        {tp ? (
          <div className="dashboard-card">
            <h2 className="dashboard-card-title">{tp.name}</h2>
            <p className="dashboard-card-subtitle">{tp.description}</p>

            <CountdownTimer
              endTime={effectiveEndTime || tp.end_time}
              graceMinutes={tp.grace_minutes}
              onTimeUp={logout}
            />

            <hr className="my-6 border-gray-200" />
            <UploadComponent tpId={tp.tp_id} />
          </div>
        ) : (
          <div className="loading-indicator">
            <img src={loadingSpinner} alt="Loading..." />
            <span>Loading assessment details...</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default DashboardPage;