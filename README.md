# 🎙️ Voice Helper — 全局语音输入工具

一个常驻的「按住说话」语音输入工具:在**任意 App** 的输入框里,按住快捷键说话,松开后自动把语音转成文字插入光标处。支持**多识别引擎可切换**(Whisper / SenseVoice),**跨平台**(macOS / Windows)。

> 为 Claude Code CLI 的语音输入而搭建,但对所有 App 通用。

---

## 〇、快速开始(跨平台,Git 仓库)

任意 Python 3.10+ 即可,安装脚本会自建 `.venv` 并装好对应平台的依赖、配置开机自启。

```bash
git clone <仓库地址> voice-helper
cd voice-helper
python install.py          # Windows 用 py install.py 或 python install.py
```

- **Windows**:`python install.py` 自动建环境、装 `faster-whisper`(CPU)+ SenseVoice、并在「启动」文件夹放一个隐藏启动项。装完即生效,开机自启。手动启动可双击 `run.bat`,看报错用 `run-debug.bat`。
- **macOS**:同一条命令,装 `mlx-whisper`(GPU)+ SenseVoice,并配 LaunchAgent。**额外需在系统设置授权**(见第⑧节)。
- 改配置:编辑 `voice.env`(引擎/热键/语言),然后重启服务。

> 首次说话会自动下载模型(SenseVoice 从 ModelScope,Whisper 从 HuggingFace),稍等片刻。

跨平台差异一览:

| 模块 | macOS | Windows |
|------|-------|---------|
| Whisper 后端 | `mlx-whisper`(Apple GPU) | `faster-whisper`(CPU,int8) |
| SenseVoice | funasr(通用) | funasr(通用) |
| 状态指示 | 菜单栏 emoji(rumps) | 系统托盘彩色图标(pystray) |
| 粘贴 | Cmd+V | Ctrl+V |
| 开机自启 | LaunchAgent | 启动文件夹 VBS(隐藏) |
| 系统授权 | 需输入监控/辅助功能/麦克风 | 无需特殊授权 |

---

## 一、它能做什么

- **全局可用**:任何能接受粘贴的输入框(终端、浏览器、微信、备忘录、邮件……)都能用。
- **按住说话**:按住「右 Option」键录音,松开即转写并自动粘贴。
- **多引擎可切换**:Whisper(多语言)/ SenseVoice(中文优化),通过 `VOICE_ENGINE` 一键切换,模型都在本地、互不替换。
- **状态可见**:屏幕顶部菜单栏图标实时显示状态,并标注当前引擎。
- **强制简体中文**:偶尔输出繁体时自动转简体(不影响英文)。
- **开机自启**:后台服务,开机自动运行、崩溃自动重启,无需手动开启。

**例外**:密码输入框(macOS 安全键盘机制屏蔽模拟粘贴)、全屏独占键盘的 App 可能用不了。

---

## 二、目录与文件结构

所有东西都在 `~/voice-helper/`:

| 路径 | 说明 |
|------|------|
| `voiced.py` | 主程序:常驻「按住说话」守护进程 + 状态图标 + 多引擎转写 |
| `vplatform.py` | 平台抽象层(剪贴板/粘贴键/声音/通知,mac↔win 差异都在这) |
| `tray.py` | 状态图标抽象(mac=rumps 菜单栏,win/linux=pystray 托盘) |
| `install.py` | 跨平台一键安装(建 venv、装依赖、配自启) |
| `voice.env` / `voice.env.example` | 配置文件(引擎/热键/语言);voiced 启动时自动读取 |
| `requirements-*.txt` | 分平台依赖清单(common / macos / windows / sensevoice) |
| `run.bat` / `run-debug.bat` | Windows 手动启动 / 调试启动 |
| `dictate.py` | 备用:一次性录音 → 转写 → 复制到剪贴板(不常驻) |
| `~/voice-helper/.venv/` | Python 虚拟环境(所有依赖装在这里) |
| `~/voice-helper/voiced.log` | 运行日志 |
| `~/Library/LaunchAgents/com.zhanggang.voiced.plist` | 开机自启配置(LaunchAgent) |

**技术栈**

