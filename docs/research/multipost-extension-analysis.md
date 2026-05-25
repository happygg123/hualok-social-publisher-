# MultiPost-Extension Research Notes

Source repo: https://github.com/leaperone/MultiPost-Extension
Inspected commit: `9fb4dd2` (`2026-05-22`, docs update)

## Bottom line

MultiPost-Extension is more complete as a **browser extension publishing product**. It should not replace HuaLok's local dashboard/queue/database, but it is very valuable as a reference for the **platform automation layer**.

Recommended direction:

```text
HuaLok FastAPI dashboard + SQLite queue + logs
  -> publisher engine interface
    -> existing Python/Playwright sau engine
    -> optional MultiPost-style browser-extension bridge later
```

## What MultiPost has that we should reuse conceptually

- Mature Chrome Extension architecture via Plasmo MV3.
- Platform maps by content type:
  - `src/sync/video.ts`
  - `src/sync/dynamic.ts`
  - `src/sync/article.ts`
  - `src/sync/podcast.ts`
- Per-platform DOM injection functions.
- Account detection modules in `src/sync/account/`.
- Common payload schema in `src/sync/common.ts`.
- Support for `scheduledPublishTime` on video/article/dynamic data.
- Extension message API:
  - `MULTIPOST_EXTENSION_PUBLISH`
  - `MULTIPOST_EXTENSION_PUBLISH_NOW`
  - `MULTIPOST_EXTENSION_PLATFORMS`
  - `MULTIPOST_EXTENSION_GET_ACCOUNT_INFOS`

## Key schema to mirror

From `src/sync/common.ts`:

```ts
interface SyncData {
  platforms: SyncDataPlatform[];
  isAutoPublish: boolean;
  data: DynamicData | ArticleData | VideoData | PodcastData;
}

interface VideoData {
  title: string;
  content: string;
  video: FileData;
  tags?: string[];
  cover?: FileData;
  verticalCover?: FileData;
  horizontalCover?: FileData;
  scheduledPublishTime?: number;
  category?: string | number;
  original?: boolean;
  description?: string;
}
```

For HuaLok, we can map one job to this style:

```python
{
  "platforms": [{"name": "VIDEO_DOUYIN"}, {"name": "VIDEO_REDNOTE"}, {"name": "VIDEO_WEIXINCHANNEL"}],
  "isAutoPublish": True,
  "data": {
    "title": job.title,
    "content": job.desc,
    "video": {"name": video.name, "url": local_file_url, "type": "video/mp4"},
    "cover": {"name": cover.name, "url": local_file_url, "type": "image/png"},
    "tags": split_tags(job.tags),
    "scheduledPublishTime": timestamp_ms(job.schedule_time),
    "original": bool(job.tencent_declare_original),
  },
}
```

## Platform analysis for HuaLok priority platforms

### 1. 视频号 / WeChat Channel

MultiPost file:

```text
src/sync/video/weixinchannel.ts
```

Relevant capabilities:

- Opens:
  ```text
  https://channels.weixin.qq.com/platform/post/create
  ```
- Handles `wujie-app` Shadow DOM.
- Recursive Shadow DOM element search.
- Uploads video using `input[type="file"]` + `DataTransfer`.
- Fills title selector:
  ```text
  input[placeholder="概括视频主要内容，字数建议6-16个字符"]
  ```
- Fills description selector:
  ```text
  div[data-placeholder="添加描述"]
  ```
- Adds tags by paste + Enter.
- Uploads cover with:
  ```text
  div.video-cover div.tag-inner
  div.crop-area input[type='file']
  div.finder-dialog-footer button -> 确定 / 确认
  ```
- Has scheduled publish helper:
  ```text
  label text == 定时
  input[placeholder="请选择发表时间"]
  publish button text == 发表
  ```
- Has original declaration flow:
  ```text
  input[type="checkbox"][class="ant-checkbox-input"]
  div.declare-body-wrapper input[type="checkbox"][class="ant-checkbox-input"]
  button text == 声明原创
  ```

HuaLok action items:

- Port the Shadow DOM query helper into Python Playwright equivalent.
- Re-check video号 selectors against current site before replacing existing code.
- Keep original declaration as post-publish/optional because it has historically been unstable.
- Reuse the cover dialog sequence: `裁剪封面图` -> `确定` -> `确认`.

### 2. 抖音 / Douyin

MultiPost file:

```text
src/sync/video/douyin.ts
```

Relevant capabilities:

- Opens:
  ```text
  https://creator.douyin.com/creator-micro/content/upload
  ```
- Uploads video using first `input[type=file]`.
- Title selector:
  ```text
  input[placeholder*="作品标题"]
  ```
- Description editor selector:
  ```text
  div.zone-container.editor-kit-container.editor.editor-comp-publish[contenteditable="true"]
  ```
- Adds tags by paste text: ` #tag`.
- Cover upload selector path:
  ```text
  div.content-upload-new
  input[type="file"].semi-upload-hidden-input
  button text == 完成
  ```
- Scheduled publish:
  ```text
  label includes 定时发布
  input[format="yyyy-MM-dd HH:mm"]
  button text == 发布
  ```

HuaLok action items:

- Compare with current `uploader/douyin_uploader/main.py`.
- Add more resilient selectors around title/editor/cover.
- Confirm current platform accepts seconds or only minute precision. MultiPost formats `yyyy-MM-dd HH:mm`.

