import React, { useEffect, useState, useRef } from 'react';
import axios from './axios';

const AudioPlayer = ({ file }) => {
    const [text, setText] = useState('');
    const [error, setError] = useState(null);
    const audioRef = useRef(null);

    useEffect(() => {
        const fetchText = async () => {
            try {
                // Extract the relative path from the audio_file URL and replace backslashes with forward slashes
                const urlParts = file.audio_file.split('/static/');
                const relativePath = urlParts[urlParts.length - 1].replace('.mp3', '').replace(/\\/g, '/');
                const encodedPath = encodeURIComponent(relativePath);
                const response = await axios.get(`/v1/audio-file/${encodedPath}`);
                setText(response.data.text);
            } catch (error) {
                console.error('Error fetching text:', error);
                setError(`Failed to load text content: ${error.message}`);
            }
        };
        fetchText();
    }, [file]);

    const handleTimeUpdate = () => {
        const currentTime = audioRef.current.currentTime;
        // Logic to highlight the corresponding text based on currentTime
    };

    if (error) {
        return <div>Error: {error}</div>;
    }

    return (
        <div>
            <h2>{file.title}</h2>
            <audio ref={audioRef} controls onTimeUpdate={handleTimeUpdate}>
                <source src={file.audio_file} type="audio/mp3" />
                Your browser does not support the audio element.
            </audio>
            <div>
                {text ? (
                    text.split('\n').map((line, index) => (
                        <p key={index} className="text-line">{line}</p>
                    ))
                ) : (
                    <p>Loading text content...</p>
                )}
            </div>
        </div>
    );
};

export default AudioPlayer;