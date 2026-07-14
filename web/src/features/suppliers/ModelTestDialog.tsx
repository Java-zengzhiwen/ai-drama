import { Alert, Button, Image, Input, Modal, Spin } from "antd";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  createModelTest,
  getModelTest,
  getModelTestContent,
  newIdempotencyKey,
  recoverModelTest,
  type ModelTestRead,
  type SupplierModelRead,
  type SupplierRead,
} from "./api";
import { toManagementError } from "./managementErrors";

const DEFAULT_TEXT_PROMPT = "请只回复：连接测试成功";
const DEFAULT_IMAGE_PROMPT = "一只白色陶瓷杯放在木桌上，柔和自然光，简洁写实，无文字";
const ACTIVE_STATUSES = new Set(["queued", "submitting"]);

type Props = {
  supplier: SupplierRead;
  model: SupplierModelRead;
  open: boolean;
  onClose: () => void;
};

type StoredRun = { idempotencyKey: string; testRunId?: string };

export function modelTestStorageKey(modelId: string): string {
  return `ai-drama:model-test:${modelId}`;
}

export function hasStoredModelTest(modelId: string): boolean {
  try {
    return Boolean(globalThis.sessionStorage?.getItem(modelTestStorageKey(modelId)));
  } catch {
    return false;
  }
}

function modelEtag(model: SupplierModelRead): string {
  return `"model-${model.supplier_model_id}-${model.entity_revision}"`;
}

