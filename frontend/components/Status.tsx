'use client';

import { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle, Clock } from 'lucide-react';

interface StatusState {
  queue: {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
  };
  errors: Array<{
    timestamp: string;
    message: string;
    type: string;
  }>;
  lastUpdate: string;
}

export default function Status() {
  const [status, setStatus] = useState<StatusState>({
    queue: { pending: 0, processing: 0, completed: 0, failed: 0 },
    errors: [],
    lastUpdate: '',
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch('http://localhost:7777/v1/status');
        const data = await response.json();
        setStatus(data);
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch status:', error);
      }
    };

    // Initial fetch
    fetchStatus();

    // Poll every 5 seconds
    const interval = setInterval(fetchStatus, 5000);

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="flex items-center gap-2"><Clock className="h-4 w-4" /> Loading status...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-4">
        <div className="rounded-lg border p-4">
          <h3 className="font-medium">Pending</h3>
          <p className="text-2xl">{status.queue.pending}</p>
        </div>
        <div className="rounded-lg border p-4">
          <h3 className="font-medium">Processing</h3>
          <p className="text-2xl">{status.queue.processing}</p>
        </div>
        <div className="rounded-lg border p-4">
          <h3 className="font-medium">Completed</h3>
          <p className="text-2xl">{status.queue.completed}</p>
        </div>
        <div className="rounded-lg border p-4">
          <h3 className="font-medium">Failed</h3>
          <p className="text-2xl">{status.queue.failed}</p>
        </div>
      </div>

      {status.errors.length > 0 && (
        <div className="rounded-lg border p-4 space-y-2">
          <h3 className="font-medium flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-red-500" />
            Recent Errors
          </h3>
          <div className="space-y-2">
            {status.errors.map((error, index) => (
              <div key={index} className="text-sm text-red-500">
                [{error.timestamp}] {error.type}: {error.message}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-sm text-gray-500">
        Last updated: {status.lastUpdate}
      </div>
    </div>
  );
} 