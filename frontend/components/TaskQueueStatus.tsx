"use client";

import { useState, useEffect } from 'react';
import { Button } from './ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from './ui/dialog';
import { ListTodo, AlertCircle, Clock, CheckCircle, Loader2, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getSettings } from '@/lib/settings';
import { Progress } from './ui/progress';

interface StatusState {
  queue: {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
  };
  tasks: Array<{
    id: string;
    status: string;
    progress: number;
    tts_engine: string;
    task: string;
  }>;
  errors: Array<{
    timestamp: string;
    message: string;
    type: string;
  }>;
  lastUpdate: string;
}

interface TaskQueueStatusProps {
  refreshArticles: () => void;
}

function StatusContent({ status, loading, onRefresh }: { 
  status: StatusState; 
  loading: boolean;
  onRefresh: () => void;
}) {
  if (loading) {
    return (
      <div className="flex items-center gap-2 p-4">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Loading status...</span>
      </div>
    );
  }

  // Add safety check for status and queue
  const queue = status?.queue ?? { pending: 0, processing: 0, completed: 0, failed: 0 };
  const tasks = status?.tasks ?? [];
  const errors = status?.errors ?? [];
  const lastUpdate = status?.lastUpdate ?? new Date().toISOString();

  return (
    <div className="space-y-4 p-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Queue Status</h2>
        <Button variant="outline" size="sm" onClick={onRefresh}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh List
        </Button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-lg border p-3">
          <h3 className="text-sm font-medium flex items-center gap-2">
            <Clock className="h-4 w-4 text-blue-500" />
            Pending
          </h3>
          <p className="text-2xl">{queue.pending}</p>
        </div>
        <div className="rounded-lg border p-3">
          <h3 className="text-sm font-medium flex items-center gap-2">
            <Loader2 className="h-4 w-4 text-yellow-500 animate-spin" />
            Processing
          </h3>
          <p className="text-2xl">{queue.processing}</p>
        </div>
        <div className="rounded-lg border p-3">
          <h3 className="text-sm font-medium flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-green-500" />
            Completed
          </h3>
          <p className="text-2xl">{queue.completed}</p>
        </div>
        <div className="rounded-lg border p-3">
          <h3 className="text-sm font-medium flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-red-500" />
            Failed
          </h3>
          <p className="text-2xl">{queue.failed}</p>
        </div>
      </div>

      {tasks.length > 0 && (
        <div className="rounded-lg border p-3 space-y-3">
          <h3 className="text-sm font-medium flex items-center gap-2">
            <Loader2 className="h-4 w-4 text-yellow-500 animate-spin" />
            Active Tasks
          </h3>
          <div className="space-y-3">
            {tasks.map((task) => (
              <div key={task.id} className="space-y-2">
                <div className="flex justify-between items-center text-sm">
                  <span className="font-medium">
                    {task.tts_engine === 'chatterbox' ? 'Chatterbox TTS' : task.tts_engine} - {task.task}
                  </span>
                  <span className="text-gray-500">{task.progress}%</span>
                </div>
                <Progress value={task.progress} className="h-2" />
              </div>
            ))}
          </div>
        </div>
      )}

      {errors.length > 0 && (
        <div className="rounded-lg border p-3 space-y-2">
          <h3 className="text-sm font-medium flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-red-500" />
            Recent Errors
          </h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {errors.map((error, index) => (
              <div key={index} className="text-sm text-red-500 border-l-2 border-red-500 pl-2">
                <div className="font-medium">{error.type}</div>
                <div className="text-xs text-gray-500">{error.timestamp}</div>
                <div>{error.message}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-xs text-gray-500">
        Last updated: {new Date(lastUpdate).toLocaleString()}
      </div>
    </div>
  );
}

export default function TaskQueueStatus({ refreshArticles }: TaskQueueStatusProps) {
  const [status, setStatus] = useState<StatusState>({
    queue: { pending: 0, processing: 0, completed: 0, failed: 0 },
    tasks: [],
    errors: [],
    lastUpdate: '',
  });
  const [loading, setLoading] = useState(true);
  const [isOpen, setIsOpen] = useState(false);

  const fetchStatus = async () => {
    try {
      const { serverUrl } = getSettings();
      const response = await fetch(`${serverUrl}/v1/status`, {
        credentials: 'include'
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Status response:', data);
      
      const formattedStatus: StatusState = {
        queue: {
          pending: Number(data.queue?.pending ?? 0),
          processing: Number(data.queue?.processing ?? 0),
          completed: Number(data.queue?.completed ?? 0),
          failed: Number(data.queue?.failed ?? 0)
        },
        errors: Array.isArray(data.errors) ? data.errors : [],
        lastUpdate: data.lastUpdate ?? new Date().toISOString()
      };

      setStatus(formattedStatus);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch status:', error);
      // Set default values on error
      setStatus({
        queue: { pending: 0, processing: 0, completed: 0, failed: 0 },
        errors: [],
        lastUpdate: new Date().toISOString(),
      });
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchStatus();
    }
    // Only start polling when modal is open
    const interval = isOpen ? setInterval(fetchStatus, 5000) : null;
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isOpen]);

  // Add safety checks with optional chaining and nullish coalescing
  const hasActiveJobs = (status?.queue?.pending ?? 0) > 0 || (status?.queue?.processing ?? 0) > 0;
  const hasErrors = (status?.queue?.failed ?? 0) > 0;

  const handleRefresh = () => {
    refreshArticles();
    fetchStatus();
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
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
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Task Queue Status</DialogTitle>
        </DialogHeader>
        <StatusContent 
          status={status} 
          loading={loading} 
          onRefresh={handleRefresh}
        />
      </DialogContent>
    </Dialog>
  );
}