### 3. 小红书 / Rednote

MultiPost file:

```text
src/sync/video/rednote.ts
```

Relevant capabilities:

- Opens:
  ```text
  https://creator.xiaohongshu.com/publish/publish?target=video
  ```
- Uploads video using:
  ```text
  input[type="file"]
  ```
- Title selector:
  ```text
  input[type="text"]
  ```
- Content editor selector:
  ```text
  div[contenteditable="true"]
  ```
- Tags: paste `#tag` then dispatch Enter.
- Cover upload:
  ```text
  div.noCover.uploadCover
  input[accept='image/png, image/jpeg, image/*']
  span text == 确定
  ```
- Scheduled publish:
  ```text
  label includes 定时发布
  input[placeholder="选择日期和时间"]
  button text includes 发布
  ```
- It adds `+8h` before ISO formatting, which should be reviewed carefully. HuaLok should not blindly copy that because our schedule time is already local China time.

HuaLok action items:

- Keep our fixed upload-complete waiting logic; MultiPost uses short sleeps and may be less reliable for large videos.
- Borrow tag-confirmation behavior: paste tag and dispatch Enter.
- Verify XHS timezone handling with real scheduled publish.

## Architecture comparison

### MultiPost strengths

- More platform coverage.
- Better organized platform registry.
- Extension UI already mature.
- Natural reuse of existing browser logged-in sessions.
- Can be called from a web page via extension messaging if trust-domain flow is configured.

### MultiPost weaknesses for HuaLok

- Not a local batch scheduler by itself.
- No SQLite job database.
- No queue state, retry policy, or structured log history like HuaLok needs.
- File input uses `fetch(file.url)` and `File` objects; HuaLok needs to serve local files over localhost or convert paths into browser-accessible URLs.
- Browser extension messaging requires extension installed and trusted domain setup.
- DOM selectors can still break when platforms update.

## Integration options

### Option A — Selector/logic migration only (recommended first)

Keep current Python Playwright engine, but port useful selectors and wait strategies from MultiPost into:

```text
uploader/tencent_uploader/main.py
uploader/douyin_uploader/main.py
uploader/xiaohongshu_uploader/main.py
```

Pros:
- Fastest.
- No extension install needed.
- Keeps HuaLok current dashboard/queue/logs.

Cons:
- Still maintains Python browser automation.

### Option B — Local extension bridge

Install a HuaLok/MultiPost-style extension into user's Chrome, then HuaLok dashboard sends publish payload to extension.

Requirements:

- Serve video/cover files from HuaLok FastAPI, e.g. `/media-file/{job_id}/video`.
- Add `localhost` as trusted domain in extension.
- Add a browser bridge JS module in HuaLok dashboard:
  - detect extension
  - send `MULTIPOST_EXTENSION_PUBLISH_NOW`
  - receive tabs/status if available
- Add job engine type:
  ```text
  engine = sau | extension
  ```

Pros:
- Better reuse of logged-in normal Chrome.
- Can leverage MultiPost platform scripts directly.
- More future platforms.

Cons:
- More moving parts.
- Harder to guarantee logs/screenshots unless extension reports back.
- Requires extension installation/configuration.

### Option C — Full replacement with MultiPost

Not recommended. We would lose HuaLok queue/database/logging and still need to rebuild batch operations around it.

## Recommended next implementation sequence

1. Add a `PlatformPayload` builder in HuaLok that converts jobs into MultiPost-compatible video payloads.
2. Add local file serving endpoints for video and cover files.
3. Add a `publisher_engines/` abstraction:
   - `sau_engine.py` for current CLI/Playwright route.
   - `multipost_payload.py` for payload conversion first.
   - later `extension_engine.py` for browser extension messaging.
4. Port selector improvements into Python uploaders:
   - video号 Shadow DOM helper + cover flow + scheduled publish selectors.
   - 抖音 cover/title/editor selectors.
   - 小红书 tag confirmation and scheduled publish checks.
5. Add UI field `engine` only after the extension bridge actually works. Until then, keep it internal.

## Immediate code migration checklist

### 视频号

- [ ] Implement recursive Shadow DOM query helper in Playwright.
- [ ] Add selectors from `weixinchannel.ts` as fallbacks.
- [ ] Verify scheduled publish field `input[placeholder="请选择发表时间"]`.
- [ ] Keep original declaration optional/post-publish.
- [ ] Re-test cover upload: crop dialog -> 确定 -> 确认.

### 抖音

- [ ] Add fallback title selector `input[placeholder*="作品标题"]`.
- [ ] Add editor selector `div.zone-container...contenteditable="true"`.
- [ ] Add cover selector `input[type="file"].semi-upload-hidden-input`.
- [x] Add scheduled field fallback `input[format="yyyy-MM-dd HH:mm"]`.

### 小红书

- [ ] Add tag Enter confirmation after paste.
- [ ] Add cover selector `div.noCover.uploadCover`.
- [ ] Add cover input selector `input[accept='image/png, image/jpeg, image/*']`.
- [x] Add scheduled field fallback `input[placeholder="选择日期和时间"]`.
- [x] Do not copy `+8h` blindly; HuaLok keeps China-local schedule time unchanged.

## Decision

Do not replace HuaLok. Use MultiPost as a reference and optionally as a second engine later.
