import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Input, Skeleton, Typography } from "antd";
import { type FormEvent, useState } from "react";
import { apiClient } from "../../api/client";

type AgnesSettingsStatus = {
  configured: boolean;
  masked_suffix: string;
};

async function getAgnesSettings(): Promise<AgnesSettingsStatus> {
  const response = await apiClient.get<AgnesSettingsStatus>("/settings/agnes");
  return response.data;
}

async function saveAgnesApiKey(apiKey: string): Promise<AgnesSettingsStatus> {
  const response = await apiClient.put<AgnesSettingsStatus>("/settings/agnes", { api_key: apiKey });
  return response.data;
}

async function deleteAgnesApiKey(): Promise<AgnesSettingsStatus> {
  const response = await apiClient.delete<AgnesSettingsStatus>("/settings/agnes");
  return response.data;
}

export function AgnesSettingsPage() {
  const queryClient = useQueryClient();
  const [apiKey, setApiKey] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const settingsQuery = useQuery({
    queryKey: ["settings", "agnes"],
    queryFn: getAgnesSettings,
  });
  const deleteMutation = useMutation({
    mutationFn: deleteAgnesApiKey,
    onSuccess: (status) => {
      queryClient.setQueryData<AgnesSettingsStatus>(["settings", "agnes"], status);
      setApiKey("");
    },
  });

  async function submitApiKey(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = apiKey;
    if (!value.trim()) {
      return;
    }
    setIsSaving(true);
    setSaveError(false);
    try {
      const status = await saveAgnesApiKey(value);
      queryClient.setQueryData<AgnesSettingsStatus>(["settings", "agnes"], status);
      setApiKey("");
    } catch {
      setSaveError(true);
    } finally {
      setIsSaving(false);
    }
  }

  const status = settingsQuery.data ?? { configured: false, masked_suffix: "" };
  const isDeleting = deleteMutation.isPending;
  const isBusy = isSaving || isDeleting;

  return (
    <section aria-labelledby="agnes-settings-title">
      <div style={{ display: "grid", gap: 20, maxWidth: 720 }}>
        <div>
          <Typography.Title id="agnes-settings-title" level={1} style={{ fontSize: 22, margin: 0 }}>
            Agnes 设置
          </Typography.Title>
          <Typography.Text type="secondary">本地保存 Agnes API Key，仅后端可读取完整值。</Typography.Text>
        </div>

        {settingsQuery.isLoading ? <Skeleton active paragraph={{ rows: 3 }} title={false} /> : null}
        {settingsQuery.isError ? (
          <Alert
            action={<Button onClick={() => void settingsQuery.refetch()}>重试</Button>}
            message="Agnes 设置加载失败。请重试。"
            showIcon
            type="error"
          />
        ) : null}

        {!settingsQuery.isLoading && !settingsQuery.isError ? (
          <>
            <div
              style={{
                background: "#ffffff",
                border: "1px solid #d9dee8",
                borderRadius: 6,
                display: "grid",
                gap: 8,
                padding: 16,
              }}
            >
              <Typography.Text strong>{status.configured ? "已配置" : "未配置"}</Typography.Text>
              <Typography.Text type="secondary">
                {status.configured ? `****${status.masked_suffix}` : "未保存 Agnes API Key"}
              </Typography.Text>
            </div>

            <form
              aria-label="Agnes API Key 设置"
              onSubmit={submitApiKey}
              style={{
                background: "#ffffff",
                border: "1px solid #d9dee8",
                borderRadius: 6,
                display: "grid",
                gap: 12,
                padding: 16,
              }}
            >
              <label style={{ display: "grid", gap: 4 }}>
                <span>Agnes API Key</span>
                <Input.Password
                  aria-label="Agnes API Key"
                  autoComplete="off"
                  disabled={isBusy}
                  onChange={(event) => setApiKey(event.target.value)}
                  value={apiKey}
                />
              </label>

              {saveError ? (
                <Alert message="Agnes API Key 保存失败。请重试。" showIcon type="error" />
              ) : null}
              {deleteMutation.isError ? (
                <Alert message="Agnes API Key 移除失败。请重试。" showIcon type="error" />
              ) : null}

              <div style={{ display: "flex", gap: 8 }}>
                <Button
                  aria-label="保存"
                  disabled={!apiKey.trim()}
                  htmlType="submit"
                  loading={isSaving}
                  type="primary"
                >
                  保存
                </Button>
                <Button
                  aria-label="移除"
                  danger
                  disabled={!status.configured || isBusy}
                  loading={isDeleting}
                  onClick={() => deleteMutation.mutate()}
                  type="default"
                >
                  移除
                </Button>
              </div>
            </form>
          </>
        ) : null}
      </div>
    </section>
  );
}
