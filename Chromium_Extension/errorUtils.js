// errorUtils.js
const ErrorUtils = {
  showError: function (message, resultDiv) {
    resultDiv.style.backgroundColor = '#ff5252';
    resultDiv.style.padding = '10px';
    resultDiv.textContent = `Error: ${message}`;
    setTimeout(() => {
      resultDiv.style.backgroundColor = 'transparent';
      resultDiv.style.padding = '0';
      resultDiv.textContent = '';
    }, 5000);
  },

  showSuccess: function (message, resultDiv) {
    resultDiv.style.backgroundColor = '#4caf50';
    resultDiv.style.padding = '10px';
    resultDiv.textContent = message;
    setTimeout(() => {
      resultDiv.style.backgroundColor = 'transparent';
      resultDiv.style.padding = '0';
      resultDiv.textContent = '';
    }, 3000);
  },

  handleApiError: function (error) {
    if (error.message.includes('Failed to fetch') ||
      error.message.includes('NetworkError')) {
      return 'Server connection failed. Please check if the backend is running.';
    }
    return error.message;
  }
};

export default ErrorUtils;
