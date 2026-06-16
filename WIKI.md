# Voice Helper — 全局语音输入工具(内部部署文档)

> 本地、离线的「按住说话」语音输入:在任意 App 的输入框里按住一个键说话,松开后自动把语音转成文字插入光标处。纯本地运行、不联网、零成本。Windows / macOS 通用,本文以 **Windows** 为主。

> 内部仓库地址:`<在此填公司内部 Git 地址>`(本文命令里的 `git clone` 请替换为该地址)

---

## 一、它是什么 / 能做什么

- **全局**:任何能粘贴文字的输入框都能用(终端、浏览器、IM、文档、邮件……)。
- **按住说话**:按住热键(默认右 Alt)录音 → 松开 → 自动转写并粘贴。
- **三引擎可切换**:
  - `whisper` — 多语言,中英混说友好
  - `sensevoice` — 中文优化,带标点,快
  - `paraformer` — 中文最准,支持**热词**+标点
- **纯本地**:模型下到本机,转写不联网;托盘图标显示状态(🎤待命/🔴录音/⏳转写/✅完成/⚠️失败)。
- **可纠错**:热词偏置 + 自动纠正表,把常错的词喂进去,以后自动纠正。

> 不适用:密码输入框(系统安全键盘屏蔽模拟粘贴)、全屏独占键盘的程序。

---

## 二、安装部署(Windows)

**前置**:已装 Python 3.10+、Git。

> ⚠️ **必须放在纯英文路径**(如 `D:\voice-helper`)。**不要**放含中文/空格的目录(如 `D:\智能运维\...`)——会导致模型加载报「Not Found」。

```bash
git clone <公司内部仓库地址> voice-helper   # 克隆到纯英文路径
cd voice-helper
python install.py                          # 建虚拟环境、装依赖、配开机自启
```

`install.py` 会自动:建 `.venv`、装 `faster-whisper`(CPU)+ SenseVoice 依赖、在「启动」文件夹放隐藏启动项(开机自启)。

### 公司网络(代理 / 证书)

模型默认从 ModelScope(国内)下载。公司内网通常要走代理,在 `voice.env` 里配(值同 git:`git config --global --get http.proxy`):

```
VOICE_PROXY=http://用户:密码@代理IP:端口
VOICE_INSECURE=1     # 代理做 TLS 拦截、报 self signed certificate 时加这行
```

下载模型(断点续传,抗代理断流):

```bash
bash voicectl.sh curldl all     # 在 Git Bash 里;下 SenseVoice + Paraformer + 标点
```

> 没有可用代理时:在能联网的机器上下好模型,把模型目录整个拷到本机(见“配置”里的模型路径)。

### 验证

```bash
bash voicectl.sh selftest       # 不需麦克风,验证模型加载/转写/纠正/剪贴板全链路
bash voicectl.sh status         # 看是否在运行 + 本次启动日志
```

`selftest` 全 ✅ 即软件就绪,剩下就是对着麦克风说话。

---

## 三、日常使用

1. 光标放进任意输入框。
2. **按住右 Alt** → 说话 → **松开**。
3. 文字自动转写并粘贴。

右下角系统托盘图标显示状态(被折叠点任务栏 `^` 展开)。**右键**菜单可:
- 看状态行(开头 `[Whisper]`/`[SenseVoice]`/`[Paraformer]` 是当前引擎)
- **切到 Whisper / SenseVoice / Paraformer**(即时热切换,无需重启)
- 复制最近识别 / 退出

---

## 四、配置(`voice.env`)

编辑仓库目录下的 `voice.env`,改完重启(`bash voicectl.sh restart` 或双击 `restart.bat`)。

