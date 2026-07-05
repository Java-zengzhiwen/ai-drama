import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Input, Typography } from "antd";
import { type FormEvent, useEffect, useState } from "react";
import type { ChapterRead } from "../projects/api";
import { createSourceRevision } from "../script/api";

type SourceTabProps = {
  chapter: ChapterRead;
};

type ApiError = {
  response?: {
    data?: {
      error_code?: string;
      error_message?: string;
    };
  };
};

export function SourceTab({ chapter }: SourceTabProps) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState(chapter.source_text ?? "");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setDraft(chapter.source_text ?? "");
  }, [chapter.source_text]);

  const saveMutation = useMutation({
    mutationFn: (content: string) => createSourceRevision(chapter.chapter_id, { content }),
    onSuccess: (revision, content) => {
      queryClient.setQueryData<ChapterRead>(["chapter", chapter.chapter_id], (current) => ({
        ...(current ?? chapter),
        current_source_revision_id: revision.source_revision_id,
        source_text: content,
      }));
      void queryClient.invalidateQueries({ queryKey: ["chapter-status", chapter.chapter_id] });
      setSaved(true);
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    saveMutation.mutate(draft.trim());
  }

  return (
    <form aria-label="原文编辑" onSubmit={submit} style={{ display: "grid", gap: 12 }}>
      {!chapter.source_text ? (
        <Typography.Text type="secondary">暂无小说原文。粘贴正文后才能生成剧本。</Typography.Text>
      ) : null}
      <label style={{ display: "grid", gap: 6 }}>
        <span>小说原文</span>
        <Input.TextArea
          aria-label="小说原文"
          autoSize={{ minRows: 12 }}
          disabled={saveMutation.isPending}
          onChange={(event) => {
            setDraft(event.target.value);
            setSaved(false);
          }}
          value={draft}
        />
      </label>
      <div>
        <Button
          disabled={!draft.trim()}
          htmlType="submit"
          loading={saveMutation.isPending}
          type="primary"
        >
          保存原文
        </Button>
      </div>
      {saved ? <Alert message="原文已保存为新版本。" showIcon type="success" /> : null}
      {saveMutation.isError ? (
        <WorkflowErrorAlert
          error={saveMutation.error}
          fallbackMessage="原文保存失败。请重试。"
          onRetry={() => {
            if (saveMutation.variables) {
              saveMutation.mutate(saveMutation.variables);
            }
          }}
        />
      ) : null}
    </form>
  );
}

function WorkflowErrorAlert({
  error,
  fallbackMessage,
  onRetry,
}: {
  error: unknown;
  fallbackMessage: string;
  onRetry: () => void;
}) {
  const details = getApiErrorDetails(error, fallbackMessage);

  return (
    <Alert
      action={<Button onClick={onRetry}>重试</Button>}
      description={details.code || undefined}
      message={details.message}
      showIcon
      type="error"
    />
  );
}

function getApiErrorDetails(error: unknown, fallbackMessage: string) {
  const data = (error as ApiError | undefined)?.response?.data;
  return {
    code: data?.error_code ?? "",
    message: data?.error_message ?? fallbackMessage,
  };
}
