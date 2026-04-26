import React from "react";
import ReactDOM from "react-dom/client";
import { Toaster } from "react-hot-toast";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
    <Toaster
      position="top-right"
      toastOptions={{
        style: {
          background: "#1a1a1a",
          color: "#f0f0f0",
          border: "1px solid #2e2e2e",
          fontFamily: "'IBM Plex Sans', sans-serif",
          fontSize: "13px",
          borderRadius: "6px",
        },
        success: {
          iconTheme: { primary: "#00c896", secondary: "#0a0a0a" },
        },
        error: {
          iconTheme: { primary: "#ff4d4d", secondary: "#0a0a0a" },
        },
      }}
    />
  </React.StrictMode>
);
