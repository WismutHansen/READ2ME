"use client";
import { useEffect, useState } from "react";
import { Loader2, X, ListOrdered } from "lucide-react";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { getSettings } from "@/lib/settings";

interface TaskQueueStatusProps {
  refreshInterval?: number;
  refreshArticles: () => Promise<void>;
}

interface Task {
  type: string;
  content: string;
  tts_engine: string;
}

const parseTaskType = (type: string) => {
  const [source, action] = type.split('/');
  return {
    source: source || '',
    action: action || ''
  };
};

const getSourceLabel = (source: string) => {
  switch (source) {
    case 'url':
      return 'URL';
    case 'text':
      return 'Text';
    default:
      return source;
  }
};

const getActionLabel = (action: string) => {
  switch (action) {
    case 'full':
      return 'Full Text';
    case 'summary':
      return 'TL;DR';
    case 'podcast':
      return 'Podcast';
    default:
      return action;
  }
};

const getSourceColor = (source: string) => {
  switch (source) {
    case 'url':
      return 'bg-orange-100 text-orange-800';
    case 'text':
      return 'bg-pink-100 text-pink-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

const getActionColor = (action: string) => {
  switch (action) {
    case 'full':
      return 'bg-blue-100 text-blue-800';
    case 'summary':
      return 'bg-green-100 text-green-800';
    case 'podcast':
      return 'bg-purple-100 text-purple-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

const TaskQueueStatus: React.FC<TaskQueueStatusProps> = ({
  refreshInterval = 5000,
  refreshArticles,
}) => {
  const [taskCount, setTaskCount] = useState<number | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState(false);
  const [previousTaskCount, setPreviousTaskCount] = useState<number | null>(null);
  const { toast } = useToast();

  const fetchQueueStatus = async () => {
    // Only show loading on initial fetch
    if (!initialized) {
      setLoading(true);
    }
    
    const { serverUrl, ttsEngine } = getSettings();
    try {
      const response = await fetch(`${serverUrl}/v1/queue/status`);
      if (!response.ok) throw new Error("Failed to fetch queue status");
      const data = await response.json();
      
      // Only update state if there are actual changes
      const tasksChanged = JSON.stringify(data.tasks) !== JSON.stringify(tasks);
      const countChanged = data.task_count !== taskCount;
      
      if (tasksChanged || countChanged) {
        // If task count decreased and we had a previous count, it means a task completed
        if (previousTaskCount !== null && data.task_count < previousTaskCount) {
          // Refresh the article list since a task completed
          await refreshArticles();
        }
        
        setTaskCount(data.task_count);
        setPreviousTaskCount(data.task_count);
        setTasks(data.tasks || []);
      }
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Failed to fetch task queue status",
      });
    } finally {
      setLoading(false);
      setInitialized(true);
    }
  };

  const removeTask = async (task: Task) => {
    const { serverUrl } = getSettings();
    try {
      const response = await fetch(`${serverUrl}/v1/queue/remove`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(task),
      });
      if (!response.ok) throw new Error("Failed to remove task");
      toast({ variant: "success", title: "Task removed successfully" });

      // Call refreshArticles after task removal
      await refreshArticles();

      // Refresh the task list after deletion
      await fetchQueueStatus();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Failed to remove task",
      });
    }
  };

  useEffect(() => {
    fetchQueueStatus();
    const interval = setInterval(fetchQueueStatus, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  return (
    <HoverCard>
      <HoverCardTrigger asChild>
        <Button
          variant="outline"
          size="default"
          className="flex items-center gap-2"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <>
              <ListOrdered className="h-4 w-4" />
              <span>
                {taskCount !== null ? `${taskCount} ` : "No tasks"}
              </span>
            </>
          )}
        </Button>
      </HoverCardTrigger>
      <HoverCardContent className="w-96 p-4">
        <div className="space-y-3">
          <h4 className="font-semibold">Task List</h4>
          {tasks.length > 0 ? (
            tasks.map((task, index) => (
              <div key={index} className="p-2 border-b last:border-0 flex justify-between items-start gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium">Task {index + 1}</span>
                    {task.type && (
                      <>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${getSourceColor(parseTaskType(task.type).source)}`}>
                          {getSourceLabel(parseTaskType(task.type).source)}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${getActionColor(parseTaskType(task.type).action)}`}>
                          {getActionLabel(parseTaskType(task.type).action)}
                        </span>
                      </>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 truncate hover:text-clip hover:whitespace-normal">
                    <a href={task.content} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
                      {task.content}
                    </a>
                  </p>
                  <p className="text-xs text-gray-500">TTS: {task.tts_engine}</p>
                </div>
                <button
                  onClick={() => removeTask(task)}
                  className="text-gray-500 hover:text-red-500 flex-shrink-0"
                  aria-label="Remove task"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ))
          ) : (
            <span className="text-sm">No tasks available</span>
          )}
        </div>
      </HoverCardContent>
    </HoverCard>
  );
};

export default TaskQueueStatus;
