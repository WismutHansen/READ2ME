'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { Play, Pause } from 'lucide-react';

export default function AudioPlayer({ audioUrl }: { audioUrl: string }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    setError(null);
  }, [audioUrl]);

  const togglePlayPause = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        setError(null);
        audioRef.current.play().catch(err => {
          console.error('Play error:', err);
          setError('Failed to play audio');
        });
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleError = (e: React.SyntheticEvent<HTMLAudioElement, Event>) => {
    const mediaError = e.currentTarget.error;
    console.error('Audio error:', {
      url: audioUrl,
      error: mediaError,
      code: mediaError?.code,
      message: mediaError?.message
    });
    setError('Failed to load audio');
    setIsPlaying(false);
  };

  return (
    <div className="flex items-center gap-4">
      <audio
        ref={audioRef}
        src={audioUrl}
        onEnded={() => setIsPlaying(false)}
        onError={handleError}
        preload="metadata"
      />
      <Button
        variant="outline"
        size="icon"
        onClick={togglePlayPause}
        disabled={!!error}
      >
        {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
      </Button>
      {error && (
        <span className="text-sm text-red-500">{error}</span>
      )}
    </div>
  );
}
