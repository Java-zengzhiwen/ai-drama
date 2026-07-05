import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Input, Skeleton, Typography } from "antd";
import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { createProject, listProjects, type ProjectCreate, type ProjectRead } from "./api";

const emptyProject: ProjectCreate = {
  name: "",
  description: "",
  series_canon: "",
  characters_context: "",
  production_brief: "",
};

export function ProjectListPage() {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<ProjectCreate>(emptyProject);
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });
  const createProjectMutation = useMutation({
    mutationFn: createProject,
    onSuccess: (project) => {
      queryClient.setQueryData<ProjectRead[]>(["projects"], (current = []) => [...current, project]);
      setDraft(emptyProject);
    },
  });

  function updateDraft(field: keyof ProjectCreate, value: string) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  function submitProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createProjectMutation.mutate({
      name: draft.name.trim(),
      description: draft.description.trim(),
      series_canon: draft.series_canon.trim(),
      characters_context: draft.characters_context.trim(),
      production_brief: draft.production_brief.trim(),
    });
  }

  const projects = projectsQuery.data ?? [];
  const isSubmitting = createProjectMutation.isPending;

  return (
    <section aria-labelledby="project-list-title">
      <div style={{ display: "grid", gap: 20 }}>
        <div>
          <Typography.Title id="project-list-title" level={1} style={{ fontSize: 22, margin: 0 }}>
            项目列表
          </Typography.Title>
          <Typography.Text type="secondary">选择或创建一个本地制作项目。</Typography.Text>
        </div>

        <form
          aria-label="创建项目"
          onSubmit={submitProject}
          style={{
            background: "#ffffff",
            border: "1px solid #d9dee8",
            borderRadius: 6,
            display: "grid",
            gap: 12,
            padding: 16,
          }}
        >
          <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
            <label style={{ display: "grid", gap: 4 }}>
              <span>项目名称</span>
              <Input
                aria-label="项目名称"
                disabled={isSubmitting}
                onChange={(event) => updateDraft("name", event.target.value)}
                value={draft.name}
              />
            </label>
            <label style={{ display: "grid", gap: 4 }}>
              <span>项目描述</span>
              <Input
                aria-label="项目描述"
                disabled={isSubmitting}
                onChange={(event) => updateDraft("description", event.target.value)}
                value={draft.description}
              />
            </label>
            <label style={{ display: "grid", gap: 4 }}>
              <span>系列设定</span>
              <Input
                aria-label="系列设定"
                disabled={isSubmitting}
                onChange={(event) => updateDraft("series_canon", event.target.value)}
                value={draft.series_canon}
              />
            </label>
            <label style={{ display: "grid", gap: 4 }}>
              <span>人物上下文</span>
              <Input
                aria-label="人物上下文"
                disabled={isSubmitting}
                onChange={(event) => updateDraft("characters_context", event.target.value)}
                value={draft.characters_context}
              />
            </label>
            <label style={{ display: "grid", gap: 4 }}>
              <span>制作简述</span>
              <Input
                aria-label="制作简述"
                disabled={isSubmitting}
                onChange={(event) => updateDraft("production_brief", event.target.value)}
                value={draft.production_brief}
              />
            </label>
          </div>
          {createProjectMutation.isError ? (
            <Alert message="项目创建失败。请重试。" showIcon type="error" />
          ) : null}
          <div>
            <Button disabled={!draft.name.trim()} htmlType="submit" loading={isSubmitting} type="primary">
              创建项目
            </Button>
          </div>
        </form>

        {projectsQuery.isLoading ? <Skeleton active paragraph={{ rows: 4 }} title={false} /> : null}
        {projectsQuery.isError ? (
          <Alert
            action={<Button onClick={() => void projectsQuery.refetch()}>重试</Button>}
            message="项目加载失败。请重试。"
            showIcon
            type="error"
          />
        ) : null}
        {!projectsQuery.isLoading && !projectsQuery.isError && projects.length === 0 ? (
          <Typography.Text type="secondary">暂无项目。创建项目后开始章节制作。</Typography.Text>
        ) : null}
        {projects.length > 0 ? (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                background: "#ffffff",
                border: "1px solid #d9dee8",
                borderCollapse: "collapse",
                minWidth: 760,
                width: "100%",
              }}
            >
              <thead style={{ background: "#f9fafc" }}>
                <tr>
                  <th style={tableHeaderStyle}>项目</th>
                  <th style={tableHeaderStyle}>描述</th>
                  <th style={tableHeaderStyle}>章节数</th>
                  <th style={tableHeaderStyle}>最后更新</th>
                  <th style={tableHeaderStyle}>M1 进度</th>
                  <th style={tableHeaderStyle}>下一步</th>
                </tr>
              </thead>
              <tbody>
                {projects.map((project) => (
                  <tr key={project.project_id}>
                    <td style={tableCellStyle}>
                      <Link to={`/projects/${project.project_id}`}>{project.name}</Link>
                    </td>
                    <td style={tableCellStyle}>{project.description || "未填写"}</td>
                    <td style={tableCellStyle}>未加载</td>
                    <td style={tableCellStyle}>{project.updated_at}</td>
                    <td style={tableCellStyle}>打开项目查看本次会话章节</td>
                    <td style={tableCellStyle}>open_project</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </section>
  );
}

const tableHeaderStyle = {
  borderBottom: "1px solid #d9dee8",
  color: "#5f6b7a",
  fontSize: 12,
  fontWeight: 600,
  padding: "10px 12px",
  textAlign: "left" as const,
};

const tableCellStyle = {
  borderBottom: "1px solid #d9dee8",
  color: "#1f2937",
  padding: "10px 12px",
};
