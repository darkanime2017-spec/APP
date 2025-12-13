import React, { createContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { jwtDecode } from 'jwt-decode';
import api from '../lib/api';

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      if (token === 'fake-jwt-for-development-only') {
        const userData = JSON.parse(localStorage.getItem('user'));
        if (userData) {
          setUser(userData);
          api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        }
      } else {
        try {
          const decoded = jwtDecode(token);
          // Check if token is expired
          if (decoded.exp * 1000 > Date.now()) {
            const userData = JSON.parse(localStorage.getItem('user'));
            setUser(userData);
            api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          } else {
            // Token expired
            localStorage.removeItem('token');
            localStorage.removeItem('user');
          }
        } catch (e) {
          console.error("Invalid token", e);
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
      }
    }
    setLoading(false);
  }, []);

  const login = async (studentId, fullName) => {
    // Call lightweight student login that locates an existing ZIP in Drive.
    const response = await api.post('/api/student/login', {
      student_id: studentId,
      full_name: fullName,
    });

    const data = response.data;

    const userData = {
      student_id: data.student_id,
      full_name: data.full_name,
      drive_zip_id: data.drive_zip_id ?? null,
      zip_name: data.zip_name ?? null,
      has_submitted: data.has_submitted ?? false,
      role: 'student',
    };

    const placeholderToken = 'fake-jwt-for-development-only';

    localStorage.setItem('token', placeholderToken);
    localStorage.setItem('user', JSON.stringify(userData));
    api.defaults.headers.common['Authorization'] = `Bearer ${placeholderToken}`;
    setUser(userData);
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    delete api.defaults.headers.common['Authorization'];
    navigate('/login');
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};