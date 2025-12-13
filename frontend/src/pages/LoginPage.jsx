import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import api from '../lib/api';
import '../styles/login.css';
import '../styles/notifications.css'; // Import notification styles
import loadingSpinner from '../../icons/loading-animation.gif';

function LoginPage() {
  const [studentId, setStudentId] = useState('');
  const [fullName, setFullName] = useState('');
  const [toast, setToast] = useState({ message: '', type: '' });
  const [loading, setLoading] = useState(false);
  const [students, setStudents] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [isSuggestionsVisible, setSuggestionsVisible] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const showErrorToast = (message) => {
    setToast({ message, type: 'error' });
  };

  // Effect to auto-dismiss toast after 2 seconds
  useEffect(() => {
    if (toast.message) {
      const timer = setTimeout(() => {
        setToast({ message: '', type: '' });
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [toast.message]);

  const handleLogin = async () => {
    const trimmedId = studentId.trim();
    const trimmedName = fullName.trim();

    if (!trimmedId) {
      showErrorToast('Student ID is required.');
      return;
    }
    if (!/^(201[5-9]|202[0-5])\d{8}$/.test(trimmedId)) {
      showErrorToast('Invalid Student ID format. Example: 201912345678');
      return;
    }
    if (!trimmedName || !students.includes(trimmedName)) {
      showErrorToast('Please select a valid name from the list.');
      return;
    }

    setLoading(true);
    setToast({ message: '', type: '' });

    try {
      await login(trimmedId, trimmedName);
      navigate('/');
    } catch (err) {
      console.error(err);
      const detail = err.response?.data?.detail;
      const message = Array.isArray(detail) ? detail[0].msg : detail || 'An error occurred during login.';
      showErrorToast(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const fetchStudents = async () => {
      try {
        const resp = await api.get('/api/student/list');
        setStudents(resp.data || []);
      } catch (err) {
        console.error('Failed to load student list', err);
        showErrorToast('Failed to load student list. Please refresh the page.');
      }
    };
    fetchStudents();
  }, []);

  const handleNameChange = (e) => {
    const value = e.target.value;
    setFullName(value);
    if (value.length > 0) {
      const filteredSuggestions = students.filter(student =>
        student.toLowerCase().includes(value.toLowerCase())
      );
      setSuggestions(filteredSuggestions);
      setSuggestionsVisible(true);
    } else {
      setSuggestions([]);
      setSuggestionsVisible(false);
    }
  };

  const suggestionClicked = (name) => {
    setFullName(name);
    setSuggestions([]);
    setSuggestionsVisible(false);
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="login-container">
        <h1 className="login-title">Login</h1>
        
        <div>
          <div className="relative mb-6">
            <label htmlFor="studentId" className="login-label">Student ID</label>
            <input
              type="text"
              id="studentId"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              placeholder="Enter your student ID"
              className="login-input"
              required
            />
          </div>
          <div className="relative">
            <label htmlFor="fullName" className="login-label">Full Name</label>
            <input
              type="text"
              id="fullName"
              value={fullName}
              onChange={handleNameChange}
              onFocus={() => setSuggestionsVisible(true)} // Simplified onFocus
              onBlur={() => setTimeout(() => setSuggestionsVisible(false), 200)} // Increased delay
              placeholder="Type to search your name"
              className="login-input"
              required
              autoComplete="off"
            />
            {isSuggestionsVisible && suggestions.length > 0 && (
              <ul className="autocomplete-results">
                {suggestions.map((name) => (
                  <li
                    key={name}
                    onClick={() => suggestionClicked(name)}
                    className="autocomplete-item"
                  >
                    {name}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="mt-8">
          <button
            onClick={handleLogin}
            disabled={loading}
            className="login-button"
          >
            {loading && <img src={loadingSpinner} alt="Loading" className="loading-spinner" />}
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </div>
      </div>

      {toast.message && (
        <div className={`toast-notification ${toast.type}`}>
          <p className="toast-message">{toast.message}</p>
          <button
            type="button"
            onClick={() => setToast({ message: '', type: '' })}
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

export default LoginPage;