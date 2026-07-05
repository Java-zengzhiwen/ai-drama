import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Layout, Typography } from "antd";
import { useState } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes, useParams } from "react-router-dom";
import { ProjectDashboardPage } from "../features/projects/ProjectDashboardPage";
import { ProjectListPage } from "../features/projects/ProjectListPage";

function ChapterWorkspacePage() {
  const { chapterId, projectId } = useParams();

  return (
    <section>
      <Typography.Title level={1}>章节工作区</Typography.Title>
      <Typography.Text type="secondary">
        Project {projectId} / Chapter {chapterId}
      </Typography.Text>
    </section>
  );
}

function AppShell() {
  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Layout.Header
        style={{
          alignItems: "center",
          display: "flex",
          paddingInline: 24,
        }}
      >
        <Typography.Title
          level={2}
          style={{ color: "white", fontSize: 18, lineHeight: 1, margin: 0, width: 180 }}
        >
          AI Drama
        </Typography.Title>
        <nav style={{ flex: 1, minWidth: 0 }}>
          <Link style={{ color: "white" }} to="/projects">
            项目
          </Link>
        </nav>
      </Layout.Header>
      <Layout.Content style={{ padding: 24 }}>
        <Routes>
          <Route path="/projects" element={<ProjectListPage />} />
          <Route path="/projects/:projectId" element={<ProjectDashboardPage />} />
          <Route
            path="/projects/:projectId/chapters/:chapterId"
            element={<ChapterWorkspacePage />}
          />
          <Route path="*" element={<Navigate to="/projects" replace />} />
        </Routes>
      </Layout.Content>
    </Layout>
  );
}

export function App() {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
