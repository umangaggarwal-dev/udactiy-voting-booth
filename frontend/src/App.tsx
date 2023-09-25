import './App.css';
import React, { useEffect } from 'react';
import { H1, H4 } from "@blueprintjs/core"
import { IBallotForm } from "./BallotForm"


function App() {
    useEffect(() => {
        function showPrompt() {
          const promptMessage = 'Kindly read the privacy policy carefully.\nYour national ID will be used to verify your voter registration and validate the casted ballot.\nOnce the digital verification is complete, your vote will be completely \'anonymous\'.\nPlease note that the system will release an internal list of voters committing a fraud which will also remain private.';
          if (window.confirm(promptMessage)) {
            // User clicked "OK" in the prompt
          } else {
            // User clicked "Cancel" in the prompt
            window.close();
          }
        }

        window.onload = showPrompt;

        // Clean up the event handler when the component unmounts
        return () => {
          window.onload = null;
        };
    }, []);

  return (
    <div className="app">
      <div className="app-header">
          <H1 className="white-text"> The Republic of Atlantis </H1>
          <H4 className="white-text"> DEPARTMENT OF ELECTORAL AFFAIRS </H4>
      </div>
      <div className="form">
        <IBallotForm />
      </div>
    </div>
  );
}

export default App;
