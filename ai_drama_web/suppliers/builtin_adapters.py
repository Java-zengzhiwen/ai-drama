import uuid
import json
import hashlib

from .compiler import compile_supplier


def _model_id(slug, capability):
    return uuid.uuid5(uuid.NAMESPACE_URL, f"ai-drama:{slug}:{capability}:builtin").hex


OPENAI_SOURCE = f'''
export const vendor = {{
  id:"openai", version:"m6c-1", name:"OpenAI Compatible", author:"AI Drama",
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
export const vendor = {{
  id:"agnes", version:"m6c-1", name:"Agnes", author:"AI Drama",
  adapterContractVersion:"ai-drama-supplier-v1", helperApiVersion:"ai-drama-helper-v1",
  rateLimitBucketKey:"agnes-generation", inputs:[], inputValues:{{}},
  models:[
    {{supplierModelId:"{_model_id('agnes','image')}",providerModelName:"agnes-image-2.1-flash",displayName:"Agnes Image",capability:"image"}},
    {{supplierModelId:"{_model_id('agnes','video')}",providerModelName:"agnes-video-v2.0",displayName:"Agnes Video",capability:"video"}}
  ]
}};
const headers = payload => ({{Authorization:`Bearer ${{payload.credential}}`,"Content-Type":"application/json"}});
export async function imageRequest(payload, helpers) {{
  const body = {{model:payload.model,prompt:payload.request.prompt,size:payload.request.size,extra_body:{{response_format:"url"}}}};
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
  if (mode === "keyframes" ? (images.length < 2 || images.length > 3) : images.length > 1)
    throw Object.assign(new Error("INVALID_INPUT_IMAGES"),{{code:"INVALID_INPUT_IMAGES"}});
  const body = {{model:payload.model,prompt:payload.request.prompt}};
  if (payload.request.negative_prompt) body.negative_prompt=payload.request.negative_prompt;
  for (const key of ["frame_rate","num_frames","seed"]) if (payload.request.parameters?.[key] !== undefined) body[key]=payload.request.parameters[key];
  if (images.length === 1) body.image=images[0];
  if (mode === "keyframes") body.extra_body={{image:images,mode}};
  const raw = await helpers.http.request({{method:"POST",url:payload.config.video_endpoint,headers:headers(payload),body}});
  const video_id = raw.video_id || raw.id || raw.data?.video_id;
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
  const url=raw.url||raw.video_url||raw.data?.url||raw.data?.video_url;
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
        if current is not None and not current.worker_runtime_version.startswith("unavailable"):
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