export function ModelTestDialog({ supplier, model, open, onClose }: Props) {
  const storedRunPresent = open && hasStoredModelTest(model.supplier_model_id);
  const [prompt, setPrompt] = useState(model.capability === "image" ? DEFAULT_IMAGE_PROMPT : DEFAULT_TEXT_PROMPT);
  const [run, setRun] = useState<ModelTestRead | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [recovering, setRecovering] = useState(storedRunPresent);
  const [error, setError] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [pollAttempt, setPollAttempt] = useState(0);
  const submitLock = useRef(storedRunPresent);

  const clearStored = useCallback(() => {
    sessionStorage.removeItem(modelTestStorageKey(model.supplier_model_id));
  }, [model.supplier_model_id]);

  const loadImage = useCallback(async (current: ModelTestRead) => {
    if (current.capability !== "image" || current.status !== "completed") return;
    const blob = await getModelTestContent(current.test_run_id);
    if (typeof URL.createObjectURL === "function") {
      setImageUrl((previous) => {
        if (previous) URL.revokeObjectURL(previous);
        return URL.createObjectURL(blob);
      });
    }
  }, []);

  const acceptRun = useCallback(async (current: ModelTestRead) => {
    setError("");
    setRun(current);
    if (!ACTIVE_STATUSES.has(current.status)) {
      submitLock.current = false;
      clearStored();
      await loadImage(current);
    }
  }, [clearStored, loadImage]);

  useEffect(() => {
    if (!open) return;
    setPrompt(model.capability === "image" ? DEFAULT_IMAGE_PROMPT : DEFAULT_TEXT_PROMPT);
    setRun(null);
    setError("");
    setPollAttempt(0);
    const raw = sessionStorage.getItem(modelTestStorageKey(model.supplier_model_id));
    if (!raw) {
      submitLock.current = false;
      setRecovering(false);
      return;
    }
    submitLock.current = true;
    setRecovering(true);
    let stored: StoredRun;
    try {
      stored = JSON.parse(raw) as StoredRun;
    } catch {
      clearStored();
      submitLock.current = false;
      setRecovering(false);
      return;
    }
    let cancelled = false;
    let retryTimer: number | undefined;
    const recover = async () => {
      try {
        const current = stored.testRunId
          ? await getModelTest(stored.testRunId)
          : await recoverModelTest(model.supplier_model_id, stored.idempotencyKey);
        if (cancelled) return;
        setRecovering(false);
        await acceptRun(current);
      } catch {
        if (cancelled) return;
        setError("恢复查询暂时不可用。已保留原请求标识，将继续查询以避免重复扣费。");
        retryTimer = window.setTimeout(() => void recover(), 750);
      }
    };
    void recover();
    return () => {
      cancelled = true;
      if (retryTimer !== undefined) window.clearTimeout(retryTimer);
    };
  }, [acceptRun, clearStored, model.capability, model.supplier_model_id, open]);

  useEffect(() => {
    if (!open || !run || !ACTIVE_STATUSES.has(run.status)) return;
    const timer = window.setTimeout(() => {
      void getModelTest(run.test_run_id).then(acceptRun).catch((caught) => {
        setError(toManagementError(caught).message);
        setPollAttempt((current) => current + 1);
      });
    }, 750);
    return () => window.clearTimeout(timer);
  }, [acceptRun, open, pollAttempt, run]);

  useEffect(() => () => {
    if (imageUrl && typeof URL.revokeObjectURL === "function") URL.revokeObjectURL(imageUrl);
  }, [imageUrl]);

  async function submit() {
    if (submitLock.current || !prompt.trim()) return;
    submitLock.current = true;
    setSubmitting(true);
    setError("");
    const idempotencyKey = newIdempotencyKey("model-test");
    sessionStorage.setItem(
      modelTestStorageKey(model.supplier_model_id),
      JSON.stringify({ idempotencyKey }),
    );
    try {
      const created = await createModelTest(
        model.supplier_model_id,
        prompt.trim(),
        modelEtag(model),
        idempotencyKey,
      );
      sessionStorage.setItem(
        modelTestStorageKey(model.supplier_model_id),
        JSON.stringify({ idempotencyKey, testRunId: created.test_run_id }),
      );
      await acceptRun(created);
    } catch (caught) {
      const failure = toManagementError(caught);
      if (failure.status !== undefined && failure.status >= 400 && failure.status < 500) {
        clearStored();
        submitLock.current = false;
        setRecovering(false);
        setError(failure.message);
        return;
      }
      try {
        const recovered = await recoverModelTest(model.supplier_model_id, idempotencyKey);
        sessionStorage.setItem(
          modelTestStorageKey(model.supplier_model_id),
          JSON.stringify({ idempotencyKey, testRunId: recovered.test_run_id }),
        );
        await acceptRun(recovered);
      } catch {
        setRecovering(true);
        setError("提交结果尚未确认。已保留原请求标识；为避免重复扣费，请刷新页面继续查询。");
      }
    } finally {
      setSubmitting(false);
    }
  }

  const terminal = run && !ACTIVE_STATUSES.has(run.status);
  const locked = storedRunPresent || recovering || submitting || submitLock.current
    || Boolean(run && ACTIVE_STATUSES.has(run.status));

  return (
    <Modal
      title="测试模型连接"
      open={open}
      onCancel={locked ? undefined : onClose}
      footer={null}
      destroyOnHidden
      width={620}
      closable={!locked}
      maskClosable={!locked}
      keyboard={!locked}
    >
      <div className="model-test-dialog">
        <dl className="model-test-identity">
          <div><dt>供应商</dt><dd>{supplier.display_name}</dd></div>
          <div><dt>模型</dt><dd>{model.display_name}</dd></div>
          <div><dt>供应商模型名</dt><dd><code>{model.provider_model_name}</code></dd></div>
          <div><dt>能力</dt><dd>{model.capability === "text" ? "文本" : "图片"}</dd></div>
        </dl>
        <label className="model-test-prompt">
          <span>测试提示词</span>
          <Input.TextArea
            aria-label="测试提示词"
            value={prompt}
            maxLength={model.capability === "text" ? 4000 : 2000}
            autoSize={{ minRows: 3, maxRows: 6 }}
            onChange={(event) => setPrompt(event.target.value)}
            disabled={recovering || submitting || Boolean(run && ACTIVE_STATUSES.has(run.status))}
          />
        </label>
        <Alert type="warning" showIcon message="将向真实供应商提交 1 次生成请求，可能产生费用。" />
        {run && ACTIVE_STATUSES.has(run.status) ? (
          <div className="model-test-progress"><Spin size="small" /><span>供应商正在处理，测试编号 {run.test_run_id}</span></div>
        ) : null}
        {terminal && run.status === "completed" ? (
          <div className="model-test-result">
            {run.capability === "text" ? <pre>{run.output}</pre> : null}
            {run.capability === "image" && imageUrl ? <Image src={imageUrl} alt={`${model.display_name} 测试结果`} /> : null}
            <dl>
              {run.media_type ? <div><dt>媒体类型</dt><dd>{run.media_type}</dd></div> : null}
              {run.byte_size ? <div><dt>文件大小</dt><dd>{formatBytes(run.byte_size)}</dd></div> : null}
              <div><dt>耗时</dt><dd>{run.elapsed_ms ?? 0} ms</dd></div>
              {run.usage && Object.keys(run.usage).length ? <div><dt>Token</dt><dd>{JSON.stringify(run.usage)}</dd></div> : null}
            </dl>
          </div>
        ) : null}
        {terminal && run.status !== "completed" ? (
          <Alert type="error" message={run.error_message || "模型测试失败。"} description={run.error_code} />
        ) : null}
        {error ? <Alert type="error" message={error} /> : null}
        <div className="management-form-actions">
          <Button onClick={onClose} disabled={locked}>取消</Button>
          <Button
            type="primary"
            loading={submitting}
            disabled={!prompt.trim() || locked}
            onClick={() => void submit()}
          >确认并测试</Button>
        </div>
      </div>
    </Modal>
  );
}

function formatBytes(value: number): string {
  if (value >= 1024 * 1024) return `${Math.round(value / (1024 * 1024))} MB`;
  if (value >= 1024) return `${Math.round(value / 1024)} KB`;
  return `${value} B`;
}
