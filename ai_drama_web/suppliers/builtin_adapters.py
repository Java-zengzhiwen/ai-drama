import uuid
import json
import hashlib

from .compiler import compile_supplier


def _model_id(slug, capability):
    return uuid.uuid5(uuid.NAMESPACE_URL, f"ai-drama:{slug}:{capability}:builtin").hex


OPENAI_SOURCE = f'''
/**
 * OpenAI Compatible 内置适配器
 *
 * AI 生成适配代码步骤：把本文件与供应商官方文档交给 AI，说明只修改接口映射，
 * 不改变 adapterContractVersion、helperApiVersion、稳定模型 ID 或规范化返回结构。
 * 不要提供真实 API Key；密钥由网页保存并通过 payload.credential 注入。
 * 网络只能经过 helpers.http.request，配置只能读取 payload.config。
 * textRequest 将平台中立的提示词转换为 Chat Completions 请求，并统一 token 字段。
 */
export const vendor = {{
  id:"openai", version:"m6c-2-comments", name:"OpenAI Compatible", author:"AI Drama",
  adapterContractVersion:"ai-drama-supplier-v1", helperApiVersion:"ai-drama-helper-v1",
  rateLimitBucketKey:"openai-text", inputs:[], inputValues:{{}},
  models:[{{supplierModelId:"{_model_id('openai','text')}",providerModelName:"gpt-4.1",displayName:"OpenAI Text",capability:"text"}}]
}};
export async function textRequest(payload, helpers) {{
  const base = String(payload.config.base_url || "").replace(/[/]$/, "");
  const body = {{model:payload.model,messages:payload.request.messages || [{{role:"user",content:String(payload.request.prompt || "")}}]}};
  const raw = await helpers.http.request({{method:"POST",url:base+"/chat/completions",headers:{{Authorization:`Bearer ${{payload.credential}}`,"Content-Type":"application/json"}},body}});
  const choice = raw.choices && raw.choices[0];
  if (!choice || !choice.message) throw Object.assign(new Error("PROVIDER_RESPONSE_MALFORMED"),{{code:"PROVIDER_RESPONSE_MALFORMED"}});
  return {{output:String(choice.message.content || ""),usage:{{input_tokens:Number(raw.usage?.prompt_tokens||0),output_tokens:Number(raw.usage?.completion_tokens||0),total_tokens:Number(raw.usage?.total_tokens||0)}}}};
}}
'''


AGNES_SOURCE = f'''
/**
 * Agnes 内置图片与视频适配器
 *
 * AI 生成适配代码步骤：把本文件、Agnes 官方文档和需要的能力交给 AI，只调整已确认字段。
 * 不要提供真实 API Key、Bearer 或签名链接；密钥仅从 payload.credential 读取且不得记录。
 * 所有提交、状态查询和结果下载都必须经过 helpers.http.request。
 * 图片生成先取得结果 URL，再由受控 helper 下载为本地媒体引用。
 * 普通视频模式严格 0–1 张输入图；keyframes 模式严格 2–3 张有序关键帧。
 * 视频创建后必须使用 video_id 查询，不得使用 task_id；完成后再下载视频结果。
 * 保持 providerModelName、错误码和规范化状态不变，未知状态必须失败关闭。
 */
export const vendor = {{
  id:"agnes", version:"m6c-4-image-video-contract", name:"Agnes", author:"AI Drama",
  adapterContractVersion:"ai-drama-supplier-v1", helperApiVersion:"ai-drama-helper-v1",
  rateLimitBucketKey:"agnes-generation", inputs:[], inputValues:{{}},
  models:[
    {{supplierModelId:"{_model_id('agnes','image')}",providerModelName:"agnes-image-2.1-flash",displayName:"Agnes Image",capability:"image",default_size:"1K",default_ratio:"1:1",constraints:{{supported_sizes:["1K","2K","3K","4K","1024x768","1024x1024","768x1024","1024x1536","1536x1024"],supported_ratios:["1:1","3:4","4:3","16:9","9:16","2:3","3:2","21:9"]}}}},
    {{supplierModelId:"{_model_id('agnes','video')}",providerModelName:"agnes-video-v2.0",displayName:"Agnes Video",capability:"video"}}
  ]
}};
const headers = payload => ({{Authorization:`Bearer ${{payload.credential}}`,"Content-Type":"application/json"}});
const fail = code => {{ throw Object.assign(new Error(code), {{code}}); }};
const imageSizes = new Set(["1K","2K","3K","4K","1024x768","1024x1024","768x1024","1024x1536","1536x1024"]);
const imageRatios = new Set(["1:1","3:4","4:3","16:9","9:16","2:3","3:2","21:9"]);
export async function imageRequest(payload, helpers) {{
  const size = payload.request.size || payload.constraints?.size || "1K";
  const ratio = payload.request.ratio || payload.constraints?.ratio || "1:1";
  if (!imageSizes.has(size)) fail("INVALID_IMAGE_SIZE");
  if (!imageRatios.has(ratio)) fail("INVALID_IMAGE_RATIO");
  const body = {{model:payload.model,prompt:payload.request.prompt,size,ratio,extra_body:{{response_format:"url"}}}};
  if (payload.request.input_images?.length) body.extra_body.image = payload.request.input_images;
  const raw = await helpers.http.request({{method:"POST",url:payload.config.image_endpoint,headers:headers(payload),body}});
  const url = raw.data?.[0]?.url;
  if (!url) throw Object.assign(new Error("PROVIDER_RESPONSE_MALFORMED"),{{code:"PROVIDER_RESPONSE_MALFORMED"}});
  const bytes = await helpers.http.request({{method:"GET",url,responseType:"bytes"}});
  return {{provider_job_id:`image-${{raw.created||"result"}}`,url,...bytes}};
}}
export async function videoSubmit(payload, helpers) {{
  const images = payload.request.input_images || [];
  const mode = payload.request.parameters?.mode;
  if (mode !== undefined && !["std","pro","keyframes"].includes(mode))
    fail("INVALID_VIDEO_MODE");
  if (mode === "keyframes" ? (images.length < 2 || images.length > 3) : images.length > 1)
    throw Object.assign(new Error("INVALID_INPUT_IMAGES"),{{code:"INVALID_INPUT_IMAGES"}});
  const numFrames = payload.request.parameters?.num_frames;
  if (numFrames !== undefined && (!Number.isInteger(numFrames) || numFrames < 1 || numFrames > 441 || (numFrames - 1) % 8 !== 0))
    fail("INVALID_VIDEO_NUM_FRAMES");
  const frameRate = payload.request.parameters?.frame_rate;
  if (frameRate !== undefined && (!Number.isInteger(frameRate) || frameRate < 1 || frameRate > 60))
    fail("INVALID_VIDEO_FRAME_RATE");
  const body = {{model:payload.model,prompt:payload.request.prompt}};
  if (payload.request.negative_prompt) body.negative_prompt=payload.request.negative_prompt;
  for (const key of ["frame_rate","num_frames","seed"]) if (payload.request.parameters?.[key] !== undefined) body[key]=payload.request.parameters[key];
  if (images.length === 1) body.image=images[0];
  if (mode === "keyframes") body.extra_body={{image:images,mode}};
  const raw = await helpers.http.request({{method:"POST",url:payload.config.video_endpoint,headers:headers(payload),body}});
  const video_id = raw.video_id || raw.data?.video_id;
  if (!video_id) throw Object.assign(new Error("PROVIDER_VIDEO_ID_MISSING"),{{code:"PROVIDER_VIDEO_ID_MISSING"}});
  return {{video_id:String(video_id),status:"queued"}};
}}
export async function videoPoll(payload, helpers) {{
  const raw = await helpers.http.request({{method:"GET",url:payload.config.video_status_endpoint,headers:headers(payload),query:{{video_id:payload.request.video_id}}}});
  const value=String(raw.status||raw.data?.status||"pending").toLowerCase();
  const status=({{pending:"queued",queued:"queued",processing:"polling",running:"polling",succeeded:"completed",completed:"completed",failed:"failed",error:"failed"}})[value];
  if (!status) throw Object.assign(new Error("PROVIDER_STATUS_INVALID"),{{code:"PROVIDER_STATUS_INVALID"}});
  return {{video_id:payload.request.video_id,status}};
}}
export async function videoFetch(payload, helpers) {{
  const raw = await helpers.http.request({{method:"GET",url:payload.config.video_status_endpoint,headers:headers(payload),query:{{video_id:payload.request.video_id}}}});
  const url=raw.metadata?.url||raw.url||raw.video_url||raw.data?.url||raw.data?.video_url;
  if (!url) throw Object.assign(new Error("RESULT_MISSING"),{{code:"RESULT_MISSING"}});
  const bytes=await helpers.http.request({{method:"GET",url,responseType:"bytes"}});
  return {{video_id:payload.request.video_id,url,...bytes}};
}}
'''