| 组件 | 用途 |
|------|------|
| `mlx-whisper` | Whisper 引擎(Apple MLX 加速,吃满 M 芯片 GPU) |
| `funasr` + `modelscope` + `torchaudio` | SenseVoice 中文引擎(模型从 ModelScope 下载) |
| `sounddevice` | 麦克风录音(自带 portaudio) |
| `pynput` | 全局热键监听 + 模拟 Cmd-V 粘贴 |
| `rumps` | 菜单栏状态图标 |
| `opencc` | 繁体强制转简体 |

**模型缓存位置**

- Whisper:`~/.cache/huggingface/`(turbo 默认;large-v3 可选)
- SenseVoice:`~/.cache/modelscope/hub/models/iic/SenseVoiceSmall`(~900MB)

---

## 三、日常使用

1. 把光标放进任意输入框。
2. **按住「右 Option」键** → 说话 → **松开**。
3. 文字自动转写并粘贴到光标处。

菜单栏图标(屏幕**最顶部**系统栏,靠近刘海一侧)实时显示状态;点开菜单可见**当前引擎**(`[Whisper]` / `[SenseVoice]`)、最近一次识别文字(点击可复制)、退出按钮。

| 图标 | 含义 |
|------|------|
| 🎤 | 待命 |
| 🔴 | 录音中 |
| ⏳ | 转写中 |
| ✅ | 完成(闪一下回到 🎤) |
| ⚠️ | 太短 / 失败 |

---

## 四、识别引擎

通过 `VOICE_ENGINE` 选择,两个引擎模型都在本地,可随时切换:

| 引擎 | `VOICE_ENGINE` | 特点 | 适用 |
|------|----------------|------|------|
| **Whisper** | `whisper`(默认) | 多语言,中英混说友好 | 通用、英文多 |
| **SenseVoice** | `sensevoice` | 阿里达摩院,中文/方言优化,带智能标点,非自回归极快 | 中文为主 |

> **关于准确度**:中文里的「技术同音词」(如 时延 / 实验 / 食言,推理 / 椎离)对**所有通用模型**都是难点——它们会默认挑最常见的词。换模型只能小幅缓解。真正对症的是**热词偏置**(给模型一份高频词清单强制优先匹配),可通过 FunASR 的 SeACo-Paraformer 实现(规划中,见第八节)。

---

## 五、配置项(环境变量)

所有配置通过环境变量控制,写在 LaunchAgent 的 `EnvironmentVariables` 段里(见第六节)。

| 环境变量 | 作用 | 默认值 |
|---------|------|--------|
| `VOICE_ENGINE` | 识别引擎:`whisper` / `sensevoice` | `whisper` |
| `VOICE_KEY` | 说话热键:`alt_r`/`alt_l`/`ctrl_r`/`cmd_r`/`f5`… | `alt_r`(右 Option) |
| `VOICE_LANG` | 强制语言,如 `zh`/`en`;留空=自动识别 | 空(自动) |
| `WHISPER_MODEL` | Whisper 引擎用的模型 | `mlx-community/whisper-large-v3-turbo` |
| `SENSEVOICE_MODEL` | SenseVoice 引擎用的模型 | `iic/SenseVoiceSmall` |
| `VOICE_PROMPT` | Whisper 专用,热词/上下文提示(`initial_prompt`) | 一组技术词 |
| `VOICE_SOUND` | 设为任意值=开启声音提示 | 关 |
| `VOICE_NOTIFY` | 设为 `1`=完成时弹通知显示识别文字 | 关 |
| `VOICE_NO_PASTE` | 设为任意值=只复制到剪贴板,不自动粘贴 | 关(自动粘贴) |

### Whisper 模型选项(速度 vs 精度)

| 模型 | 大小 | 速度 | 精度 |
|------|------|------|------|
| `mlx-community/whisper-small-mlx` | ~0.5GB | 很快 | 中 |
| `mlx-community/whisper-large-v3-turbo` ← 默认 | ~1.6GB | 快(~0.8s) | 高 |
| `mlx-community/whisper-large-v3-mlx` | ~3GB | 稍慢 | 最高 |

### 当前生效配置(plist)

```
VOICE_KEY=alt_r
VOICE_ENGINE=sensevoice
VOICE_LANG=zh
VOICE_PROMPT=<一组技术热词>
```

---

## 六、如何修改配置

编辑 LaunchAgent 文件:

```bash
open -e ~/Library/LaunchAgents/com.zhanggang.voiced.plist
```

在 `<key>EnvironmentVariables</key>` 下的 `<dict>` 里增删配置,例如切回 Whisper:

```xml
<key>VOICE_ENGINE</key>
<string>whisper</string>
```

