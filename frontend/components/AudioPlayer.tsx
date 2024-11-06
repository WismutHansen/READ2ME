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
        crossOrigin="anonymous"
      />
      <Button 
        onClick={togglePlayPause}
        variant="outline"
        size="icon"
        className="w-10 h-10"
        disabled={!!error}
      >
        {isPlaying ? (
          <Pause className="h-5 w-5" />
        ) : (
          <Play className="h-5 w-5" />
        )}
      </Button>
      {error && (
        <span className="text-sm text-destructive">{error}</span>
      )}
    </div>
  );
}