def install_builtin_adapters(store):
    installed = 0
    for slug, source in (("openai", OPENAI_SOURCE), ("agnes", AGNES_SOURCE)):
        supplier = next(item for item in store.list_suppliers() if item.slug == slug)
        current = store.get_supplier_version(supplier.current_supplier_version_id)
        source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
        if (
            current is not None
            and not current.built_in
            and not current.worker_runtime_version.startswith("unavailable")
        ):
            continue
        if (
            current is not None
            and not current.worker_runtime_version.startswith("unavailable")
            and current.source_hash == source_hash
        ):
            continue
        artifact = compile_supplier(source, runtime_store=store.runtime)
        store.replace_supplier_version(
            supplier.supplier_id,
            source_object_id=artifact.source_object_id, source_hash=artifact.source_hash,
            compiled_artifact_object_id=artifact.compiled_artifact_object_id,
            compiled_artifact_hash=artifact.compiled_artifact_hash,
            manifest_hash=artifact.manifest_hash, manifest=artifact.vendor,
            adapter_contract_version=artifact.adapter_contract_version,
            worker_protocol_version="1", worker_runtime_version=artifact.worker_runtime_version,
            compiler_name=artifact.compiler_name, compiler_version=artifact.compiler_version,
            compiler_options_hash=artifact.compiler_options_hash,
            helper_api_version=artifact.helper_api_version,
            rate_limit_bucket_key=artifact.vendor["rateLimitBucketKey"],
            expected_revision=supplier.revision, built_in=True,
        )
        supplier = store.get_supplier(supplier.supplier_id)
        config = store.get_config_revision(supplier.current_config_revision_id)
        if not config.config_object_id:
            defaults = (
                {"base_url": "https://api.openai.com/v1"}
                if slug == "openai"
                else {
                    "image_endpoint": "https://apihub.agnes-ai.com/v1/images/generations",
                    "video_endpoint": "https://apihub.agnes-ai.com/v1/videos",
                    "video_status_endpoint": "https://apihub.agnes-ai.com/agnesapi",
                    "result_origins": ["https://platform-outputs.agnes-ai.space"],
                }
            )
            raw = json.dumps(defaults, sort_keys=True, separators=(",", ":"))
            object_id = store.runtime.write_text_object(raw)
            store.replace_supplier_config(
                supplier.supplier_id,
                config_object_id=object_id,
                config_hash=hashlib.sha256(raw.encode()).hexdigest(),
                expected_revision=supplier.config_revision,
            )
        installed += 1
    return installed
