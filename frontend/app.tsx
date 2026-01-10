import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import SearchInterface from './components/SearchInterface';
import Dashboard from './components/Dashboard';
import RecordDetailView from './components/RecordDetailView';
import Jurisdictions from './components/Jurisdictions';
import Records from './components/Records';

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/search" element={<SearchInterface />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/records" element={<Records />} />
          <Route path="/records/:id" element={<RecordDetailView />} />
          <Route path="/jurisdictions" element={<Jurisdictions />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
};

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