| 配置 | 作用 | 默认 |
|------|------|------|
| `VOICE_ENGINE` | 引擎:`whisper`/`sensevoice`/`paraformer` | `sensevoice` |
| `VOICE_KEY` | 热键:`alt_r`(右Alt)/`ctrl_r`/`f8`… | `alt_r` |
| `VOICE_LANG` | 强制语言 `zh`/`en`;空=自动 | 空 |
| `VOICE_PROXY` | 下载代理 | 空 |
| `VOICE_INSECURE` | `1`=跳过 TLS 校验(代理拦截时) | 空 |
| `SENSEVOICE_MODEL` / `PARAFORMER_MODEL` | 模型仓库名或**本地目录路径** | 自动 |

> 模型缓存在 `%USERPROFILE%\.cache\modelscope\...`;`curldl` 下到 `仓库\models\`。`VOICE_*MODEL` 可填本地目录绝对路径(纯英文)。

---

## 五、提升中文准确度

中文「技术同音词」(时延/实验、推理/椎离)对通用模型都难。两招(对所有引擎生效,即时):

```bash
# 热词偏置(仅 paraformer 引擎):遇同音歧义优先匹配这些词
bash voicectl.sh hot 时延 推理 吞吐量

# 自动纠正(所有引擎):转写后把错词替换成对词
bash voicectl.sh fix 食盐 时延
```

> `hotwords.txt`(热词)和 `corrections.txt`(纠正)每次转写实时读取,加完立即生效,无需重启。建议日常用 `paraformer` 引擎 + 攒热词/纠正,越用越准。

---

## 六、维护命令(Git Bash,仓库目录)

| 命令 | 作用 |
|------|------|
| `bash voicectl.sh status` | 是否在运行 + 本次启动日志 |
| `bash voicectl.sh restart` / `stop` / `start` | 重启 / 停止 / 启动 |
| `bash voicectl.sh selftest` | 基础自测(不需麦克风) |
| `bash voicectl.sh doctor` | 一键诊断(环境/模型/网络/加载路径) |
| `bash voicectl.sh curldl all` | 断点续传下载模型 |
| `bash voicectl.sh fixpath` | 中文路径修复(模型挪到纯英文路径) |
| `bash voicectl.sh hot <词…>` / `fix <错> <对>` | 加热词 / 加纠正 |

> 也可在仓库目录双击 `.bat`:`status.bat` / `restart.bat` / `run-debug.bat`(前台看报错)。

---

## 七、部署避坑速查

| 现象 | 原因 | 解法 |
|------|------|------|
| 模型在却报 `Not Found ...bpe.model` | 路径含中文/非ASCII | 项目放纯英文路径;已装错跑 `bash voicectl.sh fixpath` |
| 启动日志 `api 407` / `authentication required` | 代理要鉴权,加载去连 ModelScope API | 模型下到本地后离线加载;`doctor` 第9行应为“本地路径” |
| 下载报 `self signed certificate` | 代理 TLS 拦截 | `voice.env` 加 `VOICE_INSECURE=1`(或配 `VOICE_CA`) |
| 下载全 `000` / 连不上 | 没走代理 | `voice.env` 配 `VOICE_PROXY`(同 git 的代理) |
| `model.pt` 越下越大 / 反复断 | modelscope 续传在烂代理上坏 | 用 `bash voicectl.sh curldl all`(curl 断点续传) |
| 按右 Alt 没反应 | 右 Alt 是 AltGr | 已自动兼容;仍不行改 `VOICE_KEY=f8` |
| 托盘菜单只有“退出” | 旧版 pystray 兼容问题 | 升级到最新代码(`git pull`) |
| 远程按键有反应但不出字 | 远程桌面不转发麦克风 | 到真机操作;或开 RDP「本地资源→远程音频→录制」 |

---

## 八、卸载

```bat
:: Git Bash 或 cmd,仓库目录
stop.bat
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\voice-helper.vbs"
:: 然后删掉仓库目录与(可选)模型缓存 %USERPROFILE%\.cache\modelscope
```

---

> 完整工程文档(含 macOS、源码结构):见仓库 `README.md`。
