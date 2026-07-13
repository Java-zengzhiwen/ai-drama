import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Layout, Typography } from "antd";
import { useState } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes, useParams } from "react-router-dom";
import { ChapterWorkspace } from "../features/chapter/ChapterWorkspace";
import { ProjectDashboardPage } from "../features/projects/ProjectDashboardPage";
import { ProjectListPage } from "../features/projects/ProjectListPage";
import { AgnesSettingsPage } from "../features/settings/AgnesSettingsPage";
import { SupplierListPage } from "../features/suppliers/SupplierListPage";
import { SupplierDetailPage } from "../features/suppliers/SupplierDetailPage";
import "./app.css";

function ChapterWorkspacePage() {
  const { chapterId = "", projectId = "" } = useParams();

  return <ChapterWorkspace chapterId={chapterId} projectId={projectId} />;
}

function AppShell() {
  return (
    <Layout className="app-shell">
      <Layout.Header className="app-header">
        <Typography.Text className="app-brand">AI 剧集制作</Typography.Text>
        <nav className="app-nav" aria-label="主导航">
          <Link to="/projects">
            项目
          </Link>
          <Link to="/suppliers">模型供应商</Link>
        </nav>
      </Layout.Header>
      <Layout.Content className="app-content">
        <Routes>
          <Route path="/projects" element={<ProjectListPage />} />
          <Route path="/projects/:projectId" element={<ProjectDashboardPage />} />
          <Route
            path="/projects/:projectId/chapters/:chapterId"
            element={<ChapterWorkspacePage />}
          />
          <Route path="/suppliers" element={<SupplierListPage />} />
          <Route path="/suppliers/:supplierId" element={<SupplierDetailPage />} />
          <Route path="/settings/agnes" element={<AgnesSettingsPage />} />
          <Route path="*" element={<Navigate to="/projects" replace />} />
        </Routes>
      </Layout.Content>
    </Layout>
  );
}

export function App() {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
