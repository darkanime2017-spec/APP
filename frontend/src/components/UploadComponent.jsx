import React, { useState, useContext, useEffect } from 'react';
import api from '../lib/api';
import { AuthContext } from '../context/AuthContext';
import ipynbIcon from '../../icons/jupyter-seeklogo.svg';
import txtIcon from '../../icons/txt.png';
import loadingGif from '../../icons/loading-animation.gif';
import '../styles/upload.css';
import '../styles/notifications.css';

const UPLOAD_TYPES = [
  { key: 'textprocess', label: 'Text Process Notebook (.ipynb)', backendType: 'ipynb_textprocess' },
  { key: 'classifier', label: 'Classifier Notebook (.ipynb)', backendType: 'ipynb_classifier' },
  { key: 'embedding', label: 'Embedding File (.txt)', backendType: 'embeddings' },
];

function UploadComponent({ tpId }) {
  const { user } = useContext(AuthContext);

  const [files, setFiles] = useState({
    textprocess: null,
    classifier: null,
    embedding: null,
  });
  const [statuses, setStatuses] = useState({
    textprocess: 'idle',
    classifier: 'idle',
    embedding: 'idle',
  });
  const [messages, setMessages] = useState({
    textprocess: '',
    classifier: '',
    embedding: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState({ type: null, message: '' });
  const [draggedOverItem, setDraggedOverItem] = useState(null); // New state for drag-over effect

  // Effect to auto-dismiss toast after 2 seconds
  useEffect(() => {
    if (toast.message) {
      const timer = setTimeout(() => {
        setToast({ type: null, message: '' });
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [toast.message]);


  const handleFileChange = (key, file) => {
    setFiles(prev => ({ ...prev, [key]: file }));
    setStatuses(prev => ({ ...prev, [key]: 'idle' }));
    setMessages(prev => ({ ...prev, [key]: '' }));
    setToast({ type: null, message: '' });
  };

  const uploadOne = async (key) => {
    const file = files[key];
    if (!file) {
      const errorMsg = 'Please select a file first.';
      setStatuses(prev => ({ ...prev, [key]: 'error' }));
      setMessages(prev => ({ ...prev, [key]: errorMsg }));
      setToast({ type: 'error', message: errorMsg });
      throw new Error(errorMsg);
    }

    if (!user || !user.student_id) {
      const errorMsg = 'You must be logged in to upload.';
      setToast({ type: 'error', message: errorMsg });
      throw new Error(errorMsg);
    }

    const typeConfig = UPLOAD_TYPES.find(t => t.key === key);
    const nameLower = file.name.toLowerCase();
    if (typeConfig.backendType.startsWith('ipynb') && !nameLower.endsWith('.ipynb')) {
      const errorMsg = 'File must be a .ipynb notebook.';
      setStatuses(prev => ({ ...prev, [key]: 'error' }));
      setMessages(prev => ({ ...prev, [key]: errorMsg }));
      setToast({ type: 'error', message: errorMsg });
      throw new Error(errorMsg);
    }
    if (typeConfig.backendType === 'embeddings' && !nameLower.endsWith('.txt')) {
      const errorMsg = 'Embedding file must be a .txt file.';
      setStatuses(prev => ({ ...prev, [key]: 'error' }));
      setMessages(prev => ({ ...prev, [key]: errorMsg }));
      setToast({ type: 'error', message: errorMsg });
      throw new Error(errorMsg);
    }

    const formData = new FormData();
    formData.append('student_id', user.student_id);
    formData.append('file_type', typeConfig.backendType);
    formData.append('file', file);
    formData.append('tp_id', tpId);

    setStatuses(prev => ({ ...prev, [key]: 'uploading' }));

    const minimumDisplayTime = new Promise(resolve => setTimeout(resolve, 700)); // Minimum 700ms display for uploading state

    try {
      const [response] = await Promise.all([
        api.post('/api/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        }),
        minimumDisplayTime
      ]);
      setStatuses(prev => ({ ...prev, [key]: 'success' }));
      setToast({ type: 'success', message: `Successfully uploaded: ${file.name}` });

      if (typeConfig.backendType === 'embeddings') {
        const stored = localStorage.getItem('user');
        if (stored) {
          const parsed = JSON.parse(stored);
          parsed.has_submitted = true;
          localStorage.setItem('user', JSON.stringify(parsed));
        }
        setToast({ type: 'success', message: 'Thank you for your submission! You will be logged out in 5 seconds.' });
        setTimeout(() => {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }, 5000); // 5 seconds delay
      }
    } catch (err) {
      console.error(err);
      await minimumDisplayTime; // Ensure delay even on error
      setStatuses(prev => ({ ...prev, [key]: 'error' }));
      const detail = err.response?.data?.detail;
      const msg = Array.isArray(detail) ? detail.map(d => d.msg).join(', ') : detail || 'Upload failed.';
      setMessages(prev => ({ ...prev, [key]: msg }));

      if (msg.includes('already submitted')) {
        setToast({ type: 'error', message: 'You have already submitted. Logging out.' });
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        setTimeout(() => { window.location.href = '/login'; }, 1500);
      } else {
        setToast({ type: 'error', message: msg });
      }
      throw err;
    }
  };

  const handleSubmitAll = async () => {
    if (!files.textprocess || !files.classifier || !files.embedding) return;
    setSubmitting(true);
    try {
      await uploadOne('textprocess');
      await uploadOne('classifier');
      await uploadOne('embedding');
    } catch (err) {
      // Error toast is already set by uploadOne()
    } finally {
      setSubmitting(false);
    }
  };

  const handleDragEnter = (e, key) => {
    e.preventDefault();
    e.stopPropagation();
    setDraggedOverItem(key);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragLeave = (e, key) => {
    e.preventDefault();
    e.stopPropagation();
    if (draggedOverItem === key) { // Only clear if leaving the current target
      setDraggedOverItem(null);
    }
  };

  const handleDrop = (e, key) => {
    e.preventDefault();
    e.stopPropagation();
    setDraggedOverItem(null);

    const droppedFiles = e.dataTransfer.files;
    if (droppedFiles.length > 0) {
      handleFileChange(key, droppedFiles[0]); // Only take the first file
    }
  };

  const allSelected = !!(files.textprocess && files.classifier && files.embedding);

  return (
    <div className="upload-panel">
      <h3 className="upload-title">Your Submission</h3>

      <div className="space-y-4">
        {UPLOAD_TYPES.map(type => (
          <div
            key={type.key}
            className={`upload-row ${statuses[type.key] === 'success' ? 'is-success' : ''} ${statuses[type.key] === 'error' ? 'is-error' : ''} ${statuses[type.key] === 'uploading' ? 'is-uploading' : ''} ${draggedOverItem === type.key ? 'dragging-over' : ''}`}
            onDragEnter={(e) => handleDragEnter(e, type.key)}
            onDragOver={handleDragOver}
            onDragLeave={(e) => handleDragLeave(e, type.key)}
            onDrop={(e) => handleDrop(e, type.key)}
          >
            <div className="flex items-center flex-1">
              <img
                src={type.backendType.startsWith('ipynb') ? ipynbIcon : txtIcon}
                alt={type.backendType.startsWith('ipynb') ? 'Jupyter Notebook icon' : 'Text file icon'}
                className="upload-icon"
              />
              <div className="flex-1">
                <label className="upload-label">{type.label}</label>
                <input
                  type="file"
                  accept={type.backendType.startsWith('ipynb') ? '.ipynb' : '.txt'}
                  onChange={(e) => handleFileChange(type.key, e.target.files[0])}
                  className="upload-file-input"
                />
              </div>
            </div>
            {statuses[type.key] === 'uploading' && <img src={loadingGif} alt="Uploading..." className="upload-spinner" />}
          </div>
        ))}
      </div>

      <button
        onClick={handleSubmitAll}
        disabled={!allSelected || submitting}
        className="upload-submit-button"
      >
        {submitting ? 'Submitting...' : 'Submit All Files'}
      </button>

      {toast.message && (
        <div className={`toast-notification ${toast.type}`}>
          <p className="toast-message">{toast.message}</p>
          <button
            type="button"
            onClick={() => setToast({ type: null, message: '' })}
            className="toast-close-button"
            aria-label="Dismiss notification"
          >
            &times;
          </button>
        </div>
      )}
    </div>
  );
}

export default UploadComponent;