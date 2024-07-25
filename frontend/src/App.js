import React, { useState } from 'react';
import AudioList from './AudioList';
import AudioPlayer from './AudioPlayer';
import './App.css';


const App = () => {
    const [selectedFile, setSelectedFile] = useState(null);

    return (
        <div>
            <h1>Read2Me Audio Player</h1>
            {!selectedFile && <AudioList onSelect={setSelectedFile} />}
            {selectedFile && <AudioPlayer file={selectedFile} />}
        </div>
    );
};

export default App;