改完后**重启服务**生效:

```bash
launchctl kickstart -k gui/$(id -u)/com.zhanggang.voiced
```

---

## 七、开机自启 / 服务管理

后台常驻靠 macOS **LaunchAgent**:plist 里 `RunAtLoad=true`(登录即启动)、`KeepAlive=true`(崩溃自动重启)。

```bash
# 查看是否在运行(有输出即在跑)
launchctl list | grep voiced

# 重启(改完代码或配置后用)
launchctl kickstart -k gui/$(id -u)/com.zhanggang.voiced

# 临时关闭 / 重新开启
launchctl unload ~/Library/LaunchAgents/com.zhanggang.voiced.plist
launchctl load   ~/Library/LaunchAgents/com.zhanggang.voiced.plist

# 实时看日志
tail -f ~/voice-helper/voiced.log
```

---

## 八、系统权限(首次/换机必做)

后台进程需三项权限,授给那个 Python 解释器二进制:

```
/Users/zhanggang/.local/share/uv/python/cpython-3.13.13-macos-aarch64-none/bin/python3.13
```

在 **系统设置 → 隐私与安全性** 里授权:

| 权限 | 用途 |
|------|------|
| **输入监控 (Input Monitoring)** | 监听「右 Option」热键 |
| **辅助功能 (Accessibility)** | 模拟 Cmd-V 自动粘贴 |
| **麦克风 (Microphone)** | 录音 |

> 文件选择框灰掉无法选中时,改用「从 Finder 拖拽」该二进制到列表里。授权后需重启服务。

---

## 九、常见问题

**按了没反应,日志报 `PortAudioError ... [PaErrorCode -9986]`?**
录音设备状态变了(插拔耳机、切换音频输出、麦克风被别的程序占用)导致 PortAudio 缓存失效。**重启服务**即可恢复:
```bash
launchctl kickstart -k gui/$(id -u)/com.zhanggang.voiced
```

**菜单栏看不到图标?**
图标在屏幕**最顶部系统栏**(不是终端里),MacBook 刘海可能挡住。按住热键说话时盯顶栏看图标变化即正常。

**按键没反应** → 缺「输入监控」权限。
**有识别但没粘贴** → 缺「辅助功能」权限。
**录不到音** → 缺「麦克风」权限。
(授权后均需重启服务)

**输出繁体字?** 已用 OpenCC 强制转简体;若仍出现,检查 `opencc` 是否在 venv 里。

**改了 `voiced.py` 代码不生效?** 需 `launchctl kickstart -k gui/$(id -u)/com.zhanggang.voiced` 重启。

**下载 Whisper large-v3 一直卡在 `0.00B`?**
HF 大文件已改用 Xet 后端,某些网络下会卡死。**禁用 Xet 走旧通道**即可:
```bash
HF_HUB_DISABLE_XET=1 ~/voice-helper/.venv/bin/python -c \
  "from huggingface_hub import snapshot_download; print(snapshot_download('mlx-community/whisper-large-v3-mlx'))"
```
该模型权重文件名为 `weights.npz`(~3GB),下完后 `~/.cache/huggingface/.../snapshots/` 里应能看到它。

---

## 十、规划中:热词偏置(技术词准确度)

针对「技术同音词」(时延/实验、推理/椎离 等)的根治方案是**热词偏置**:
- 引擎换成 FunASR 的 **SeACo-Paraformer**(支持 `hotword` 参数)
- 新增 `VOICE_ENGINE=paraformer` 与 `VOICE_HOTWORD=<词表>` 配置
- 模型从 ModelScope 下载(国内快),funasr 已就绪
- 把高频技术词/专有名词放进 `VOICE_HOTWORD`,遇到同音歧义时强制优先匹配

> 尚未启用。启用后 Whisper / SenseVoice / Paraformer 三个引擎可自由切换。

---

## 十一、卸载

```bash
launchctl unload ~/Library/LaunchAgents/com.zhanggang.voiced.plist
rm ~/Library/LaunchAgents/com.zhanggang.voiced.plist
rm ~/.local/bin/voiced ~/.local/bin/dictate
rm -rf ~/voice-helper
# 可选:删模型缓存
# rm -rf ~/.cache/huggingface/hub/models--mlx-community--whisper-*
# rm -rf ~/.cache/modelscope/hub/models/iic/SenseVoiceSmall
```
