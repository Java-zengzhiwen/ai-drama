import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Input, InputNumber, Skeleton, Typography } from "antd";
import { type FormEvent, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { createChapter, getChapterStatus, getProject, listProjectChapters, type ChapterRead } from "./api";

export function ProjectDashboardPage() {
  const { projectId = "" } = useParams();
  const queryClient = useQueryClient();
  const [chapterTitle, setChapterTitle] = useState("");
  const [chapterPosition, setChapterPosition] = useState(1);
  const projectQuery = useQuery({
    enabled: Boolean(projectId),
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });
  const chaptersQuery = useQuery({
    enabled: Boolean(projectId),
    queryKey: ["project-chapters", projectId],
    queryFn: () => listProjectChapters(projectId),
  });
  const createChapterMutation = useMutation({
    mutationFn: () =>
      createChapter(projectId, {
        title: chapterTitle.trim(),
        position: chapterPosition,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["project-chapters", projectId] });
      setChapterTitle("");
      setChapterPosition((current) => current + 1);
    },
  });

  function submitChapter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createChapterMutation.mutate();
  }

  if (projectQuery.isLoading) {
    return <Skeleton active paragraph={{ rows: 5 }} />;
  }

  if (projectQuery.isError || !projectQuery.data) {
    return (
      <Alert
        action={<Button onClick={() => void projectQuery.refetch()}>重试</Button>}
        message="项目加载失败。请重试。"
        showIcon
        type="error"
      />
    );
  }

  const project = projectQuery.data;
  const isSubmitting = createChapterMutation.isPending;
  const chapters = chaptersQuery.data ?? [];

  return (
    <section aria-labelledby="project-dashboard-title">
      <div style={{ display: "grid", gap: 20 }}>
        <div>
          <Typography.Title id="project-dashboard-title" level={1} style={{ fontSize: 22, margin: 0 }}>
            {project.name}
          </Typography.Title>
          <Typography.Text type="secondary">{project.description || "暂无项目描述"}</Typography.Text>
        </div>

        <dl
          style={{
            background: "#ffffff",
            border: "1px solid #d9dee8",
            borderRadius: 6,
            display: "grid",
            gap: 12,
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            margin: 0,
            padding: 16,
          }}
        >
          <MetadataItem label="系列设定" value={project.series_canon || "未填写"} />
          <MetadataItem label="人物上下文" value={project.characters_context || "未填写"} />
          <MetadataItem label="制作简述" value={project.production_brief || "未填写"} />
        </dl>

        <form
          aria-label="添加章节"
          onSubmit={submitChapter}
          style={{
            alignItems: "end",
            background: "#ffffff",
            border: "1px solid #d9dee8",
            borderRadius: 6,
            display: "grid",
            gap: 12,
            gridTemplateColumns: "minmax(220px, 1fr) 140px auto",
            padding: 16,
          }}
        >
          <label style={{ display: "grid", gap: 4 }}>
            <span>章节标题</span>
            <Input
              aria-label="章节标题"
              disabled={isSubmitting}
              onChange={(event) => setChapterTitle(event.target.value)}
              value={chapterTitle}
            />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>章节序号</span>
            <InputNumber
              aria-label="章节序号"
              disabled={isSubmitting}
              min={1}
              onChange={(value) => setChapterPosition(Number(value ?? 1))}
              style={{ width: "100%" }}
              value={chapterPosition}
            />
          </label>
          <Button disabled={!chapterTitle.trim()} htmlType="submit" loading={isSubmitting} type="primary">
            添加章节
          </Button>
          {createChapterMutation.isError ? (
            <Alert message="章节创建失败。请重试。" showIcon style={{ gridColumn: "1 / -1" }} type="error" />
          ) : null}
        </form>

        {chaptersQuery.isLoading ? (
          <Skeleton active paragraph={{ rows: 3 }} title={false} />
        ) : chaptersQuery.isError ? (
          <Alert
            action={<Button onClick={() => void chaptersQuery.refetch()}>重试</Button>}
            message="章节列表加载失败。请重试。"
            showIcon
            type="error"
          />
        ) : chapters.length === 0 ? (
          <Typography.Text type="secondary">暂无章节。添加章节后开始制作。</Typography.Text>
        ) : (
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
                  <th style={tableHeaderStyle}>序号</th>
                  <th style={tableHeaderStyle}>章节</th>
                  <th style={tableHeaderStyle}>状态</th>
                  <th style={tableHeaderStyle}>阻塞原因</th>
                  <th style={tableHeaderStyle}>下一步</th>
                </tr>
              </thead>
              <tbody>
                {chapters.map((chapter) => (
                  <ChapterRow chapter={chapter} key={chapter.chapter_id} projectId={project.project_id} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}

function MetadataItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt style={{ color: "#5f6b7a", fontSize: 12, marginBottom: 4 }}>{label}</dt>
      <dd style={{ color: "#1f2937", margin: 0 }}>{value}</dd>
    </div>
  );
}

function ChapterRow({ chapter, projectId }: { chapter: ChapterRead; projectId: string }) {
  const statusQuery = useQuery({
    queryKey: ["chapter-status", chapter.chapter_id],
    queryFn: () => getChapterStatus(chapter.chapter_id),
  });
  const status = statusQuery.data;

  return (
    <tr>
      <td style={tableCellStyle}>{chapter.position}</td>
      <td style={tableCellStyle}>
        <Link to={`/projects/${projectId}/chapters/${chapter.chapter_id}`}>{chapter.title}</Link>
      </td>
      <td style={tableCellStyle}>{statusQuery.isLoading ? "加载状态" : status?.status ?? "error"}</td>
      <td style={tableCellStyle}>{status?.blocking_reason || "无"}</td>
      <td style={tableCellStyle}>{status?.next_action ?? "retry_status"}</td>
    </tr>
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
