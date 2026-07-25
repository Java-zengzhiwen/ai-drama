import { Alert, Button, Image, Input, Modal, Spin } from "antd";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  createModelTest,
  getModelTest,
  getModelTestContent,
  newIdempotencyKey,
  recoverModelTest,
  type ImageQuality,
  type ImageRatio,
  type ImageSize,
  type ModelTestRead,
  type ModelTestOptions,
  type ReasoningEffort,
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

type StoredRun = {
  idempotencyKey: string;
  testRunId?: string;
  reasoningEffort?: ReasoningEffort | null;
  imageSize?: ImageSize | null;
  imageQuality?: ImageQuality | null;
  imageRatio?: ImageRatio | null;
};

const REASONING_LABELS: Record<ReasoningEffort, string> = {
  none: "无额外推理",
  low: "低",
  medium: "中",
  high: "高",
  xhigh: "超高",
  max: "最大",
};
const REASONING_VALUES = Object.keys(REASONING_LABELS) as ReasoningEffort[];
const IMAGE_SIZE_LABELS: Record<ImageSize, string> = {
  auto: "自动",
  "1K": "1K",
  "2K": "2K",
  "3K": "3K",
  "4K": "4K",
  "1024x768": "横版 1024 × 768",
  "1024x1024": "方形 1024 × 1024",
  "768x1024": "竖版 768 × 1024",
  "1024x1536": "竖版 1024 × 1536",
  "1536x1024": "横版 1536 × 1024",
};
const IMAGE_SIZE_VALUES = Object.keys(IMAGE_SIZE_LABELS) as ImageSize[];
const IMAGE_QUALITY_LABELS: Record<ImageQuality, string> = {
  auto: "自动",
  low: "低",
  medium: "中",
  high: "高",
};
const IMAGE_QUALITY_VALUES = Object.keys(IMAGE_QUALITY_LABELS) as ImageQuality[];
const IMAGE_RATIO_LABELS: Record<ImageRatio, string> = {
  "1:1": "1:1", "3:4": "3:4", "4:3": "4:3", "16:9": "16:9",
  "9:16": "9:16", "2:3": "2:3", "3:2": "3:2", "21:9": "21:9",
};
const IMAGE_RATIO_VALUES = Object.keys(IMAGE_RATIO_LABELS) as ImageRatio[];

function modelConstraints(model: SupplierModelRead): Record<string, unknown> {
  const constraints = model.definition?.constraints;
  return constraints && !Array.isArray(constraints) && typeof constraints === "object"
    ? constraints as Record<string, unknown>
    : {};
}

function declaredValues<T extends string>(
  value: unknown,
  allowed: readonly T[],
  fallback: readonly T[] = [],
): T[] {
  if (!Array.isArray(value)) return [...fallback];
  const supported = value.filter((item): item is T => (
    typeof item === "string" && allowed.includes(item as T)
  ));
  return supported.length === value.length && supported.length > 0
    ? [...new Set(supported)]
    : [...fallback];
}

function supportedReasoningEfforts(model: SupplierModelRead): ReasoningEffort[] {
  return declaredValues(
    modelConstraints(model).supported_reasoning_efforts,
    REASONING_VALUES,
    ["low", "medium", "high"],
  );
}

function modelReasoningEffort(supplier: SupplierRead, model: SupplierModelRead): ReasoningEffort {
  const supported = supportedReasoningEfforts(model);
  const values = [supplier.config_values?.reasoning_effort, modelConstraints(model).reasoning_effort];
  return values.find((value): value is ReasoningEffort => (
    typeof value === "string" && supported.includes(value as ReasoningEffort)
  )) ?? (supported.includes("medium") ? "medium" : supported[0]);
}

function supportedImageSizes(model: SupplierModelRead): ImageSize[] {
  return declaredValues(modelConstraints(model).supported_sizes, IMAGE_SIZE_VALUES);
}

