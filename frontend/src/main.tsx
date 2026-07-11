import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./index.css";
import { Layout } from "./components/Layout";
import { Scanner } from "./pages/Scanner";
import { Screener } from "./pages/Screener";
import { Guide } from "./pages/Guide";
import { ExpertCorner } from "./pages/ExpertCorner";
import { About } from "./pages/About";
import { SettingsProvider } from "./lib/settings";

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <SettingsProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<About />} />
            <Route path="/scanner" element={<Scanner />} />
            <Route path="/screener" element={<Screener />} />
            <Route path="/guide" element={<Guide />} />
            <Route path="/expert" element={<ExpertCorner />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
      </SettingsProvider>
    </QueryClientProvider>
  </StrictMode>,
);
