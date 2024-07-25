import axios from 'axios';

const instance = axios.create({
    baseURL: 'http://localhost:7777', // Change this to your backend URL
});

export default instance;