function supportedImageQualities(model: SupplierModelRead): ImageQuality[] {
  return declaredValues(modelConstraints(model).supported_qualities, IMAGE_QUALITY_VALUES);
}

function supportedImageRatios(model: SupplierModelRead): ImageRatio[] {
  return declaredValues(modelConstraints(model).supported_ratios, IMAGE_RATIO_VALUES);
}

function modelImageSize(supplier: SupplierRead, model: SupplierModelRead): ImageSize {
  const supported = supportedImageSizes(model);
  const values = [supplier.config_values?.image_size, model.definition?.default_size];
  return values.find((value): value is ImageSize => (
    typeof value === "string" && supported.includes(value as ImageSize)
  )) ?? supported[0];
}

function modelImageQuality(supplier: SupplierRead, model: SupplierModelRead): ImageQuality {
  const supported = supportedImageQualities(model);
  const values = [supplier.config_values?.image_quality, modelConstraints(model).default_quality];
  return values.find((value): value is ImageQuality => (
    typeof value === "string" && supported.includes(value as ImageQuality)
  )) ?? supported[0];
}

function modelImageRatio(supplier: SupplierRead, model: SupplierModelRead): ImageRatio {
  const supported = supportedImageRatios(model);
  const values = [supplier.config_values?.image_ratio, model.definition?.default_ratio];
  return values.find((value): value is ImageRatio => (
    typeof value === "string" && supported.includes(value as ImageRatio)
  )) ?? supported[0];
}

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
  const [reasoningEffort, setReasoningEffort] = useState<ReasoningEffort | null>(null);
  const [imageSize, setImageSize] = useState<ImageSize | null>(null);
  const [imageQuality, setImageQuality] = useState<ImageQuality | null>(null);
  const [imageRatio, setImageRatio] = useState<ImageRatio | null>(null);
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
    setReasoningEffort(null);
    setImageSize(null);
    setImageQuality(null);
    setImageRatio(null);
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
    setReasoningEffort(stored.reasoningEffort ?? null);
    setImageSize(stored.imageSize ?? null);
    setImageQuality(stored.imageQuality ?? null);
    setImageRatio(stored.imageRatio ?? null);
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
    const selectedReasoningEffort = model.capability === "text" ? reasoningEffort : null;
    const selectedImageSize = model.capability === "image" ? imageSize : null;
    const selectedImageQuality = model.capability === "image" ? imageQuality : null;
    const selectedImageRatio = model.capability === "image" ? imageRatio : null;
    const options: ModelTestOptions = {};
    if (selectedReasoningEffort) options.reasoning_effort = selectedReasoningEffort;
    if (selectedImageSize) options.size = selectedImageSize;
    if (selectedImageQuality) options.quality = selectedImageQuality;
    if (selectedImageRatio) options.ratio = selectedImageRatio;
    const storedOptions = {
      idempotencyKey,
      reasoningEffort: selectedReasoningEffort,
      imageSize: selectedImageSize,
      imageQuality: selectedImageQuality,
      imageRatio: selectedImageRatio,
    };
    sessionStorage.setItem(
      modelTestStorageKey(model.supplier_model_id),
      JSON.stringify(storedOptions),
    );
    try {
      const created = await createModelTest(
        model.supplier_model_id,
        prompt.trim(),
        options,
        modelEtag(model),
        idempotencyKey,
      );
      sessionStorage.setItem(
        modelTestStorageKey(model.supplier_model_id),
        JSON.stringify({ ...storedOptions, testRunId: created.test_run_id }),
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
          JSON.stringify({ ...storedOptions, testRunId: recovered.test_run_id }),
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
  const reasoningOptions = supportedReasoningEfforts(model);
  const imageSizeOptions = supportedImageSizes(model);
  const imageQualityOptions = supportedImageQualities(model);
  const imageRatioOptions = supportedImageRatios(model);

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
        {model.capability === "text" ? (
          <label className="model-test-prompt">
            <span>本次思考深度</span>
            <select
              aria-label="本次思考深度"
              value={reasoningEffort ?? ""}
              onChange={(event) => setReasoningEffort(
                event.target.value ? event.target.value as ReasoningEffort : null,
              )}
              disabled={locked}
            >
              <option value="">跟随供应商默认（当前：{REASONING_LABELS[modelReasoningEffort(supplier, model)]}）</option>
              {reasoningOptions.map((value) => (
                <option key={value} value={value}>{REASONING_LABELS[value]}</option>
              ))}
            </select>
          </label>
        ) : null}
        {model.capability === "image" && (imageSizeOptions.length || imageQualityOptions.length || imageRatioOptions.length) ? (
          <div className="model-test-options-grid">
            {imageSizeOptions.length ? <label className="model-test-prompt">
              <span>本次图片尺寸</span>
              <select
                aria-label="本次图片尺寸"
                value={imageSize ?? ""}
                onChange={(event) => setImageSize(event.target.value ? event.target.value as ImageSize : null)}
                disabled={locked}
              >
                <option value="">跟随供应商默认（当前：{IMAGE_SIZE_LABELS[modelImageSize(supplier, model)]}）</option>
                {imageSizeOptions.map((value) => (
                  <option key={value} value={value}>{IMAGE_SIZE_LABELS[value]}</option>
                ))}
              </select>
            </label> : null}
            {imageRatioOptions.length ? <label className="model-test-prompt">
              <span>本次画幅比例</span>
              <select
                aria-label="本次画幅比例"
                value={imageRatio ?? ""}
                onChange={(event) => setImageRatio(event.target.value ? event.target.value as ImageRatio : null)}
                disabled={locked}
              >
                <option value="">跟随供应商默认（当前：{IMAGE_RATIO_LABELS[modelImageRatio(supplier, model)]}）</option>
                {imageRatioOptions.map((value) => (
                  <option key={value} value={value}>{IMAGE_RATIO_LABELS[value]}</option>
                ))}
              </select>
            </label> : null}
            {imageQualityOptions.length ? <label className="model-test-prompt">
              <span>本次图片质量</span>
              <select
                aria-label="本次图片质量"
                value={imageQuality ?? ""}
                onChange={(event) => setImageQuality(event.target.value ? event.target.value as ImageQuality : null)}
                disabled={locked}
              >
                <option value="">跟随供应商默认（当前：{IMAGE_QUALITY_LABELS[modelImageQuality(supplier, model)]}）</option>
                {imageQualityOptions.map((value) => (
                  <option key={value} value={value}>{IMAGE_QUALITY_LABELS[value]}</option>
                ))}
              </select>
            </label> : null}
          </div>
        ) : null}
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
              {run.capability === "text" && run.reasoning_effort && run.reasoning_effort in REASONING_LABELS ? <div><dt>思考深度</dt><dd>实际思考深度：{REASONING_LABELS[run.reasoning_effort as ReasoningEffort]}</dd></div> : null}
              {run.capability === "image" && run.size && run.size in IMAGE_SIZE_LABELS ? <div><dt>图片尺寸</dt><dd>实际尺寸：{IMAGE_SIZE_LABELS[run.size as ImageSize].replace(/^[^ ]+ /, "")}</dd></div> : null}
              {run.capability === "image" && run.quality && run.quality in IMAGE_QUALITY_LABELS ? <div><dt>图片质量</dt><dd>实际质量：{IMAGE_QUALITY_LABELS[run.quality as ImageQuality]}</dd></div> : null}
              {run.capability === "image" && run.ratio && run.ratio in IMAGE_RATIO_LABELS ? <div><dt>画幅比例</dt><dd>实际比例：{IMAGE_RATIO_LABELS[run.ratio as ImageRatio]}</dd></div> : null}
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
