# 免安装绿色版(给非研发同事)

非研发同事装 Python/Git、配代理、下模型门槛太高。做法:**研发打包一次,同事解压双击即用**。

## 一、研发:打包(只做一次)

在一台**已经装好、能正常用**的 Windows 机器上(模型已下好):

```bash
python build_portable.py
```

> 走代理装依赖时,先 `set HTTPS_PROXY=...` 和 `set HTTP_PROXY=...`。

产物:`dist\voice-helper-portable.zip`(约 2~3GB,含内嵌 Python + 依赖 + SenseVoice 模型)。
把这个 zip 放到内部共享盘,发给同事。

> 绿色版默认带 **SenseVoice** 引擎(最稳)。打包前先在本机把 SenseVoice 模型下好(`bash voicectl.sh curldl` 或首次说话自动下)。

## 二、同事:使用(零门槛)

1. 把 zip 解压到**纯英文路径**,如 `C:\voice-helper`(**不要**放中文目录!)。
2. 双击 **「启动语音输入.bat」**。
3. 右下角托盘出现 🎤 图标后,在任意输入框**按住右 Alt 键**说话,松开即出字。

就这 3 步。不装 Python、不用 Git、不连网下模型、不碰代理。已自动设为开机自启。

- 停用:双击 **「停止.bat」**
- 卸载:双击 **「卸载.bat」**,再删整个文件夹

## 三、原理

绿色版文件夹结构:

```
voice-helper\
  python\            内嵌 Python(embeddable)+ 全部依赖,自带 pythonw.exe
  models\            已下好的模型(SenseVoiceSmall)
  voiced.py …        程序代码
  voice.env          默认配置(SenseVoice / 右Alt / 中文)
  启动语音输入.bat / 停止.bat / 卸载.bat / 使用说明.txt
```

- 用**内嵌 Python**(非系统 Python),所以同事不用装 Python。
- 模型放在 `models\`,程序自动识别本地目录加载(`_resolve_model`),不联网。
- 「启动」脚本在 Windows「启动」文件夹放一个隐藏启动项,开机自启。

## 四、注意

- **必须纯英文路径**(funasr 分词器打不开中文路径)。
- 默认 SenseVoice;想带 Paraformer 把它的模型也放进 `models\`,但部分机器 Paraformer 不兼容(见 README 避坑),非研发建议就用 SenseVoice。
- 想给同事预置常用纠正词:打包前编辑 `corrections.txt.example`(`错=>对`,每行一条),会随包带出去。

> 打包脚本在 Windows 上首次跑可能需按实际环境微调(内嵌 Python 版本、代理、模型位置)。有报错把日志发出来即可。
