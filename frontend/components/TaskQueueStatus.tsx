"use client";
import { useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
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

const TaskQueueStatus: React.FC<TaskQueueStatusProps> = ({
  refreshInterval = 5000,
  refreshArticles,
}) => {
  const [taskCount, setTaskCount] = useState<number | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const fetchQueueStatus = async () => {
    setLoading(true);
    const { serverUrl, ttsEngine } = getSettings();
    try {
      const response = await fetch(`${serverUrl}/v1/queue/status`);
      if (!response.ok) throw new Error("Failed to fetch queue status");
      const data = await response.json();
      setTaskCount(data.task_count);
      setTasks(data.tasks || []);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Failed to fetch task queue status",
      });
    } finally {
      setLoading(false);
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
        <div className="flex items-center space-x-2">
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <span>
              {taskCount !== null ? `${taskCount} tasks in queue` : "No tasks"}
            </span>
          )}
        </div>
      </HoverCardTrigger>
      <HoverCardContent className="w-80 p-4">
        <div className="space-y-3">
          <h4 className="font-semibold">Task List</h4>
          {tasks.length > 0 ? (
            tasks.map((task, index) => (
              <div key={index} className="p-2 border-b last:border-0 flex justify-between items-center">
                <div>
                  <p className="text-sm font-medium">Task {index + 1}</p>
                  <p className="text-xs text-gray-500">Type: {task.type}</p>
                  <p className="text-xs text-gray-500">
                    Content: <a href={task.content} target="_blank" rel="noopener noreferrer" className="text-blue-500 underline">{task.content}</a>
                  </p>
                  <p className="text-xs text-gray-500">TTS Engine: {task.tts_engine}</p>
                </div>
                <button
                  onClick={() => removeTask(task)}
                  className="text-gray-500 hover:text-red-500"
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
