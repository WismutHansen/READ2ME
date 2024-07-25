import React, { useEffect, useState } from 'react';
import axios from './axios';

const AudioList = ({ onSelect }) => {
    const [audioFiles, setAudioFiles] = useState([]);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchAudioFiles = async () => {
            try {
                const response = await axios.get('/v1/audio-files');
                const files = response.data.audio_files.map(file => ({
                    ...file,
                    audio_file: `http://localhost:7777/${file.audio_file}`
                }));
                setAudioFiles(files);
            } catch (error) {
                console.error('Error fetching audio files:', error);
                setError('Failed to load audio files');
            }
        };
        fetchAudioFiles();
    }, []);

    if (error) {
        return <div>Error: {error}</div>;
    }

    return (
        <div>
            <h2>Available Audio Files</h2>
            {audioFiles.length === 0 ? (
                <p>No audio files available.</p>
            ) : (
                <ul>
                    {audioFiles.map(file => (
                        <li key={file.audio_file} onClick={() => onSelect(file)}>
                            {file.title}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
};

export default AudioList;