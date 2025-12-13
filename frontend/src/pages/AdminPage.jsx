import React, { useState, useEffect } from 'react';
import api from '../lib/api';

function AdminPage() {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchSubmissions = async () => {
      try {
        // This endpoint does not exist yet. You will need to create it.
        // const response = await api.get('/api/admin/submissions');
        // setSubmissions(response.data);

        // Mock data for now
        setSubmissions([
          { id: 1, user_name: 'Ahmed Ali', file_type: 'classifier', status: 'uploaded', timestamp: new Date().toISOString() },
          { id: 2, user_name: 'Fatima Zahra', file_type: 'textprocess', status: 'late', timestamp: new Date().toISOString() },
        ]);

      } catch (err) {
        setError('Failed to fetch submissions.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchSubmissions();
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Admin - Submissions</h1>
      {loading && <p>Loading...</p>}
      {error && <p className="text-red-500">{error}</p>}
      {/* Here you would map over `submissions` to display them in a table */}
      <pre className="bg-gray-200 dark:bg-gray-800 p-4 rounded">{JSON.stringify(submissions, null, 2)}</pre>
    </div>
  );
}

export default AdminPage;