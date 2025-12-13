import React from 'react';
import '../styles/guide.css';

function GuidePanel() {
  return (
    <div className="guide-panel">
      <a
        href="https://github.com/gitpizzanow/NLP-test/blob/main/README.md"
        download="NLP_Test_Guide.md"
        className="download-guide-button"
      >
        Download Guide (Markdown)
      </a>
    </div>
  );
}

export default GuidePanel;
