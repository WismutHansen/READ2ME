'use client';

import { useState, useEffect } from 'react';
import { Button } from './ui/button';
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from './ui/hover-card';
import {
  Dialog,
  DialogContent,
  DialogTrigger,
} from './ui/dialog';
import { ListTodo, AlertCircle, Clock, CheckCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getSettings } from '@/lib/settings';

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

function StatusContent({ status, loading }: { status: StatusState; loading: boolean }) {
  if (loading) {
    return (
      <div className="flex items-center gap-2 p-4">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Loading status...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-lg border p-3">
          <h3 className="text-sm font-medium flex items-center gap-2">
            <Clock className="h-4 w-4 text-blue-500" />
            Pending
          </h3>
          <p className="text-2xl">{status.queue.pending}</p>
        </div>
        <div className="rounded-lg border p-3">
          <h3 className="text-sm font-medium flex items-center gap-2">
            <Loader2 className="h-4 w-4 text-yellow-500 animate-spin" />
            Processing
          </h3>
          <p className="text-2xl">{status.queue.processing}</p>
        </div>
        <div className="rounded-lg border p-3">
          <h3 className="text-sm font-medium flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-green-500" />
            Completed
          </h3>
          <p className="text-2xl">{status.queue.completed}</p>
        </div>
        <div className="rounded-lg border p-3">
          <h3 className="text-sm font-medium flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-red-500" />
            Failed
          </h3>
          <p className="text-2xl">{status.queue.failed}</p>
        </div>
      </div>

      {status.errors.length > 0 && (
        <div className="rounded-lg border p-3 space-y-2">
          <h3 className="text-sm font-medium flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-red-500" />
            Recent Errors
          </h3>
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {status.errors.map((error, index) => (
              <div key={index} className="text-sm text-red-500">
                [{error.timestamp}] {error.type}: {error.message}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-xs text-gray-500">
        Last updated: {new Date(status.lastUpdate).toLocaleString()}
      </div>
    </div>
  );
}

export default function TaskStatusModal() {
  const [status, setStatus] = useState<StatusState>({
    queue: { pending: 0, processing: 0, completed: 0, failed: 0 },
    errors: [],
    lastUpdate: '',
  });
  const [loading, setLoading] = useState(true);

  const fetchStatus = async () => {
    try {
      const { serverUrl, ttsEngine } = getSettings();
      const response = await fetch(`${serverUrl}/v1/status`);
      const data = await response.json();
      setStatus(data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch status:', error);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const hasActiveJobs = status.queue.pending > 0 || status.queue.processing > 0;
  const hasErrors = status.queue.failed > 0;

  return (
    <div className="relative inline-block">
      {/* Desktop: Hover Card */}
      <div className="hidden sm:block">
        <HoverCard>
          <HoverCardTrigger asChild>
            <Button
              variant="outline"
              size="icon"
              className={cn(
                "relative",
                hasActiveJobs && "animate-pulse",
                hasErrors && "border-red-500"
              )}
            >
              <ListTodo className={cn(
                "h-4 w-4",
                hasErrors && "text-red-500"
              )} />
              {(hasActiveJobs || hasErrors) && (
                <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-red-500" />
              )}
            </Button>
          </HoverCardTrigger>
          <HoverCardContent className="w-[340px] sm:w-[500px]" align="end">
            <StatusContent status={status} loading={loading} />
          </HoverCardContent>
        </HoverCard>
      </div>

      {/* Mobile: Click Dialog */}
      <div className="sm:hidden">
        <Dialog>
          <DialogTrigger asChild>
            <Button
              variant="outline"
              size="icon"
              className={cn(
                "relative",
                hasActiveJobs && "animate-pulse",
                hasErrors && "border-red-500"
              )}
            >
              <ListTodo className={cn(
                "h-4 w-4",
                hasErrors && "text-red-500"
              )} />
              {(hasActiveJobs || hasErrors) && (
                <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-red-500" />
              )}
            </Button>
          </DialogTrigger>
          <DialogContent className="w-[340px] sm:w-[500px]">
            <StatusContent status={status} loading={loading} />
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
} 
