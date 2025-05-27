import React, { useCallback, useState } from 'react';
import './FileUpload.css';

const FileUpload = ({ onFileUpload, isLoading }) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type === 'application/pdf') {
        setSelectedFile(file);
        onFileUpload(file);
      } else {
        alert('Please upload a PDF file');
      }
    }
  }, [onFileUpload]);

  const handleChange = useCallback((e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.type === 'application/pdf') {
        setSelectedFile(file);
        onFileUpload(file);
      } else {
        alert('Please upload a PDF file');
      }
    }
  }, [onFileUpload]);

  const onButtonClick = useCallback(() => {
    document.getElementById('file-upload-input').click();
  }, []);

  return (
    <div className="file-upload-container">
      <form 
        className={`file-upload-form ${dragActive ? 'drag-active' : ''} ${isLoading ? 'loading' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onSubmit={(e) => e.preventDefault()}
      >
        <input
          id="file-upload-input"
          type="file"
          accept=".pdf"
          onChange={handleChange}
          style={{ display: 'none' }}
          disabled={isLoading}
        />
        
        <div className="file-upload-content">
          {isLoading ? (
            <div className="upload-loading">
              <div className="upload-spinner"></div>
              <p>Processing your PDF...</p>
              <small>This may take a few minutes</small>
            </div>
          ) : (
            <>
              <div className="upload-icon">📄</div>
              <h3>Upload PDF Document</h3>
              <p>
                {selectedFile 
                  ? `Selected: ${selectedFile.name}` 
                  : 'Drag and drop your PDF here, or click to browse'
                }
              </p>
              <button 
                type="button" 
                onClick={onButtonClick}
                className="upload-button"
                disabled={isLoading}
              >
                Choose PDF File
              </button>
              <div className="upload-info">
                <small>Supported format: PDF (max 50MB)</small>
              </div>
            </>
          )}
        </div>
      </form>
    </div>
  );
};

export default FileUpload;