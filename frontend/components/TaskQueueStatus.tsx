"use client";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { getSettings } from "@/hooks/useSettings";

interface TaskQueueStatusProps {
  refreshInterval?: number; // Optional interval to refresh status
}

const TaskQueueStatus: React.FC<TaskQueueStatusProps> = ({
  refreshInterval = 5000, // Default to 5 seconds
}) => {
  const [taskCount, setTaskCount] = useState<number | null>(null);
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
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Failed to fetch task queue status",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueueStatus();
    const interval = setInterval(fetchQueueStatus, refreshInterval);
    return () => clearInterval(interval); // Clear interval on component unmount
  }, [refreshInterval]);

  return (
    <div className="flex items-center space-x-2">
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <span>
          {taskCount !== null ? `${taskCount} tasks in queue` : "No tasks"}
        </span>
      )}
    </div>
  );
};

export default TaskQueueStatus;
